import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class DissonanceFlag(Base):
    __tablename__ = "dissonance_flags"
    __table_args__ = (CheckConstraint("severity IN ('low', 'medium', 'high')", name="flags_severity_check"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    flag_type = Column(Text, nullable=False)      # "sleep_late_activity" | "mood_movement" | etc.
    self_report_val = Column(Text, nullable=False)
    signal_val = Column(Text, nullable=False)
    severity = Column(Text, nullable=False)
    resolved = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    session = relationship("Session", back_populates="dissonance_flags")
    patient = relationship("User", back_populates="dissonance_flags")
