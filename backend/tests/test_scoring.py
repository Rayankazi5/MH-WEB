"""Unit tests for the scoring engine — no DB, no HTTP, pure logic."""
import sys
from pathlib import Path

import pytest

# Make sure the backend package is importable when running from the tests/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine.scoring import (
    ABSTAIN_THRESHOLD,
    DOMAINS,
    compute_all_domains,
    compute_domain_score,
    compute_uncertainty,
    normalise_calendar_inverted,
    normalise_phq,
    normalise_rt,
    normalise_sentiment,
    should_abstain,
    load_weights,
)
from app.engine.dissonance import detect_dissonance


# ── Indicator normalisers ─────────────────────────────────────────────────────

class TestNormalisePhq:
    def test_zero(self):
        assert normalise_phq(0) == 0.0

    def test_max(self):
        assert normalise_phq(3) == 1.0

    def test_midpoint(self):
        assert normalise_phq(1.5) == pytest.approx(0.5)

    def test_clamp_above(self):
        assert normalise_phq(9) == 1.0

    def test_clamp_below(self):
        assert normalise_phq(-1) == 0.0


class TestNormaliseCalendarInverted:
    def test_no_good_days_is_max_concern(self):
        assert normalise_calendar_inverted(0) == 1.0

    def test_all_good_days_is_zero_concern(self):
        assert normalise_calendar_inverted(7) == 0.0

    def test_half_week(self):
        # 3 good days → 1 - 3/7 ≈ 0.571
        assert normalise_calendar_inverted(3) == pytest.approx(1 - 3 / 7)

    def test_clamp_above(self):
        assert normalise_calendar_inverted(10) == 0.0


class TestNormaliseRt:
    def test_very_fast_is_low(self):
        # 500ms well below the 2000ms midpoint → logistic ≈ 0.13, clearly below 0.5
        assert normalise_rt(500) < 0.2

    def test_midpoint(self):
        # At exactly 2000ms the logistic equals 0.5
        assert normalise_rt(2000) == pytest.approx(0.5, abs=1e-6)

    def test_very_slow_is_high(self):
        assert normalise_rt(8000) > 0.9


class TestNormaliseSentiment:
    def test_very_positive(self):
        # VADER +1.0 → 0.0 concern
        assert normalise_sentiment(1.0) == pytest.approx(0.0)

    def test_neutral(self):
        assert normalise_sentiment(0.0) == pytest.approx(0.5)

    def test_very_negative(self):
        # VADER -1.0 → 1.0 concern
        assert normalise_sentiment(-1.0) == pytest.approx(1.0)


# ── Domain scoring ────────────────────────────────────────────────────────────

class TestComputeDomainScore:
    def setup_method(self):
        self.weights = load_weights()

    def test_zero_indicators_gives_zero(self):
        score = compute_domain_score({}, self.weights, "mood_stability")
        assert score == 0.0

    def test_all_ones_is_positive(self):
        indicators = {k: 1.0 for domain in self.weights.values() for k in domain}
        score = compute_domain_score(indicators, self.weights, "anxiety")
        assert score > 0

    def test_relu_clamps_negative(self):
        # All indicators at 0 → dot product = 0 → after ReLU still 0
        indicators = {k: 0.0 for domain in self.weights.values() for k in domain}
        for domain in DOMAINS:
            assert compute_domain_score(indicators, self.weights, domain) == 0.0


class TestComputeAllDomains:
    def setup_method(self):
        self.weights = load_weights()

    def test_sums_to_one(self):
        indicators = {k: 0.5 for domain in self.weights.values() for k in domain}
        scores = compute_all_domains(indicators, self.weights)
        assert sum(scores.values()) == pytest.approx(1.0, abs=1e-6)

    def test_returns_all_five_domains(self):
        scores = compute_all_domains({}, self.weights)
        assert set(scores.keys()) == set(DOMAINS)

    def test_zero_indicators_distributes_uniformly(self):
        # All zero → all pseudosums 0 → after adding epsilon, all equal
        scores = compute_all_domains({}, self.weights)
        values = list(scores.values())
        assert max(values) - min(values) < 0.01

    def test_elevated_sleep_indicators(self):
        # High sleep concern indicators should push sleep_quality up
        indicators = {
            "indirect_sleep_days": 1.0,
            "sleep_hours": 1.0,
            "phq_3": 1.0,
            "journal_sleep_disruption": 1.0,
        }
        scores = compute_all_domains(indicators, self.weights)
        assert scores["sleep_quality"] == max(scores.values())


# ── Uncertainty & abstention ──────────────────────────────────────────────────

class TestComputeUncertainty:
    def test_all_present_uniform_rt_is_low(self):
        expected = ["phq_1", "phq_2", "phq_3"]
        indicators = {"phq_1": 0.5, "phq_2": 0.5, "phq_3": 0.5, "rt_phq_1": 0.5, "rt_phq_2": 0.5}
        u = compute_uncertainty(indicators, expected)
        # missing_penalty = 0; rt std ≈ 0 → low uncertainty
        assert u < 0.3

    def test_all_missing_gives_high_uncertainty(self):
        expected = ["phq_1", "phq_2", "phq_3", "phq_4"]
        u = compute_uncertainty({}, expected)
        # missing_penalty = 1.0; no RT → rt_penalty = 0.5
        # uncertainty = 0.6*1.0 + 0.4*0.5 = 0.8
        assert u == pytest.approx(0.8, abs=0.01)

    def test_high_rt_variance_increases_uncertainty(self):
        expected = ["phq_1"]
        indicators_uniform = {"phq_1": 0.5, "rt_phq_1": 0.5, "rt_phq_2": 0.5}
        indicators_skewed = {"phq_1": 0.5, "rt_phq_1": 0.01, "rt_phq_2": 0.99}
        u_uniform = compute_uncertainty(indicators_uniform, expected)
        u_skewed = compute_uncertainty(indicators_skewed, expected)
        assert u_skewed > u_uniform


class TestShouldAbstain:
    def test_above_threshold_abstains(self):
        assert should_abstain(ABSTAIN_THRESHOLD + 0.01) is True

    def test_at_threshold_does_not_abstain(self):
        assert should_abstain(ABSTAIN_THRESHOLD) is False

    def test_well_below_does_not_abstain(self):
        assert should_abstain(0.1) is False


# ── Dissonance detection ──────────────────────────────────────────────────────

class TestDetectDissonance:
    def test_no_flags_when_no_signals(self):
        flags = detect_dissonance({})
        assert flags == []

    def test_social_withdrawal_flag_triggered(self):
        indicators = {
            "indirect_social_days": 0.8,
            "journal_isolation": 0.7,
        }
        flags = detect_dissonance(indicators)
        flag_types = [f["flag_type"] for f in flags]
        assert "social_report_vs_withdrawal" in flag_types

    def test_social_withdrawal_not_triggered_when_below_threshold(self):
        indicators = {
            "indirect_social_days": 0.3,
            "journal_isolation": 0.3,
        }
        flags = detect_dissonance(indicators)
        flag_types = [f["flag_type"] for f in flags]
        assert "social_report_vs_withdrawal" not in flag_types

    def test_mood_movement_flag_triggered(self):
        indicators = {
            "phq_2": 0.1,         # low mood self-report
            "daily_step_variance": 0.1,   # sedentary
        }
        flags = detect_dissonance(indicators)
        flag_types = [f["flag_type"] for f in flags]
        assert "mood_movement" in flag_types

    def test_flag_has_required_fields(self):
        indicators = {
            "indirect_social_days": 0.8,
            "journal_isolation": 0.7,
        }
        flags = detect_dissonance(indicators)
        assert len(flags) >= 1
        for flag in flags:
            assert "flag_type" in flag
            assert "self_report_val" in flag
            assert "signal_val" in flag
            assert "severity" in flag

    def test_severity_values_are_valid(self):
        indicators = {
            "phq_2": 0.1,
            "daily_step_variance": 0.1,
            "indirect_social_days": 0.8,
            "journal_isolation": 0.7,
        }
        flags = detect_dissonance(indicators)
        valid_severities = {"low", "medium", "high"}
        for flag in flags:
            assert flag["severity"] in valid_severities
