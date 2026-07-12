import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_clinician
from app.database import get_db
from app.models.clinician import ClinicianProfile
from app.models.link import LinkStatus, PatientClinicianLink
from app.models.patient import PatientProfile
from app.models.user import User
from app.schemas.clinician import ClinicianProfileResponse, ClinicianProfileUpdate, InviteResponse
from app.schemas.patient import PatientSummary

router = APIRouter(prefix="/clinicians", tags=["clinicians"])


@router.get("/me", response_model=ClinicianProfileResponse)
def get_my_profile(current_user: User = Depends(require_clinician), db: Session = Depends(get_db)):
    profile = db.query(ClinicianProfile).filter(ClinicianProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.patch("/me", response_model=ClinicianProfileResponse)
def update_my_profile(
    payload: ClinicianProfileUpdate,
    current_user: User = Depends(require_clinician),
    db: Session = Depends(get_db),
):
    profile = db.query(ClinicianProfile).filter(ClinicianProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.post("/invite", response_model=InviteResponse)
def create_invite(current_user: User = Depends(require_clinician), db: Session = Depends(get_db)):
    clinician = db.query(ClinicianProfile).filter(ClinicianProfile.user_id == current_user.id).first()
    if not clinician:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinician profile not found")

    link = PatientClinicianLink(
        clinician_id=clinician.id,
        invite_token=str(uuid.uuid4()),
        status=LinkStatus.PENDING,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return InviteResponse(invite_token=link.invite_token, link_id=link.id)


@router.get("/patients", response_model=List[PatientSummary])
def list_patients(current_user: User = Depends(require_clinician), db: Session = Depends(get_db)):
    clinician = db.query(ClinicianProfile).filter(ClinicianProfile.user_id == current_user.id).first()
    if not clinician:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinician profile not found")

    links = (
        db.query(PatientClinicianLink)
        .filter(
            PatientClinicianLink.clinician_id == clinician.id,
            PatientClinicianLink.status == LinkStatus.ACTIVE,
        )
        .all()
    )
    patient_ids = [link.patient_id for link in links]
    return db.query(PatientProfile).filter(PatientProfile.id.in_(patient_ids)).all()
