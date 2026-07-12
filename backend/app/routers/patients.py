from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_patient
from app.database import get_db
from app.models.link import LinkStatus, PatientClinicianLink
from app.models.patient import PatientProfile
from app.models.user import User
from app.schemas.patient import PatientProfileResponse, PatientProfileUpdate

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/me", response_model=PatientProfileResponse)
def get_my_profile(current_user: User = Depends(require_patient), db: Session = Depends(get_db)):
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.patch("/me", response_model=PatientProfileResponse)
def update_my_profile(
    payload: PatientProfileUpdate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.post("/accept-invite/{token}", status_code=status.HTTP_200_OK)
def accept_invite(
    token: str,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    link = (
        db.query(PatientClinicianLink)
        .filter(
            PatientClinicianLink.invite_token == token,
            PatientClinicianLink.status == LinkStatus.PENDING,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired invite")

    patient = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    already_linked = (
        db.query(PatientClinicianLink)
        .filter(
            PatientClinicianLink.patient_id == patient.id,
            PatientClinicianLink.clinician_id == link.clinician_id,
            PatientClinicianLink.status == LinkStatus.ACTIVE,
        )
        .first()
    )
    if already_linked:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already linked to this clinician")

    link.patient_id = patient.id
    link.status = LinkStatus.ACTIVE
    link.linked_at = datetime.utcnow()
    db.commit()
    return {"message": "Successfully linked to clinician"}
