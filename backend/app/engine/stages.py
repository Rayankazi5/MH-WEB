"""
Psychological stage detection.

The stage is worked out from the patient's most recent scored check-in and
decides which reference items (app/engine/questionnaire_reference.py) are
added to the next check-in.

  initial  – no previous check-in: full reference screen
  stable   – low concern: short check-in
  mild     – some concern
  moderate – clear concern: broader screen
  severe   – high concern: broadest screen
  crisis   – any safety item (self-harm, harm to others, hopelessness)
             endorsed last time
"""
from __future__ import annotations

from app.engine.questionnaire_reference import (
    MEALS_LOW, SAFETY_KEYS, SLEEP_HIGH_HOURS, SLEEP_LOW_HOURS,
)

_CRISIS_KEYS = set(SAFETY_KEYS)
_SCALED_TYPES = {"phq9", "likert"}


def stage_from_responses(responses: list) -> str:
    """responses: objects with question_key, question_type and raw_value."""
    if not responses:
        return "initial"

    scaled: list[float] = []
    lifestyle_concern = False
    for r in responses:
        try:
            if r.question_type in _SCALED_TYPES:
                val = float(r.raw_value)
                if r.question_key in _CRISIS_KEYS and val >= 1:
                    return "crisis"
                scaled.append(max(0.0, min(1.0, val / 3.0)))
            elif r.question_key == "sleep_hours":
                hours = float(r.raw_value)
                lifestyle_concern |= hours < SLEEP_LOW_HOURS or hours > SLEEP_HIGH_HOURS
            elif r.question_key == "meals_per_day":
                lifestyle_concern |= float(r.raw_value) < MEALS_LOW
        except (TypeError, ValueError):
            continue

    concern = sum(scaled) / len(scaled) if scaled else 0.0
    if concern >= 0.6:
        return "severe"
    if concern >= 0.4:
        return "moderate"
    if concern >= 0.2 or lifestyle_concern:
        return "mild"
    return "stable"


def determine_stage(db, patient_id) -> str:
    from app.models.session import Session as CheckInSession, QuestionnaireResponse

    last = (
        db.query(CheckInSession)
        .filter(
            CheckInSession.patient_id == patient_id,
            CheckInSession.completed_at.isnot(None),
            CheckInSession.abstained.is_(False),
        )
        .order_by(CheckInSession.completed_at.desc())
        .first()
    )
    if last is None:
        return "initial"
    responses = (
        db.query(QuestionnaireResponse)
        .filter(QuestionnaireResponse.session_id == last.id)
        .all()
    )
    return stage_from_responses(responses)
