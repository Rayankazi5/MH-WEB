import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class DomainScore(Base):
    __tablename__ = "domain_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    domain = Column(Text, nullable=False)
    score = Column(Float, nullable=False)       # 0.0 – 1.0 (softmax-normalised)
    confidence = Column(Float, nullable=False)  # 1 - epistemic_uncertainty
    computed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    session = relationship("Session", back_populates="domain_scores")
    patient = relationship("User", back_populates="domain_scores")


Index("idx_domain_scores_patient", DomainScore.patient_id, DomainScore.computed_at.desc())
