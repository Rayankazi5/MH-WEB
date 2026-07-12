import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JournalSubmitRequest(BaseModel):
    session_id: Optional[uuid.UUID] = None
    body: str
    source: Optional[str] = None  # 'chat' | 'solo'


class JournalEditRequest(BaseModel):
    body: str


class InsightRequest(BaseModel):
    keyword: Optional[str] = None   # one of: sleep, mood, anxiety, energy, social, overall
    free_text: Optional[str] = None  # voice-to-vent free input


class HistoryPoint(BaseModel):
    domain: str
    score: float
    confidence: float
    date: datetime

    model_config = {"from_attributes": True}
