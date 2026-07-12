import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import verify_internal
from app.database import get_db
from app.engine.scoring import run_scoring_pipeline
from app.models.narrative import Narrative
from app.models.user import User, ROLE_PATIENT
from app.services.narrative import build_narrative_context, generate_narrative

router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(verify_internal)])


@router.post("/score/{session_id}", status_code=status.HTTP_202_ACCEPTED)
def trigger_score(session_id: uuid.UUID):
    run_scoring_pipeline(str(session_id))
    return {"status": "complete", "session_id": str(session_id)}


@router.post("/narrative/{patient_id}", status_code=status.HTTP_202_ACCEPTED)
def trigger_narrative(
    patient_id: uuid.UUID,
    week_start: date = None,
    db: Session = Depends(get_db),
):
    patient = db.query(User).filter(User.id == patient_id, User.role == ROLE_PATIENT).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())  # Most recent Monday

    ctx = build_narrative_context(db, patient_id, week_start)
    if not ctx:
        return {"status": "no_data", "patient_id": str(patient_id)}

    bullets, raw_output = generate_narrative(ctx)

    narrative = Narrative(
        patient_id=patient_id,
        week_start=week_start,
        bullets=bullets,
        raw_llm_output=raw_output,
    )
    db.add(narrative)
    db.commit()
    return {"status": "generated", "patient_id": str(patient_id), "week_start": str(week_start), "bullets": bullets}
