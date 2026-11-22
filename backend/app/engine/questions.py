PHQ_SCALE = {
    "min": 0, "max": 3,
    "labels": ["Not at all", "Several days", "More than half the days", "Nearly every day"],
}

# Retired PHQ-9 based bank — no longer asked. Kept only so check-ins answered
# before the switch still show their question text to clinicians.
LEGACY_QUESTION_BANK = [
    {"key": "phq_1a", "type": "phq9", "text": "This week, how often did you lose interest in things you normally care about?", "scale": PHQ_SCALE},
    {"key": "phq_1b", "type": "phq9", "text": "This week, how often did activities feel joyless or unfulfilling, even ones you usually enjoy?", "scale": PHQ_SCALE},
    {"key": "indirect_sleep_days", "type": "calendar", "text": "Which nights this week did you sleep well? Select all that apply.", "scale": None},
    {"key": "phq_2", "type": "phq9",  "text": "Feeling down, depressed, or hopeless?", "scale": PHQ_SCALE},
    {"key": "phq_3", "type": "phq9",  "text": "Trouble falling or staying asleep, or sleeping too much?", "scale": PHQ_SCALE},
    {"key": "indirect_social_days", "type": "calendar", "text": "Which days this week did you spend meaningful time with others? Select all that apply.", "scale": None},
    {"key": "phq_4", "type": "phq9",  "text": "Feeling tired or having little energy?", "scale": PHQ_SCALE},
    {"key": "phq_5a", "type": "phq9", "text": "This week, how often did you have little or no appetite?", "scale": PHQ_SCALE},
    {"key": "phq_5b", "type": "phq9", "text": "This week, how often did you eat much more than usual or feel out of control around food?", "scale": PHQ_SCALE},
    {"key": "sleep_hours", "type": "numeric", "text": "On average, how many hours of sleep did you get per night this week?", "scale": {"min": 0, "max": 16}},
    {"key": "phq_6", "type": "phq9",  "text": "Feeling bad about yourself — or that you are a failure?", "scale": PHQ_SCALE},
    {"key": "indirect_productive_days", "type": "calendar", "text": "Which days this week felt productive to you? Select all that apply.", "scale": None},
    {"key": "phq_7", "type": "phq9",  "text": "Trouble concentrating on things?", "scale": PHQ_SCALE},
    {"key": "phq_8", "type": "phq9",  "text": "Moving or speaking slowly — or being fidgety or restless?", "scale": PHQ_SCALE},
    {"key": "phq_9", "type": "phq9",  "text": "Thoughts that you would be better off dead or hurting yourself?", "scale": PHQ_SCALE},
]

# ── Current question bank ────────────────────────────────────────────────────
# Every check-in question now comes from the reference questionnaire. The
# patient's stage (app/engine/stages.py) decides which items are asked.
from app.engine.questionnaire_reference import REFERENCE_ITEMS, reference_items_for_stage  # noqa: E402

_PUBLIC_FIELDS = ("key", "type", "text", "scale")

QUESTION_BANK = [{f: q[f] for f in _PUBLIC_FIELDS} for q in REFERENCE_ITEMS]

# Keys a patient may answer today.
ANSWERABLE = {q["key"]: q for q in REFERENCE_ITEMS}

# Every key ever asked, for labelling past sessions.
ALL_QUESTIONS = {**{q["key"]: q for q in LEGACY_QUESTION_BANK}, **ANSWERABLE}

# Items asked at every stage — their presence drives the confidence score.
EXPECTED_INDICATOR_KEYS = [
    q["key"] for q in REFERENCE_ITEMS
    if q["type"] != "text" and len(q["stages"]) == 6
] + ["rt_mean"]


def generate_questions(stage: str) -> list[dict]:
    """The reference items for this stage, ending with the free-text prompts."""
    ref = reference_items_for_stage(stage)
    ref.sort(key=lambda q: q["type"] == "text")  # free-text prompts last
    return [{f: q[f] for f in _PUBLIC_FIELDS} for q in ref]


# ── Answer validation ────────────────────────────────────────────────────────
import math  # noqa: E402

MAX_TEXT_CHARS = 2000


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def validate_answer(question: dict, value):
    """
    Returns (clean_value, None) or (None, error message).
    likert  – whole number within the scale (0–3)
    numeric – finite number within the scale (e.g. sleep 0–16, meals 0–6)
    text    – a string (empty = skipped), trimmed to MAX_TEXT_CHARS
    """
    qtype = question["type"]
    scale = question.get("scale") or {}
    if qtype in ("likert", "phq9"):
        if not _is_number(value) or float(value) != int(value):
            return None, "Answer must be a whole number"
        lo, hi = scale.get("min", 0), scale.get("max", 3)
        if not lo <= int(value) <= hi:
            return None, f"Answer must be between {lo} and {hi}"
        return int(value), None
    if qtype == "numeric":
        if not _is_number(value):
            return None, "Answer must be a number"
        lo, hi = scale.get("min", 0), scale.get("max", float("inf"))
        if not lo <= value <= hi:
            return None, f"Answer must be between {lo:g} and {hi:g}"
        return value, None
    if qtype == "text":
        if value is None:
            return "", None
        if not isinstance(value, str):
            return None, "Answer must be text"
        return value.strip()[:MAX_TEXT_CHARS], None
    return None, f"Unsupported question type: {qtype}"
