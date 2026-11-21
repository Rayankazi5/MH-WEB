"""
Patient types, identified from the reference questionnaire.

Each type is a weighted average of the questionnaire items that describe it
(weights in app/engine/weights.json), on a 0–1 scale where 1 means every item
was answered "Nearly every day". A type is "elevated" once its score reaches
ELEVATED_THRESHOLD (roughly an average of "Several days" or more).

  primary    – the highest elevated type, or "low_concern" if none is elevated
  secondary  – the other elevated types, highest first
  at_risk    – any safety item (self-harm, harm to others, hopelessness)
               answered above "Not at all"; shown above the type, always
"""
from __future__ import annotations

from app.engine.questionnaire_reference import SAFETY_KEYS

PROFILE_KEYS = ["depressive", "anxious", "obsessive", "trauma", "interpersonal"]

# Clinician-facing names.
PROFILE_LABELS = {
    "depressive": "Depressive",
    "anxious": "Anxious",
    "obsessive": "Obsessive / repetitive",
    "trauma": "Trauma-related",
    "interpersonal": "Interpersonal / relational",
    "low_concern": "Low concern",
}

PROFILE_DESCRIPTIONS = {
    "depressive": "Hopelessness, numbness, low worth, loss of interest, trouble starting or finishing things.",
    "anxious": "Anxious, worried or frightening thoughts.",
    "obsessive": "Repetitive or unwanted thoughts; unable to change a behaviour despite knowing its effect.",
    "trauma": "Flashbacks or vivid memories of upsetting events, frightening or intrusive thoughts, numbness.",
    "interpersonal": "Loneliness, no one to rely on, feeling disapproved of, staying in harmful relationships.",
    "low_concern": "No type reached the elevated threshold.",
}

ELEVATED_THRESHOLD = 0.34


def compute_profile_scores(indicators: dict, weights: dict) -> dict:
    """Weighted mean of each type's answered items. Types with no answered items are left out."""
    scores = {}
    for profile in PROFILE_KEYS:
        w = weights.get(profile, {})
        present = {k: wt for k, wt in w.items() if k in indicators}
        if not present:
            continue
        total = sum(present.values())
        scores[profile] = round(sum(indicators[k] * wt for k, wt in present.items()) / total, 4)
    return scores


def endorsed_safety_items(values: dict) -> list:
    """values: question_key → normalised (0–1) or raw (0–3) answer; anything above 0 counts."""
    out = []
    for k in SAFETY_KEYS:
        try:
            if float(values.get(k, 0) or 0) > 0:
                out.append(k)
        except (TypeError, ValueError):
            continue
    return out


def classify(profile_scores: dict, safety_items: list | None = None) -> dict:
    elevated = sorted(
        (p for p, s in profile_scores.items() if p in PROFILE_KEYS and s >= ELEVATED_THRESHOLD),
        key=lambda p: -profile_scores[p],
    )
    primary = elevated[0] if elevated else "low_concern"
    safety_items = list(safety_items or [])
    return {
        "primary": primary,
        "primary_label": PROFILE_LABELS[primary],
        "secondary": elevated[1:],
        "secondary_labels": [PROFILE_LABELS[p] for p in elevated[1:]],
        "at_risk": bool(safety_items),
        "safety_items": safety_items,
        "scores": {p: profile_scores[p] for p in PROFILE_KEYS if p in profile_scores},
        "threshold": ELEVATED_THRESHOLD,
    }


def classify_latest(db, patient_id) -> dict | None:
    """Patient type from the most recent scored check-in, or None if there isn't one."""
    from app.models.score import DomainScore
    from app.models.session import Session as CheckInSession, QuestionnaireResponse

    latest = (
        db.query(CheckInSession)
        .filter(
            CheckInSession.patient_id == patient_id,
            CheckInSession.completed_at.isnot(None),
            CheckInSession.abstained.is_(False),
        )
        .order_by(CheckInSession.completed_at.desc())
        .first()
    )
    if latest is None:
        return None
    rows = (
        db.query(DomainScore)
        .filter(DomainScore.session_id == latest.id, DomainScore.domain.in_(PROFILE_KEYS))
        .all()
    )
    if not rows:
        return None  # last check-in predates patient types, or is still scoring
    responses = (
        db.query(QuestionnaireResponse)
        .filter(QuestionnaireResponse.session_id == latest.id, QuestionnaireResponse.question_key.in_(SAFETY_KEYS))
        .all()
    )
    result = classify({r.domain: r.score for r in rows},
                      endorsed_safety_items({r.question_key: r.raw_value for r in responses}))
    result["session_id"] = str(latest.id)
    result["session_date"] = latest.completed_at.isoformat() if latest.completed_at else None
    return result


def protective_factors(response_map: dict) -> list[dict]:
    """Strengths from one check-in's raw answers (0 = "Not at all" is the healthy end)."""
    factors = []

    def num(key):
        try:
            return float(response_map[key])
        except (KeyError, TypeError, ValueError):
            return None

    hours = num("sleep_hours")
    if hours is not None:
        strength = "strong" if 7 <= hours <= 9 else "moderate" if 5 <= hours <= 12 else "low"
        factors.append({"label": "Avg. sleep duration", "value": f"{hours:g} hrs/night", "strength": strength, "icon": "🌙"})

    meals = num("meals_per_day")
    if meals is not None:
        strength = "strong" if meals >= 2.5 else "moderate" if meals >= 1.5 else "low"
        factors.append({"label": "Meals per day", "value": f"{meals:g}", "strength": strength, "icon": "🍽️"})

    labels = ["Not at all", "Several days", "More than half the days", "Nearly every day"]
    for key, label, icon in [
        ("ref_no_one_to_rely_on", "Has someone to rely on", "🤝"),
        ("ref_no_excitement", "Finds things exciting", "✨"),
        ("ref_start_finish", "Starts & finishes things", "✅"),
    ]:
        v = num(key)
        if v is None:
            continue
        strength = "strong" if v == 0 else "moderate" if v == 1 else "low"
        factors.append({"label": label, "value": f"Struggles: {labels[min(int(v), 3)].lower()}" if v else "Yes", "strength": strength, "icon": icon})
    return factors
