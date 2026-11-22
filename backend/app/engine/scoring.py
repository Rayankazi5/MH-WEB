import json
from pathlib import Path
import numpy as np

from app.engine.profiles import PROFILE_KEYS, compute_profile_scores

# Scores are stored per patient type (DomainScore.domain holds the type key).
DOMAINS = PROFILE_KEYS
ABSTAIN_THRESHOLD = 0.55

# Appended to a kept safety flag when the patient's edited answers no longer raise it
EDITED_NOTE = "(answer later changed by patient — originally reported as above)"
# Appended to a safety flag when the patient deletes its check-in (the flag and answers are kept)
DELETED_NOTE = "(check-in deleted by patient — kept for clinician review)"


def apply_differential_privacy(scores: dict, epsilon: float) -> dict:
    """
    Gaussian mechanism ε-DP on 0–1 patient-type scores.
    Sensitivity = 1/len(scores); σ is calibrated so the guarantee holds with δ=1e-5.
    Scores are absolute (not a share of a total), so they are clamped, not renormalised.
    """
    if not scores:
        return scores
    sensitivity = 1.0 / len(scores)
    sigma = sensitivity * np.sqrt(2.0 * np.log(1.25 / 1e-5)) / epsilon
    return {d: float(min(1.0, max(0.0, v + float(np.random.normal(0.0, sigma))))) for d, v in scores.items()}


def load_weights() -> dict:
    path = Path(__file__).parent / "weights.json"
    return json.loads(path.read_text())


def normalise_phq(val: float) -> float:
    return max(0.0, min(1.0, val / 3.0))


def normalise_calendar_inverted(days_selected: int) -> float:
    # Fewer good days = higher concern
    return max(0.0, min(1.0, 1.0 - (days_selected / 7.0)))


def normalise_numeric_inverted(val: float, max_val: float = 12.0) -> float:
    # Lower value (e.g. fewer sleep hours) = higher concern
    return max(0.0, min(1.0, 1.0 - (val / max_val)))


def normalise_sleep_concern(hours: float) -> float:
    # 7–9 h = no concern; rises to full concern at 4 h or 12 h.
    if hours < 7:
        return max(0.0, min(1.0, (7.0 - hours) / 3.0))
    if hours > 9:
        return max(0.0, min(1.0, (hours - 9.0) / 3.0))
    return 0.0


def normalise_meals_concern(meals: float) -> float:
    # 2.5+ meals = no concern; 0 meals = full concern (1.5 meals → 0.4).
    return max(0.0, min(1.0, (2.5 - meals) / 2.5))


def normalise_rt(rt_ms: float) -> float:
    # Slower RT → higher value → possible manipulation / fatigue
    return float(1.0 / (1.0 + np.exp(-(rt_ms - 2000) / 800)))


def normalise_sentiment(vader_compound: float) -> float:
    # VADER compound [-1, 1] → [0, 1]; lower sentiment = higher concern
    return 1.0 - (vader_compound + 1.0) / 2.0


def extract_indicators(responses: list, journal=None) -> dict:
    indicators: dict = {}
    rt_values: list = []

    for r in responses:
        try:
            _add_response(indicators, rt_values, r)
        except (TypeError, ValueError, OverflowError):
            # A malformed stored answer is skipped rather than crashing the whole check-in
            continue

    if rt_values:
        indicators["rt_mean"] = float(np.mean(rt_values))

    if journal is not None:
        if journal.sentiment_score is not None:
            # sentiment_score already in [0, 1] where 1 = negative (high concern)
            indicators["sentiment"] = float(journal.sentiment_score)
        if journal.keyword_vector:
            for cluster_key, freq in journal.keyword_vector.items():
                indicators[cluster_key] = float(freq)

    return indicators


def _add_response(indicators: dict, rt_values: list, r) -> None:
    key = r.question_key
    val = r.raw_value
    rt = r.response_time_ms

    if rt is not None:
        normalised_rt = normalise_rt(float(rt))
        rt_values.append(normalised_rt)
        indicators[f"rt_{key}"] = normalised_rt

    if r.question_type == "text":
        return  # free-text (encrypted) — screened separately, not scored
    if isinstance(val, bool):
        raise TypeError("boolean answer")
    if r.question_type in ("phq9", "likert"):
        indicators[key] = normalise_phq(float(val))
    elif r.question_type == "calendar":
        days = len(val) if isinstance(val, list) else int(val)
        indicators[key] = normalise_calendar_inverted(days)
    elif r.question_type == "numeric" and key == "sleep_hours":
        hours = float(val)
        indicators[key] = normalise_sleep_concern(hours)
        indicators["sleep_hours_raw"] = hours
    elif r.question_type == "numeric" and key == "meals_per_day":
        indicators["meals_per_day_raw"] = float(val)
        indicators[key] = normalise_meals_concern(float(val))
    elif r.question_type == "numeric":
        indicators[key] = max(0.0, min(1.0, float(val) / 12.0))


def compute_all_domains(indicators: dict, weights: dict) -> dict:
    """0–1 score per patient type (see app/engine/profiles.py)."""
    return compute_profile_scores(indicators, weights)


def compute_uncertainty(indicators: dict, expected_keys: list) -> float:
    present = sum(1 for k in expected_keys if k in indicators)
    completeness = present / len(expected_keys) if expected_keys else 1.0
    missing_penalty = 1.0 - completeness

    rts = [v for k, v in indicators.items() if k.startswith("rt_")]
    if rts:
        rt_variance = float(np.std(rts)) / (float(np.mean(rts)) + 1e-9)
        rt_penalty = min(rt_variance / 2.0, 1.0)
    else:
        rt_penalty = 0.5

    uncertainty = 0.6 * missing_penalty + 0.4 * rt_penalty
    return round(uncertainty, 4)


def should_abstain(uncertainty: float) -> bool:
    return uncertainty > ABSTAIN_THRESHOLD


def _enrich_journal_with_mh_classifier(db, journal) -> None:
    """
    Best-effort: run the remote mental-health RoBERTa classifier on this
    journal entry's decrypted body and merge its label scores into
    keyword_vector (prefixed "mh_") for clinician visibility and for the
    suicidal-risk safety flag in app/engine/dissonance.py. A classifier
    failure (missing token, network error, cold-start timeout) must never
    block scoring — it just means these keys stay absent this round.
    """
    from app.services.encryption import decrypt
    from app.services.mental_health_classifier import classify_mental_health_risk

    try:
        body = decrypt(journal.body_encrypted)
        mh_scores = classify_mental_health_risk(body)
        if not mh_scores:
            return
        vector = dict(journal.keyword_vector or {})
        vector.update({f"mh_{label}": score for label, score in mh_scores.items()})
        journal.keyword_vector = vector
        db.commit()
    except Exception:
        db.rollback()


def run_scoring_pipeline(session_id_str: str) -> None:
    from datetime import datetime
    from app.database import SessionLocal
    from app.models.session import Session, QuestionnaireResponse
    from app.models.journal import JournalEntry
    from app.models.score import DomainScore
    from app.models.flag import DissonanceFlag
    from app.engine.dissonance import detect_dissonance
    from app.engine.questions import EXPECTED_INDICATOR_KEYS

    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.id == session_id_str).first()
        if not session:
            return

        responses = db.query(QuestionnaireResponse).filter(
            QuestionnaireResponse.session_id == session.id
        ).all()

        journal = db.query(JournalEntry).filter(
            JournalEntry.session_id == session.id
        ).first()

        if journal is not None:
            _enrich_journal_with_mh_classifier(db, journal)

        indicators = extract_indicators(responses, journal)
        for k, v in _screen_free_text(responses).items():
            indicators[k] = max(v, indicators.get(k, 0.0))  # keep the higher of journal / free-text signal
        uncertainty = compute_uncertainty(indicators, EXPECTED_INDICATOR_KEYS)
        session.uncertainty_val = uncertainty

        # Flags (including safety flags) are saved even when the check-in can't be scored.
        # Safety flags kept from before an Edit are not duplicated; if the edited answers
        # no longer raise one, it is kept and annotated rather than removed.
        new_flags = detect_dissonance(indicators)
        # A resubmit (after Edit) replaces the previous result: scores and non-safety flags
        # are recalculated from scratch; safety flags are kept and handled below.
        from app.engine.profiles import SAFETY_FLAG_TYPES
        db.query(DomainScore).filter(DomainScore.session_id == session.id).delete(synchronize_session=False)
        db.query(DissonanceFlag).filter(
            DissonanceFlag.session_id == session.id,
            DissonanceFlag.flag_type.notin_(SAFETY_FLAG_TYPES),
        ).delete(synchronize_session=False)
        kept = {
            f.flag_type: f for f in db.query(DissonanceFlag).filter(DissonanceFlag.session_id == session.id).all()
        }
        new_types = {f["flag_type"] for f in new_flags}
        for flag_type, existing in kept.items():
            if flag_type not in new_types and EDITED_NOTE not in (existing.self_report_val or ""):
                existing.self_report_val = f"{existing.self_report_val} {EDITED_NOTE}"
        for flag in new_flags:
            if flag["flag_type"] in kept:
                continue
            db.add(DissonanceFlag(
                session_id=session.id,
                patient_id=session.patient_id,
                flag_type=flag["flag_type"],
                self_report_val=flag["self_report_val"],
                signal_val=flag["signal_val"],
                severity=flag["severity"],
            ))

        weights = load_weights()
        domain_scores = compute_all_domains(indicators, weights)

        # Too little data, or nothing that maps to a patient type → "not scored" rather than stuck
        if should_abstain(uncertainty) or not domain_scores:
            session.abstained = True
            db.commit()
            return

        from app.config import get_settings
        settings = get_settings()
        if settings.privacy_enabled:
            domain_scores = apply_differential_privacy(domain_scores, settings.privacy_epsilon)

        confidence = round(1.0 - uncertainty, 4)

        for domain, score in domain_scores.items():
            db.add(DomainScore(
                session_id=session.id,
                patient_id=session.patient_id,
                domain=domain,
                score=score,
                confidence=confidence,
            ))

        db.commit()
    except Exception:
        db.rollback()
        # Never leave a check-in stuck on "scoring": mark it not scored, then surface the error
        try:
            stuck = db.query(Session).filter(Session.id == session_id_str).first()
            if stuck is not None:
                stuck.abstained = True
                db.commit()
        except Exception:
            db.rollback()
        raise
    finally:
        db.close()


def _screen_free_text(responses: list) -> dict:
    """
    Risk-language screen over the free-text answers: an offline keyword check, plus the
    remote mental-health classifier (same one used on journals) when it is configured.
    """
    from app.services.encryption import decrypt
    from app.services.text_safety import screen_text

    texts = []
    for r in responses:
        if r.question_type != "text":
            continue
        try:
            body = decrypt(r.raw_value)
        except Exception:
            continue
        if body.strip():
            texts.append(body)
    if not texts:
        return {}

    combined = "\n".join(texts)
    hits = screen_text(combined)
    out = {"text_risk_self": 1.0 if hits["self"] else 0.0, "text_risk_others": 1.0 if hits["others"] else 0.0}
    try:
        from app.services.mental_health_classifier import classify_mental_health_risk
        for label, score in (classify_mental_health_risk(combined) or {}).items():
            out[f"mh_{label}"] = float(score)
    except Exception:
        pass  # classifier unavailable — keyword screen still applies
    return out
