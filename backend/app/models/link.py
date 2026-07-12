from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ClinicianPatient(Base):
    __tablename__ = "clinician_patient"

    clinician_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    linked_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    clinician = relationship("User", foreign_keys=[clinician_id], back_populates="clinician_links")
    patient = relationship("User", foreign_keys=[patient_id], back_populates="patient_links")
