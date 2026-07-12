from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import decode_token
from app.database import get_db
from app.models.user import User, ROLE_PATIENT, ROLE_CLINICIAN

bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_patient(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != ROLE_PATIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient access required")
    return current_user


def require_clinician(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != ROLE_CLINICIAN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clinician access required")
    return current_user


def verify_internal(x_internal_secret: str = Header(None)) -> None:
    settings = get_settings()
    if x_internal_secret != settings.internal_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Internal access only")
