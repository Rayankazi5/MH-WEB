import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    consented_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    version = Column(Text, nullable=False, default="1.0")
    ip_address = Column(Text)
    withdrawn_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, nullable=False, default=True)
