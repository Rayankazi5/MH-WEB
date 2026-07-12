from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import require_patient
from app.database import get_db
from app.models.consent import ConsentRecord
from app.models.push_token import PushToken
from app.models.user import User

router = APIRouter(prefix="/patient", tags=["patient"])


class ConsentRequest(BaseModel):
    version: str = "1.0"


class PushTokenRequest(BaseModel):
    token: str
    platform: str  # 'ios' | 'android'


@router.post("/consent", status_code=status.HTTP_200_OK)
def record_consent(
    payload: ConsentRequest,
    request: Request,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    existing = db.query(ConsentRecord).filter(ConsentRecord.user_id == current_user.id).first()
    ip = request.client.host if request.client else None

    if existing:
        existing.consented_at = datetime.utcnow()
        existing.version = payload.version
        existing.ip_address = ip
        existing.withdrawn_at = None
        existing.is_active = True
    else:
        db.add(ConsentRecord(
            user_id=current_user.id,
            version=payload.version,
            ip_address=ip,
        ))
    db.commit()
    return {"status": "consented", "version": payload.version}


@router.get("/consent")
def get_consent(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    record = db.query(ConsentRecord).filter(ConsentRecord.user_id == current_user.id).first()
    if not record or not record.is_active:
        return {"consented": False}
    return {
        "consented": True,
        "version": record.version,
        "consented_at": record.consented_at.isoformat(),
    }


@router.delete("/account", status_code=status.HTTP_200_OK)
def delete_account(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    """GDPR/PIPEDA right-to-erasure: deactivate and anonymise the account."""
    current_user.is_active = False
    current_user.email = f"deleted_{current_user.id}@deleted"
    current_user.full_name = "Deleted User"
    current_user.password_hash = ""

    # Withdraw consent record
    record = db.query(ConsentRecord).filter(ConsentRecord.user_id == current_user.id).first()
    if record:
        record.is_active = False
        record.withdrawn_at = datetime.utcnow()

    db.commit()
    return {"status": "deleted"}


@router.post("/push-token", status_code=status.HTTP_200_OK)
def register_push_token(
    payload: PushTokenRequest,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    if payload.platform not in ("ios", "android"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="platform must be 'ios' or 'android'")

    existing = (
        db.query(PushToken)
        .filter(PushToken.user_id == current_user.id, PushToken.token == payload.token)
        .first()
    )
    if not existing:
        db.add(PushToken(user_id=current_user.id, token=payload.token, platform=payload.platform))
        db.commit()
    return {"status": "registered"}
