"""Regression tests for the edge cases found in the 2026-11-22 probe."""
import math
import sys
from pathlib import Path
from types import SimpleNamespace as R

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine.profiles import classify, compute_profile_scores, endorsed_safety_items  # noqa: E402
from app.engine.questionnaire_reference import REFERENCE_BY_KEY, REFERENCE_ITEMS  # noqa: E402
from app.engine.questions import validate_answer  # noqa: E402
from app.engine.scoring import extract_indicators, load_weights  # noqa: E402
from app.engine.stages import stage_from_responses  # noqa: E402
from app.services.text_safety import screen_text  # noqa: E402

LIKERT = REFERENCE_BY_KEY["ref_numb"]
SLEEP = REFERENCE_BY_KEY["sleep_hours"]
TEXT = REFERENCE_BY_KEY["subj_mind"]


class TestValidateAnswer:
    @pytest.mark.parametrize("v", [0, 1, 2, 3, 2.0])
    def test_likert_ok(self, v):
        assert validate_answer(LIKERT, v) == (int(v), None)

    @pytest.mark.parametrize("v", [5, -1, 1.5, True, False, None, "2", "two", [1], {"a": 1}, math.nan, math.inf])
    def test_likert_rejected(self, v):
        assert validate_answer(LIKERT, v)[1] is not None

    @pytest.mark.parametrize("v", [0, 5.5, 16])
    def test_sleep_ok(self, v):
        assert validate_answer(SLEEP, v) == (v, None)

    @pytest.mark.parametrize("v", [-5, 16.01, 1_000_000, math.nan, math.inf, True, "8", None])
    def test_sleep_rejected(self, v):
        assert validate_answer(SLEEP, v)[1] is not None

    def test_text(self):
        assert validate_answer(TEXT, None) == ("", None)
        assert validate_answer(TEXT, "  hi  ") == ("hi", None)
        assert len(validate_answer(TEXT, "x" * 100_000)[0]) == 2000
        assert validate_answer(TEXT, 5)[1] is not None


class TestScoringNeverCrashes:
    def test_malformed_stored_answers_are_skipped(self):
        rs = [R(question_key="ref_numb", question_type="likert", raw_value=v, response_time_ms=1800)
              for v in (None, "two", True, [1], {"x": 1})]
        rs.append(R(question_key="ref_loneliness", question_type="likert", raw_value=2, response_time_ms=1800))
        ind = extract_indicators(rs)
        assert "ref_numb" not in ind and ind["ref_loneliness"] == pytest.approx(2 / 3)


class TestTextSafety:
    @pytest.mark.parametrize("t", ["I want to kill myself", "thinking about ending it all", "I’m suicidal",
                                   "I'd be better off dead", "I don't want to wake up", "I keep cutting myself", "self-harming again"])
    def test_self(self, t):
        assert screen_text(t)["self"]

    @pytest.mark.parametrize("t", ["I want to hurt someone", "I could kill him", "I feel like attacking people", "I thought about stabbing my boss"])
    def test_others(self, t):
        assert screen_text(t)["others"]

    @pytest.mark.parametrize("t", ["Busy week, a bit tired", "I killed it at work today", "this commute is killing me", ""])
    def test_benign(self, t):
        assert screen_text(t) == {"self": False, "others": False}


def _type(answers):
    rs = [R(question_key=q["key"], question_type=q["type"], raw_value=answers.get(q["key"], 0), response_time_ms=1800)
          for q in REFERENCE_ITEMS if q["type"] == "likert"]
    ind = extract_indicators(rs)
    return classify(compute_profile_scores(ind, load_weights()), endorsed_safety_items(ind))


class TestClassificationBoundaries:
    def test_several_days_on_a_type_is_elevated(self):
        t = _type({"ref_thoughts_repetitive": 1, "ref_thoughts_unwanted": 1, "ref_cant_change_behaviour": 1})
        assert t["primary"] == "obsessive"

    def test_exact_tie_is_joint(self):
        t = classify({"anxious": 0.5, "trauma": 0.5, "depressive": 0.1})
        assert t["joint"] == ["anxious", "trauma"] and t["primary_label"] == "Anxious + Trauma-related"

    def test_within_margin_is_joint_outside_is_secondary(self):
        t = classify({"anxious": 0.60, "trauma": 0.56, "interpersonal": 0.40})
        assert t["joint"] == ["anxious", "trauma"] and t["secondary"] == ["interpersonal"]

    def test_three_or_more_close_is_mixed(self):
        t = classify({"anxious": 1.0, "trauma": 1.0, "obsessive": 1.0, "depressive": 0.85})
        assert t["primary"] == "mixed" and t["primary_label"] == "Mixed" and t["secondary"] == ["depressive"]

    def test_single_type(self):
        t = classify({"anxious": 0.7, "trauma": 0.3})
        assert t["primary_label"] == "Anxious" and t["joint"] == ["anxious"] and t["secondary"] == []


class TestLegacyPhq9:
    def test_old_phq9_item9_still_means_crisis(self):
        rs = [R(question_key="phq_9", question_type="phq9", raw_value=3), R(question_key="phq_2", question_type="phq9", raw_value=0)]
        assert stage_from_responses(rs) == "crisis"


class TestSafetyNoteWording:
    from app.services.insight_chat import safety_note as _note
    note = staticmethod(_note)

    def test_self_only(self):
        assert "harming yourself," in self.note(["self"]) and "someone else" not in self.note(["self"])

    def test_others_only(self):
        n = self.note(["others"])
        assert "harming someone else" in n and "yourself" not in n

    def test_both(self):
        assert "harming yourself or someone else" in self.note(["self", "others"])

    def test_hopeless_only(self):
        n = self.note(["hopeless"])
        assert "feeling hopeless" in n and "harming" not in n

    def test_hopeless_and_self(self):
        assert "feeling hopeless or having thoughts of harming yourself" in self.note(["hopeless", "self"])

    def test_nothing(self):
        assert self.note([]) is None
