import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class PatientListItem(BaseModel):
    patient_id: uuid.UUID
    name: str
    last_session: Optional[datetime]
    risk_flag: bool  # True if any HIGH severity unresolved dissonance flag


class ScorePoint(BaseModel):
    date: datetime
    score: float
    confidence: float


class PatientSummary(BaseModel):
    patient_id: uuid.UUID
    name: str
    domain_scores: dict[str, list[ScorePoint]]  # domain → last-4-weeks points
    latest_narrative: Optional[dict]
    open_flags: list[dict]


class LinkRequest(BaseModel):
    patient_email: str


class ResolveRequest(BaseModel):
    note: Optional[str] = None
