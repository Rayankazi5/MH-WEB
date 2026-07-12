import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import require_clinician
from app.database import get_db
from app.models.flag import DissonanceFlag
from app.models.link import ClinicianPatient
from app.models.narrative import Narrative
from app.models.score import DomainScore
from app.models.session import Session as CheckInSession, QuestionnaireResponse
from app.models.user import User, ROLE_PATIENT
from app.schemas.clinician import LinkRequest

router = APIRouter(prefix="/clinician", tags=["clinician"])


def _assert_linked(db: Session, clinician_id, patient_id) -> ClinicianPatient:
    link = (
        db.query(ClinicianPatient)
        .filter(
            ClinicianPatient.clinician_id == clinician_id,
            ClinicianPatient.patient_id == patient_id,
            ClinicianPatient.active == True,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found or not linked")
    return link


@router.get("/patients")
def list_patients(current_user: User = Depends(require_clinician), db: Session = Depends(get_db)):
    links = (
        db.query(ClinicianPatient)
        .filter(ClinicianPatient.clinician_id == current_user.id, ClinicianPatient.active == True)
        .all()
    )
    result = []
    for link in links:
        patient = db.query(User).filter(User.id == link.patient_id).first()
        if not patient:
            continue

        last_session = (
            db.query(CheckInSession)
            .filter(CheckInSession.patient_id == patient.id, CheckInSession.completed_at.isnot(None))
            .order_by(CheckInSession.completed_at.desc())
            .first()
        )
        open_flags = (
            db.query(DissonanceFlag)
            .filter(DissonanceFlag.patient_id == patient.id, DissonanceFlag.resolved.is_(None))
            .count()
        )

        result.append({
            "id": str(patient.id),
            "full_name": patient.full_name,
            "email": patient.email,
            "timezone": patient.timezone,
            "last_session_at": last_session.completed_at.isoformat() if last_session else None,
            "open_flags": open_flags,
        })
    return result


@router.post("/link", status_code=status.HTTP_201_CREATED)
def link_patient(payload: LinkRequest, current_user: User = Depends(require_clinician), db: Session = Depends(get_db)):
    patient = db.query(User).filter(User.email == payload.patient_email, User.role == ROLE_PATIENT).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    existing = (
        db.query(ClinicianPatient)
        .filter(ClinicianPatient.clinician_id == current_user.id, ClinicianPatient.patient_id == patient.id)
        .first()
    )
    if existing:
        if existing.active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already linked")
        existing.active = True
        db.commit()
        return {"clinician_patient_id": str(current_user.id) + ":" + str(patient.id)}

    db.add(ClinicianPatient(clinician_id=current_user.id, patient_id=patient.id))
    db.commit()
    return {"clinician_patient_id": str(current_user.id) + ":" + str(patient.id)}


@router.delete("/link/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_patient(
    patient_id: uuid.UUID,
    current_user: User = Depends(require_clinician),
    db: Session = Depends(get_db),
):
    link = _assert_linked(db, current_user.id, patient_id)
    link.active = False
    db.commit()


@router.get("/patient/{patient_id}/summary")
def patient_summary(
    patient_id: uuid.UUID,
    current_user: User = Depends(require_clinician),
    db: Session = Depends(get_db),
):
    _assert_linked(db, current_user.id, patient_id)
    cutoff = datetime.utcnow() - timedelta(weeks=4)

    scores = (
        db.query(DomainScore)
        .filter(DomainScore.patient_id == patient_id, DomainScore.computed_at >= cutoff)
        .order_by(DomainScore.computed_at)
        .all()
    )
    domain_map: dict = {}
    for s in scores:
        domain_map.setdefault(s.domain, []).append(
            {"date": s.computed_at.isoformat(), "score": s.score, "confidence": s.confidence}
        )

    narrative = (
        db.query(Narrative)
        .filter(Narrative.patient_id == patient_id)
        .order_by(Narrative.generated_at.desc())
        .first()
    )

    open_flags = (
        db.query(DissonanceFlag)
        .filter(DissonanceFlag.patient_id == patient_id, DissonanceFlag.resolved.is_(None))
        .order_by(DissonanceFlag.created_at.desc())
        .all()
    )

    patient = db.query(User).filter(User.id == patient_id).first()

    return {
        "id": str(patient_id),
        "full_name": patient.full_name if patient else "",
        "email": patient.email if patient else "",
        "timezone": patient.timezone if patient else "UTC",
        "domain_scores": domain_map,
        "latest_narrative": {
            "week_start": str(narrative.week_start),
            "bullets": narrative.bullets,
        } if narrative else None,
        "open_flags": [
            {
                "flag_type": f.flag_type,
                "self_report_val": f.self_report_val,
                "signal_val": f.signal_val,
                "severity": f.severity,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in open_flags
        ],
    }


@router.get("/patient/{patient_id}/scores")
def patient_scores(
    patient_id: uuid.UUID,
    domain: Optional[str] = Query(None),
    weeks: int = Query(4, ge=1, le=52),
    current_user: User = Depends(require_clinician),
    db: Session = Depends(get_db),
):
    _assert_linked(db, current_user.id, patient_id)
    cutoff = datetime.utcnow() - timedelta(weeks=weeks)

    q = db.query(DomainScore).filter(
        DomainScore.patient_id == patient_id,
        DomainScore.computed_at >= cutoff,
    )
    if domain:
        q = q.filter(DomainScore.domain == domain)

    rows = q.order_by(DomainScore.computed_at).all()
    return [
        {"date": r.computed_at.isoformat(), "domain": r.domain, "score": r.score, "confidence": r.confidence}
        for r in rows
    ]


@router.get("/patient/{patient_id}/narrative")
def patient_narrative(
    patient_id: uuid.UUID,
    current_user: User = Depends(require_clinician),
    db: Session = Depends(get_db),
):
    _assert_linked(db, current_user.id, patient_id)
    narrative = (
        db.query(Narrative)
        .filter(Narrative.patient_id == patient_id)
        .order_by(Narrative.generated_at.desc())
        .first()
    )
    if not narrative:
        return None
    return {
        "week_start": str(narrative.week_start),
        "bullets": narrative.bullets,
        "generated_at": narrative.generated_at.isoformat() if narrative.generated_at else None,
    }


@router.get("/patient/{patient_id}/flags")
def patient_flags(
    patient_id: uuid.UUID,
    current_user: User = Depends(require_clinician),
    db: Session = Depends(get_db),
):
    _assert_linked(db, current_user.id, patient_id)
    flags = (
        db.query(DissonanceFlag)
        .filter(DissonanceFlag.patient_id == patient_id)
        .order_by(DissonanceFlag.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(f.id),
            "flag_type": f.flag_type,
            "self_report_val": f.self_report_val,
            "signal_val": f.signal_val,
            "severity": f.severity,
            "resolved": f.resolved,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in flags
    ]


@router.get("/patient/{patient_id}/protective-factors")
def patient_protective_factors(
    patient_id: uuid.UUID,
    current_user: User = Depends(require_clinician),
    db: Session = Depends(get_db),
):
    """Positive behavioral indicators from the patient's most recent scored session."""
    _assert_linked(db, current_user.id, patient_id)

    latest = (
        db.query(CheckInSession)
        .filter(
            CheckInSession.patient_id == patient_id,
            CheckInSession.completed_at.isnot(None),
            CheckInSession.abstained == False,
        )
        .order_by(CheckInSession.completed_at.desc())
        .first()
    )
    if not latest:
        return {"available": False, "factors": []}

    responses = (
        db.query(QuestionnaireResponse)
        .filter(QuestionnaireResponse.session_id == latest.id)
        .all()
    )
    response_map = {r.question_key: r.raw_value for r in responses}

    def calendar_count(key: str):
        val = response_map.get(key)
        if val is None:
            return None
        return len(val) if isinstance(val, list) else int(val)

    sleep_days = calendar_count("indirect_sleep_days")
    social_days = calendar_count("indirect_social_days")
    productive_days = calendar_count("indirect_productive_days")

    sleep_hours_raw = response_map.get("sleep_hours")
    sleep_hours = float(sleep_hours_raw) if sleep_hours_raw is not None else None

    factors = []

    if sleep_days is not None:
        strength = "strong" if sleep_days >= 5 else "moderate" if sleep_days >= 3 else "low"
        factors.append({
            "label": "Good sleep nights",
            "value": f"{sleep_days}/7",
            "strength": strength,
            "icon": "🌙",
        })

    if sleep_hours is not None:
        strength = "strong" if sleep_hours >= 7 else "moderate" if sleep_hours >= 5.5 else "low"
        factors.append({
            "label": "Avg. sleep duration",
            "value": f"{sleep_hours:.1f} hrs/night",
            "strength": strength,
            "icon": "⏱️",
        })

    if social_days is not None:
        strength = "strong" if social_days >= 4 else "moderate" if social_days >= 2 else "low"
        factors.append({
            "label": "Social engagement",
            "value": f"{social_days}/7 days",
            "strength": strength,
            "icon": "🤝",
        })

    if productive_days is not None:
        strength = "strong" if productive_days >= 4 else "moderate" if productive_days >= 2 else "low"
        factors.append({
            "label": "Productive days",
            "value": f"{productive_days}/7 days",
            "strength": strength,
            "icon": "✅",
        })

    return {
        "available": True,
        "session_date": latest.completed_at.isoformat() if latest.completed_at else None,
        "factors": factors,
    }


@router.get("/patient/{patient_id}/sessions")
def patient_sessions(
    patient_id: uuid.UUID,
    current_user: User = Depends(require_clinician),
    db: Session = Depends(get_db),
):
    from app.engine.questions import QUESTION_BANK
    _assert_linked(db, current_user.id, patient_id)

    PHQ_LABELS = ["Not at all", "Several days", "More than half the days", "Nearly every day"]
    DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    question_map = {q["key"]: q for q in QUESTION_BANK}

    sessions = (
        db.query(CheckInSession)
        .filter(CheckInSession.patient_id == patient_id)
        .order_by(CheckInSession.started_at.desc())
        .all()
    )

    result = []
    for s in sessions:
        if s.abstained:
            session_status = "abstained"
        elif s.completed_at:
            session_status = "done"
        else:
            session_status = "in_progress"

        responses = (
            db.query(QuestionnaireResponse)
            .filter(QuestionnaireResponse.session_id == s.id)
            .order_by(QuestionnaireResponse.answered_at)
            .all()
        )

        formatted_responses = []
        for r in responses:
            q_info = question_map.get(r.question_key, {})
            q_text = q_info.get("text", r.question_key)
            q_type = r.question_type

            if q_type == "phq9":
                try:
                    answer_label = PHQ_LABELS[int(r.raw_value)]
                except (IndexError, TypeError, ValueError):
                    answer_label = str(r.raw_value)
            elif q_type == "calendar":
                day_indices = r.raw_value if isinstance(r.raw_value, list) else []
                parts = []
                for i in day_indices:
                    if isinstance(i, str) and i in DAYS:
                        parts.append(i)
                    else:
                        try:
                            idx = int(i)
                            if 0 <= idx < 7:
                                parts.append(DAYS[idx])
                        except (TypeError, ValueError):
                            pass
                answer_label = ", ".join(parts) or "None selected"
            else:
                answer_label = str(r.raw_value)

            formatted_responses.append({
                "question_key": r.question_key,
                "question_text": q_text,
                "question_type": q_type,
                "raw_value": r.raw_value,
                "answer_label": answer_label,
            })

        result.append({
            "session_id": str(s.id),
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "status": session_status,
            "responses": formatted_responses,
        })

    return result


@router.post("/patient/{patient_id}/report")
def generate_patient_report(
    patient_id: uuid.UUID,
    weeks: int = Query(4, ge=1, le=12),
    current_user: User = Depends(require_clinician),
    db: Session = Depends(get_db),
):
    _assert_linked(db, current_user.id, patient_id)
    from app.services.report import build_report_context, generate_report

    patient = db.query(User).filter(User.id == patient_id).first()
    ctx = build_report_context(db, patient_id, weeks=weeks)
    report_data = generate_report(ctx)

    return {
        "patient_name": patient.full_name if patient else "",
        "generated_at": datetime.utcnow().isoformat(),
        "period_weeks": weeks,
        "period_start": ctx["period_start"],
        "period_end": ctx["period_end"],
        "adherence": ctx["adherence"],
        "domain_scores": ctx["domain_scores"],
        **report_data,
    }


@router.patch("/flag/{flag_id}/resolve", status_code=status.HTTP_200_OK)
def resolve_flag(
    flag_id: uuid.UUID,
    current_user: User = Depends(require_clinician),
    db: Session = Depends(get_db),
):
    flag = db.query(DissonanceFlag).filter(DissonanceFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    _assert_linked(db, current_user.id, flag.patient_id)
    flag.resolved = datetime.utcnow()
    db.commit()
    return {"status": "resolved"}
