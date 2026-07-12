import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body_encrypted = Column(Text, nullable=False)  # AES-256-GCM ciphertext
    keyword_vector = Column(JSONB, nullable=True)  # { cluster_name: frequency_score }
    sentiment_score = Column(Float, nullable=True)  # VADER compound mapped to [0, 1]
    word_count = Column(Integer, nullable=True)
    source = Column(String(20), nullable=True)  # 'chat' | 'solo' | None (legacy)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    session = relationship("Session", back_populates="journal_entries")
    patient = relationship("User", back_populates="journal_entries", foreign_keys=[patient_id])
