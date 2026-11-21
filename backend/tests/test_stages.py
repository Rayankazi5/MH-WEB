"""Stage detection and stage-aware question generation — pure logic."""
import sys
from pathlib import Path
from types import SimpleNamespace as R

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine.dissonance import detect_dissonance
from app.engine.questionnaire_reference import REFERENCE_ITEMS, SAFETY_KEYS, STAGES
from app.engine.questions import ALL_QUESTIONS, ANSWERABLE, LEGACY_QUESTION_BANK, generate_questions
from app.engine.profiles import PROFILE_KEYS, classify, compute_profile_scores
from app.engine.scoring import load_weights
from app.engine.scoring import extract_indicators
from app.engine.stages import stage_from_responses


def resp(key, qtype, val, rt=1500):
    return R(question_key=key, question_type=qtype, raw_value=val, response_time_ms=rt)


class TestStageFromResponses:
    def test_no_history_is_initial(self):
        assert stage_from_responses([]) == "initial"

    def test_low_scores_are_stable(self):
        assert stage_from_responses([resp("ref_numb", "likert", 0), resp("ref_loneliness", "likert", 0)]) == "stable"

    def test_high_scores_are_severe(self):
        assert stage_from_responses([resp("ref_loneliness", "likert", 3), resp("ref_numb", "likert", 2)]) == "severe"

    def test_safety_item_is_crisis(self):
        for key in SAFETY_KEYS:
            assert stage_from_responses([resp("ref_numb", "likert", 0), resp(key, "likert", 1)]) == "crisis"

    def test_short_sleep_or_few_meals_is_at_least_mild(self):
        assert stage_from_responses([resp("ref_numb", "likert", 0), resp("sleep_hours", "numeric", 4)]) == "mild"
        assert stage_from_responses([resp("ref_numb", "likert", 0), resp("sleep_hours", "numeric", 13)]) == "mild"
        assert stage_from_responses([resp("ref_numb", "likert", 0), resp("meals_per_day", "numeric", 1)]) == "mild"


class TestGenerateQuestions:
    def test_every_stage_has_safety_items_and_measures_every_type(self):
        weights = load_weights()
        for stage in STAGES:
            keys = {q["key"] for q in generate_questions(stage)}
            assert set(SAFETY_KEYS) <= keys
            assert {"sleep_hours", "meals_per_day"} <= keys
            for profile in PROFILE_KEYS:
                assert keys & set(weights[profile]), f"{profile} not measured at {stage}"

    def test_no_phq_questions_are_asked(self):
        for stage in STAGES:
            assert not any(q["key"].startswith(("phq_", "indirect_")) for q in generate_questions(stage))

    def test_initial_asks_everything(self):
        keys = {q["key"] for q in generate_questions("initial")}
        assert {q["key"] for q in REFERENCE_ITEMS} <= keys

    def test_stable_is_shorter_than_severe(self):
        assert len(generate_questions("stable")) < len(generate_questions("severe"))

    def test_text_prompts_come_last(self):
        types = [q["type"] for q in generate_questions("initial")]
        assert all(t == "text" for t in types[types.index("text"):])

    def test_unknown_stage_falls_back_to_initial(self):
        assert generate_questions("nonsense") == generate_questions("initial")

    def test_public_fields_only(self):
        for q in generate_questions("initial"):
            assert set(q) == {"key", "type", "text", "scale"}

    def test_all_keys_unique(self):
        assert len(ANSWERABLE) == len(REFERENCE_ITEMS)
        assert len(ALL_QUESTIONS) == len(LEGACY_QUESTION_BANK) + len(REFERENCE_ITEMS) - 1  # sleep_hours in both


class TestReferenceFlags:
    def _flags(self, responses):
        return {f["flag_type"] for f in detect_dissonance(extract_indicators(responses))}

    def test_self_harm_flags(self):
        assert "self_reported_safety_concern" in self._flags([resp("ref_self_harm", "likert", 1)])

    def test_no_flag_when_not_endorsed(self):
        assert "self_reported_safety_concern" not in self._flags([resp("ref_self_harm", "likert", 0)])

    def test_sleep_and_meal_flags(self):
        flags = self._flags([resp("sleep_hours", "numeric", 14), resp("meals_per_day", "numeric", 1)])
        assert {"sleep_out_of_range", "low_meal_intake"} <= flags
        assert not {"sleep_out_of_range", "low_meal_intake"} & self._flags(
            [resp("sleep_hours", "numeric", 8), resp("meals_per_day", "numeric", 3)]
        )

    def test_text_answers_are_not_scored(self):
        assert "subj_mind" not in extract_indicators([resp("subj_mind", "text", "encrypted-blob")])


class TestPatientType:
    def setup_method(self):
        self.weights = load_weights()

    def _type(self, answers):
        ind = extract_indicators([resp(k, "likert", v) for k, v in answers.items()])
        return classify(compute_profile_scores(ind, self.weights))

    def test_low_concern_when_nothing_elevated(self):
        assert self._type({k: 0 for k in ANSWERABLE if ANSWERABLE[k]["type"] == "likert"})["primary"] == "low_concern"

    def test_depressive(self):
        t = self._type({"ref_numb": 3, "ref_not_worthy": 2, "ref_no_excitement": 3, "ref_start_finish": 2,
                        "ref_loneliness": 0, "ref_thoughts_anxious": 0, "ref_flashbacks": 0, "ref_thoughts_repetitive": 0})
        assert t["primary"] == "depressive" and t["secondary"] == []

    def test_trauma_with_secondary(self):
        t = self._type({"ref_flashbacks": 3, "ref_thoughts_scary": 3, "ref_loneliness": 2, "ref_no_one_to_rely_on": 2,
                        "ref_thoughts_anxious": 0, "ref_no_excitement": 0, "ref_thoughts_repetitive": 0})
        assert t["primary"] == "trauma"
        assert "interpersonal" in t["secondary"]

    def test_obsessive(self):
        t = self._type({"ref_thoughts_repetitive": 3, "ref_thoughts_unwanted": 2, "ref_cant_change_behaviour": 2,
                        "ref_flashbacks": 0, "ref_thoughts_anxious": 0, "ref_loneliness": 0, "ref_no_excitement": 0})
        assert t["primary"] == "obsessive"

    def test_at_risk_is_independent_of_type(self):
        t = classify({"depressive": 0.1}, ["ref_self_harm"])
        assert t["at_risk"] and t["primary"] == "low_concern"
