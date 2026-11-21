"""
Reference questionnaire, consulted before a check-in's questions are generated.

Areas covered: thoughts, actions, consequences, satisfaction/fulfilment,
motivation, flashbacks, plus subjective (free-text / daily routine) prompts.

Clinical sources used as structural references (dimension names only; item
wording below is our own, the instruments themselves are copyrighted):
  - Brief Symptom Inventory (BSI):
    https://cdn.pabau.com/cdn/attachments/pulse/content-engine/templates/brief-symptom-inventory/brief-symptom-inventory.pdf
  - Symptom Checklist-90 (SCL-90):
    https://accesscm.org/wp-content/uploads/2013/03/SCL-90.pdf
  Shared dimensions: somatization, obsessive-compulsive, interpersonal
  sensitivity, depression, anxiety, hostility, phobic anxiety, paranoid
  ideation, psychoticism.

This is the full check-in question bank (it replaced the PHQ-9 based bank).
Each item lists the stages it should be asked in (see app/engine/stages.py);
one item per patient type (app/engine/profiles.py) is asked at every stage so
each type is measured in every check-in.
Items marked "safety": True are asked in every stage and raise a clinician
flag when endorsed (see app/engine/dissonance.py).
"""

FREQUENCY_SCALE = {
    "min": 0, "max": 3,
    "labels": ["Not at all", "Several days", "More than half the days", "Nearly every day"],
}

# Stage names, lowest to highest concern. Defined here so the reference and
# the stage logic share one vocabulary.
STAGES = ["initial", "stable", "mild", "moderate", "severe", "crisis"]
ALL_STAGES = list(STAGES)

REFERENCE_SOURCES = [
    {"name": "Brief Symptom Inventory (BSI)",
     "url": "https://cdn.pabau.com/cdn/attachments/pulse/content-engine/templates/brief-symptom-inventory/brief-symptom-inventory.pdf"},
    {"name": "Symptom Checklist-90 (SCL-90)",
     "url": "https://accesscm.org/wp-content/uploads/2013/03/SCL-90.pdf"},
]


def _item(key, text, area, stages, bsi=None, safety=False, qtype="likert", scale=FREQUENCY_SCALE):
    return {
        "key": key, "type": qtype, "text": text, "scale": scale,
        "area": area, "stages": stages, "bsi_dimension": bsi, "safety": safety,
    }


REFERENCE_ITEMS = [
    # ── Thoughts ──────────────────────────────────────────────────────────
    _item("ref_thoughts_anxious", "This week, how often did you have anxious or worried thoughts?",
          "thoughts", ALL_STAGES, bsi="anxiety"),
    _item("ref_thoughts_repetitive", "How often did the same thoughts keep repeating in your mind?",
          "thoughts", ALL_STAGES, bsi="obsessive_compulsive"),
    _item("ref_thoughts_unwanted", "How often did unwanted or intrusive thoughts come into your mind?",
          "thoughts", ["initial", "moderate", "severe", "crisis"], bsi="obsessive_compulsive"),
    _item("ref_thoughts_scary", "How often did you have thoughts that frightened you?",
          "thoughts", ["initial", "moderate", "severe", "crisis"], bsi="phobic_anxiety"),
    _item("ref_thoughts_harm_others", "How often did you have thoughts of hurting someone else?",
          "thoughts", ALL_STAGES, bsi="hostility", safety=True),

    # ── Feelings (the "are you feeling / do you have feelings of" set) ──
    _item("ref_hopelessness", "Are you having feelings of hopelessness?",
          "thoughts", ALL_STAGES, bsi="depression", safety=True),
    _item("ref_self_harm", "Have you had feelings of wanting to harm yourself?",
          "thoughts", ALL_STAGES, bsi="depression", safety=True),
    _item("ref_loneliness", "Are you having feelings of loneliness?",
          "thoughts", ALL_STAGES, bsi="interpersonal_sensitivity"),
    _item("ref_numb", "Are you feeling numb or emotionally flat?",
          "thoughts", ["initial", "moderate", "severe", "crisis"], bsi="depression"),
    _item("ref_no_one_to_rely_on", "Do you feel like there is no one you can rely on?",
          "thoughts", ["initial", "moderate", "severe", "crisis"], bsi="interpersonal_sensitivity"),
    _item("ref_not_worthy", "Do you have feelings that you are not worthy?",
          "thoughts", ["initial", "mild", "moderate", "severe"], bsi="depression"),
    _item("ref_disapproval", "Do you feel that the people around you disapprove of you?",
          "thoughts", ["initial", "moderate", "severe"], bsi="paranoid_ideation"),

    # ── Actions ──────────────────────────────────────────────────────────
    _item("ref_harmful_relationships", "Are you staying in relationships you feel are harmful to you?",
          "actions", ["initial", "moderate", "severe"], bsi="interpersonal_sensitivity"),
    _item("ref_cant_change_behaviour", "Do you feel unable to change a behaviour even though you know it affects you?",
          "actions", ["initial", "mild", "moderate", "severe"], bsi="obsessive_compulsive"),

    # ── Consequences ─────────────────────────────────────────────────────
    _item("ref_consequences", "How often have your thoughts or actions caused problems at work, school or home?",
          "consequences", ["initial", "moderate", "severe"]),

    # ── Satisfaction / fulfilment ────────────────────────────────────────
    _item("ref_no_excitement", "Do you feel that nothing excites you anymore?",
          "satisfaction", ALL_STAGES, bsi="depression"),

    # ── Motivation ───────────────────────────────────────────────────────
    _item("ref_start_finish", "Do you have trouble starting or finishing things?",
          "motivation", ["initial", "stable", "mild", "moderate", "severe"], bsi="obsessive_compulsive"),

    # ── Flashbacks ───────────────────────────────────────────────────────
    _item("ref_flashbacks", "How often did you have flashbacks or vivid memories of upsetting events?",
          "flashbacks", ALL_STAGES, bsi="anxiety"),

    # ── Subjective ───────────────────────────────────────────────────────
    _item("subj_mind", "How does it feel to be in your mind right now?",
          "subjective", ["initial", "moderate", "severe", "crisis"], qtype="text", scale=None),
    _item("subj_day_to_day", "What does your day-to-day look like at the moment?",
          "subjective", ["initial", "mild", "moderate", "severe"], qtype="text", scale=None),
    _item("sleep_hours", "On average, how many hours of sleep did you get per night this week?",
          "subjective", ALL_STAGES, qtype="numeric", scale={"min": 0, "max": 16}),
    _item("meals_per_day", "On average, how many meals did you eat per day this week?",
          "subjective", ALL_STAGES, qtype="numeric", scale={"min": 0, "max": 6}),
]

# Thresholds from the subjective day-to-day prompt.
SLEEP_LOW_HOURS = 5
SLEEP_HIGH_HOURS = 12
MEALS_LOW = 1.5

REFERENCE_BY_KEY = {q["key"]: q for q in REFERENCE_ITEMS}
SAFETY_KEYS = [q["key"] for q in REFERENCE_ITEMS if q["safety"]]


def reference_items_for_stage(stage: str) -> list[dict]:
    """Reference items to ask at a given stage (safety items always included)."""
    if stage not in STAGES:
        stage = "initial"
    return [q for q in REFERENCE_ITEMS if q["safety"] or stage in q["stages"]]
