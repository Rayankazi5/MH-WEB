"""
Patient types, identified from the reference questionnaire.

Each type is a weighted average of the questionnaire items that describe it
(weights in app/engine/weights.json), on a 0–1 scale where 1 means every item
was answered "Nearly every day". A type is "elevated" once its score reaches
ELEVATED_THRESHOLD (an average of "Several days" or more).

  primary    – the highest elevated type, or "low_concern" if none is elevated
  joint      – elevated types within JOINT_MARGIN of the highest; shown together
               ("A + B", or "Mixed" for three or more) instead of picking one
  secondary  – the other elevated types, highest first
  at_risk    – any safety item (self-harm, harm to others, hopelessness)
               answered above "Not at all", or risk language in a free-text
               answer; shown above the type, always
"""
from __future__ import annotations

from app.engine.questionnaire_reference import ANSWER_LABELS, SAFETY_KEYS, SAFETY_LABELS

PROFILE_KEYS = ["depressive", "anxious", "obsessive", "trauma", "interpersonal"]

# Clinician-facing names.
PROFILE_LABELS = {
    "depressive": "Depressive",
    "anxious": "Anxious",
    "obsessive": "Obsessive / repetitive",
    "trauma": "Trauma-related",
    "interpersonal": "Interpersonal / relational",
    "low_concern": "Low concern",
    "mixed": "Mixed",
    "pending": "Type pending",
}

PROFILE_DESCRIPTIONS = {
    "depressive": "Hopelessness, numbness, low worth, loss of interest, trouble starting or finishing things.",
    "anxious": "Anxious, worried or frightening thoughts.",
    "obsessive": "Repetitive or unwanted thoughts; unable to change a behaviour despite knowing its effect.",
    "trauma": "Flashbacks or vivid memories of upsetting events, frightening or intrusive thoughts, numbness.",
    "interpersonal": "Loneliness, no one to rely on, feeling disapproved of, staying in harmful relationships.",
    "low_concern": "No type reached the elevated threshold.",
    "mixed": "Three or more types are elevated to a similar degree.",
}

ELEVATED_THRESHOLD = 0.33   # "Several days" on every item of a type = 0.333 → elevated
JOINT_MARGIN = 0.05         # types within 5 points of the top are joint main types

# Flags on a check-in that also mark the patient at risk
SAFETY_FLAG_TYPES = {"self_reported_safety_concern", "free_text_risk_language", "ml_suicidal_risk_signal"}
SAFETY_FLAG_LABELS = {"free_text_risk_language": "free_text_risk", "ml_suicidal_risk_signal": "free_text_risk"}


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
        key=lambda p: (-profile_scores[p], PROFILE_KEYS.index(p)),
    )
    if elevated:
        top = profile_scores[elevated[0]]
        joint = [p for p in elevated if top - profile_scores[p] <= JOINT_MARGIN + 1e-9]
    else:
        joint = []
    primary = elevated[0] if elevated else "low_concern"
    if len(joint) >= 3:
        primary_label = PROFILE_LABELS["mixed"]
    elif len(joint) == 2:
        primary_label = " + ".join(PROFILE_LABELS[p] for p in joint)
    else:
        primary_label = PROFILE_LABELS[primary]
    secondary = [p for p in elevated if p not in joint]
    safety_items = list(dict.fromkeys(safety_items or []))
    return {
        "primary": "mixed" if len(joint) >= 3 else primary,
        "primary_label": primary_label,
        "joint": joint,
        "joint_labels": [PROFILE_LABELS[p] for p in joint],
        "secondary": secondary,
        "secondary_labels": [PROFILE_LABELS[p] for p in secondary],
        "at_risk": bool(safety_items),
        "safety_items": safety_items,
        "scores": {p: profile_scores[p] for p in PROFILE_KEYS if p in profile_scores},
        "threshold": ELEVATED_THRESHOLD,
    }


def latest_checkin(db, patient_id):
    """
    The patient's most recent check-in that has been submitted at least once: either
    completed, or reopened with Edit (which keeps its safety flags). A brand-new check-in
    that hasn't been submitted yet doesn't count, so yesterday's result still applies
    while today's is being filled in.
    """
    from app.models.flag import DissonanceFlag
    from app.models.session import Session as CheckInSession

    recent = (
        db.query(CheckInSession)
        .filter(CheckInSession.patient_id == patient_id)
        .order_by(CheckInSession.started_at.desc())
        .limit(10)
        .all()
    )
    from app.models.score import DomainScore

    for s in recent:
        if s.deleted_at is not None:
            # Deleted by the patient: only still counts while a safety flag is unresolved
            if (db.query(DissonanceFlag.id).filter(
                    DissonanceFlag.session_id == s.id,
                    DissonanceFlag.flag_type.in_(SAFETY_FLAG_TYPES),
                    DissonanceFlag.resolved.is_(None)).first()):
                return s
            continue
        if s.completed_at is not None:
            return s
        # Reopened with Edit: it was submitted before, so it still has its scores or flags
        if (db.query(DomainScore.id).filter(DomainScore.session_id == s.id).first()
                or db.query(DissonanceFlag.id).filter(DissonanceFlag.session_id == s.id).first()):
            return s
    return None


def safety_items_for(db, session) -> list:
    """
    Why a check-in marks the patient at risk, from its unresolved safety flags.
    A clinician resolving the flag clears it.
    """
    from app.models.flag import DissonanceFlag
    from app.models.session import QuestionnaireResponse

    flag_types = {
        f for (f,) in db.query(DissonanceFlag.flag_type)
        .filter(
            DissonanceFlag.session_id == session.id,
            DissonanceFlag.flag_type.in_(SAFETY_FLAG_TYPES),
            DissonanceFlag.resolved.is_(None),
        )
        .all()
    }
    items = []
    if "self_reported_safety_concern" in flag_types:
        responses = (
            db.query(QuestionnaireResponse)
            .filter(QuestionnaireResponse.session_id == session.id, QuestionnaireResponse.question_key.in_(SAFETY_KEYS))
            .all()
        )
        endorsed = endorsed_safety_items({r.question_key: r.raw_value for r in responses})
        items += endorsed or ["edited_safety_answer"]  # reported, then edited away by the patient
    items += [SAFETY_FLAG_LABELS[f] for f in sorted(flag_types) if f in SAFETY_FLAG_LABELS]
    return list(dict.fromkeys(items))


_ITEM_REASON = {"ref_self_harm": "self", "ref_thoughts_harm_others": "others", "ref_hopelessness": "hopeless"}


def safety_reasons(db, session) -> list:
    """
    What the patient reported, for patient-facing wording: any of "self" (harming themself),
    "others" (harming someone else), "hopeless". Read from the unresolved safety flags, which
    record what was originally reported (so this still works after an Edit).
    """
    from app.models.flag import DissonanceFlag

    reasons = set()
    for flag_type, text in (
        db.query(DissonanceFlag.flag_type, DissonanceFlag.self_report_val)
        .filter(
            DissonanceFlag.session_id == session.id,
            DissonanceFlag.flag_type.in_(SAFETY_FLAG_TYPES),
            DissonanceFlag.resolved.is_(None),
        )
        .all()
    ):
        text = text or ""
        if flag_type == "self_reported_safety_concern":
            # current flags use the question wording; older ones listed the question keys
            reasons |= {r for k, r in _ITEM_REASON.items() if k in text or SAFETY_LABELS[k] in text}
        elif flag_type == "free_text_risk_language":
            if "harming themself" in text:
                reasons.add("self")
            if "harming others" in text:
                reasons.add("others")
        elif flag_type == "ml_suicidal_risk_signal":
            reasons.add("self")
    return [r for r in ("self", "others", "hopeless") if r in reasons]


def safety_details_for(db, session) -> list[dict]:
    """
    Clinician-facing detail for the At risk banner: which question, and the answer given.
    e.g. [{"label": "Thoughts of hurting someone else", "answer": "Several days"}]
    """
    from app.models.flag import DissonanceFlag
    from app.models.session import QuestionnaireResponse
    from app.engine.scoring import DELETED_NOTE, EDITED_NOTE

    details = []
    flags = (
        db.query(DissonanceFlag)
        .filter(
            DissonanceFlag.session_id == session.id,
            DissonanceFlag.flag_type.in_(SAFETY_FLAG_TYPES),
            DissonanceFlag.resolved.is_(None),
        )
        .all()
    )
    by_type = {f.flag_type: f for f in flags}
    if "self_reported_safety_concern" in by_type:
        answers = {
            r.question_key: r.raw_value for r in db.query(QuestionnaireResponse).filter(
                QuestionnaireResponse.session_id == session.id, QuestionnaireResponse.question_key.in_(SAFETY_KEYS)
            )
        }
        current = []
        for k in SAFETY_KEYS:
            try:
                v = int(answers.get(k, 0) or 0)
            except (TypeError, ValueError):
                continue
            if v > 0:
                current.append({"item": k, "label": SAFETY_LABELS[k], "answer": ANSWER_LABELS[min(v, 3)]})
        if current:
            details += current
        else:  # reported, then edited away — show what was originally reported
            original = (by_type["self_reported_safety_concern"].self_report_val or "")
            original = original.replace(EDITED_NOTE, "").replace(DELETED_NOTE, "").strip()
            details.append({"item": "edited_safety_answer", "label": "Originally reported (patient later changed it to “Not at all”)",
                            "answer": original})
    for t in ("free_text_risk_language", "ml_suicidal_risk_signal"):
        if t in by_type:
            text = (by_type[t].self_report_val or "").replace(EDITED_NOTE, "").replace(DELETED_NOTE, "").strip()
            details.append({"item": "free_text_risk", "label": "Risk language in a written answer",
                            "answer": text.replace("Free-text answer mentions ", "mentions ")})
    return details


def classify_latest(db, patient_id) -> dict | None:
    """
    Patient type from the most recent submitted check-in, or None if there is nothing to show.
    A check-in reopened with Edit keeps showing its last submitted result ("being_edited").
    If it couldn't be scored but carries a safety flag, the patient is still shown as at
    risk, with the type marked "pending".
    """
    from app.models.score import DomainScore

    latest = latest_checkin(db, patient_id)
    if latest is None:
        return None
    rows = []
    if not latest.abstained:  # a reopened check-in keeps its last submitted scores
        rows = (
            db.query(DomainScore)
            .filter(DomainScore.session_id == latest.id, DomainScore.domain.in_(PROFILE_KEYS))
            .all()
        )
    safety = safety_items_for(db, latest)
    if not rows and not safety:
        return None  # nothing scored yet (or an older pre-type check-in) and no risk
    result = classify({r.domain: r.score for r in rows}, safety)
    if not rows:
        result.update(primary="pending", primary_label=PROFILE_LABELS["pending"], joint=[], joint_labels=[])
    result["safety_details"] = safety_details_for(db, latest) if safety else []
    result["scores_pending"] = not rows
    # Reopened with Edit: everything shown is the last submitted result until resubmitted
    result["being_edited"] = latest.completed_at is None
    result["session_id"] = str(latest.id)
    result["session_date"] = (latest.completed_at or latest.started_at).isoformat()
    return result


# Patient-facing badge (S1–S4), shown in the patient app. Computed here so it always agrees
# with what the clinician sees.
def _risk(t: dict | None) -> dict:
    """
    The home-screen "Risk Rate". An unresolved safety flag is always High (no number — it
    isn't a score). Otherwise it is the highest patient-type score, so one strongly elevated
    type isn't averaged away by the others.
    """
    if t is not None and t["at_risk"]:
        return {"pct": None, "label": "High", "reason": "safety"}
    if t is None or not t["scores"]:
        return {"pct": None, "label": "No data", "reason": None}
    pct = round(max(t["scores"].values()) * 100)
    label = "Low" if pct < round(ELEVATED_THRESHOLD * 100) else "Moderate" if pct < 60 else "High"
    return {"pct": pct, "label": label, "reason": "scores"}


def patient_badge(db, patient_id) -> dict:
    t = classify_latest(db, patient_id)
    risk = _risk(t)
    if t is None:
        return {"badge": "NONE", "at_risk": False, "checked_in": latest_checkin(db, patient_id) is not None, "risk": risk}
    if t["at_risk"]:
        reasons = safety_reasons(db, latest_checkin(db, patient_id))
        return {"badge": "S2", "at_risk": True, "checked_in": True, "risk": risk, "safety_reasons": reasons}
    scores = t["scores"]
    if not scores:
        return {"badge": "NONE", "at_risk": False, "checked_in": True, "risk": risk}
    avg = sum(scores.values()) / len(scores)
    if scores.get("depressive", 0) > 0.5 or scores.get("anxious", 0) > 0.5:
        badge = "S2"
    elif avg > 0.35:
        badge = "S3"
    elif avg > 0.22:
        badge = "S4"
    else:
        badge = "S1"
    return {"badge": badge, "at_risk": False, "checked_in": True, "risk": risk}


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
