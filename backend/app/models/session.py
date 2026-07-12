import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    device_type = Column(String, nullable=True)  # "mobile" | "web"
    abstained = Column(Boolean, default=False, nullable=False)
    uncertainty_val = Column(Float, nullable=True)

    patient = relationship("User", back_populates="sessions", foreign_keys=[patient_id])
    responses = relationship("QuestionnaireResponse", back_populates="session", cascade="all, delete-orphan")
    journal_entries = relationship("JournalEntry", back_populates="session", cascade="all, delete-orphan")
    domain_scores = relationship("DomainScore", back_populates="session", cascade="all, delete-orphan")
    dissonance_flags = relationship("DissonanceFlag", back_populates="session", cascade="all, delete-orphan")


class QuestionnaireResponse(Base):
    __tablename__ = "questionnaire_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    question_key = Column(Text, nullable=False)
    question_type = Column(Text, nullable=False)  # "phq9" | "indirect" | "calendar" | "numeric"
    raw_value = Column(JSONB, nullable=False)
    normalised_val = Column(Float, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    answered_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    session = relationship("Session", back_populates="responses")
