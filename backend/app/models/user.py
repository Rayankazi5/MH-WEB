import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base

ROLE_PATIENT = "patient"
ROLE_CLINICIAN = "clinician"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('patient', 'clinician')", name="users_role_check"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String, nullable=False)
    full_name = Column(Text, nullable=False)
    timezone = Column(Text, nullable=False, default="UTC")
    is_active = Column(Boolean, nullable=False, default=True)

    sessions = relationship("Session", back_populates="patient", foreign_keys="Session.patient_id")
    journal_entries = relationship("JournalEntry", back_populates="patient", foreign_keys="JournalEntry.patient_id")
    domain_scores = relationship("DomainScore", back_populates="patient")
    narratives = relationship("Narrative", back_populates="patient")
    dissonance_flags = relationship("DissonanceFlag", back_populates="patient")

    clinician_links = relationship(
        "ClinicianPatient",
        foreign_keys="ClinicianPatient.clinician_id",
        back_populates="clinician",
    )
    patient_links = relationship(
        "ClinicianPatient",
        foreign_keys="ClinicianPatient.patient_id",
        back_populates="patient",
    )
