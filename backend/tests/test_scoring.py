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
    compute_uncertainty,
    normalise_calendar_inverted,
    normalise_meals_concern,
    normalise_phq,
    normalise_sleep_concern,
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


# ── Patient-type scoring ──────────────────────────────────────────────────────

class TestSleepAndMealConcern:
    def test_healthy_sleep_is_zero(self):
        assert normalise_sleep_concern(8) == 0.0

    def test_short_and_long_sleep_are_concerning(self):
        assert normalise_sleep_concern(4) == 1.0
        assert normalise_sleep_concern(12) == 1.0
        assert 0 < normalise_sleep_concern(5.5) < 1

    def test_meals(self):
        assert normalise_meals_concern(3) == 0.0
        assert normalise_meals_concern(0) == 1.0
        assert normalise_meals_concern(1.5) == pytest.approx(0.4)


class TestComputeAllDomains:
    def setup_method(self):
        self.weights = load_weights()

    def test_one_score_per_type_when_all_answered(self):
        indicators = {k: 0.5 for profile in self.weights.values() for k in profile}
        scores = compute_all_domains(indicators, self.weights)
        assert set(scores) == set(DOMAINS)
        assert all(v == pytest.approx(0.5) for v in scores.values())

    def test_no_answers_gives_no_scores(self):
        assert compute_all_domains({}, self.weights) == {}

    def test_scores_are_absolute_not_shares(self):
        indicators = {k: 1.0 for profile in self.weights.values() for k in profile}
        assert all(v == pytest.approx(1.0) for v in compute_all_domains(indicators, self.weights).values())

    def test_flashbacks_drive_trauma(self):
        indicators = {k: 0.0 for profile in self.weights.values() for k in profile}
        indicators["ref_flashbacks"] = 1.0
        scores = compute_all_domains(indicators, self.weights)
        assert max(scores, key=scores.get) == "trauma"


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
        assert detect_dissonance({}) == []

    def test_loneliness_vs_journal_isolation_flag(self):
        flags = detect_dissonance({"ref_loneliness": 0.0, "journal_isolation": 0.7})
        assert "social_report_vs_withdrawal" in [f["flag_type"] for f in flags]

    def test_loneliness_flag_not_triggered_when_lonely_reported(self):
        flags = detect_dissonance({"ref_loneliness": 0.67, "journal_isolation": 0.7})
        assert "social_report_vs_withdrawal" not in [f["flag_type"] for f in flags]

    def test_mood_movement_needs_movement_data(self):
        calm = {"ref_no_excitement": 0.0, "ref_hopelessness": 0.0}
        assert "mood_movement" not in [f["flag_type"] for f in detect_dissonance(calm)]
        flags = detect_dissonance({**calm, "daily_step_variance": 0.1})
        assert "mood_movement" in [f["flag_type"] for f in flags]

    def test_flag_fields_and_severities(self):
        flags = detect_dissonance({
            "ref_loneliness": 0.0, "journal_isolation": 0.7,
            "ref_no_excitement": 0.0, "ref_hopelessness": 0.0, "daily_step_variance": 0.1,
        })
        assert len(flags) >= 2
        for flag in flags:
            assert set(flag) == {"flag_type", "self_report_val", "signal_val", "severity"}
            assert flag["severity"] in {"low", "medium", "high"}
