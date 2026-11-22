import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class QuestionSchema(BaseModel):
    key: str
    type: str  # "phq9" | "likert" | "calendar" | "numeric" | "text"
    text: str
    scale: Optional[dict] = None


class SessionStartResponse(BaseModel):
    session_id: uuid.UUID
    stage: Optional[str] = None  # see app/engine/stages.py
    questions: list[QuestionSchema]
    # Answers already saved in this check-in (so a refreshed page can restore them)
    answers: dict[str, Any] = {}


class RespondRequest(BaseModel):
    question_key: str
    raw_value: Any  # checked per question type in app/engine/questions.validate_answer
    response_time_ms: int = Field(ge=0, le=3_600_000)  # 0 ms – 1 hour


class SessionStatusResponse(BaseModel):
    status: str  # "in_progress" | "scoring" | "scored" | "abstained"
    domains: Optional[list[dict]] = None


class DomainScoreOut(BaseModel):
    domain: str
    score: float
    confidence: float
    computed_at: datetime

    model_config = {"from_attributes": True}


class DissonanceFlagOut(BaseModel):
    id: uuid.UUID
    flag_type: str
    self_report_val: str
    signal_val: str
    severity: str
    flagged_at: datetime
    resolved: Optional[str] = None

    model_config = {"from_attributes": True}


class NarrativeOut(BaseModel):
    week_start: Any  # date
    bullets: list[str]
    generated_at: datetime

    model_config = {"from_attributes": True}
