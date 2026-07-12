import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Narrative(Base):
    __tablename__ = "narratives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    week_start = Column(Date, nullable=False)     # ISO week start (Monday)
    bullets = Column(JSONB, nullable=False)       # list[str], 5–6 HPI bullet strings
    raw_llm_output = Column(Text, nullable=True)  # full LLM response for audit
    generated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    patient = relationship("User", back_populates="narratives")
