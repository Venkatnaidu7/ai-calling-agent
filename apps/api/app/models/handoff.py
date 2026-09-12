import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

def uid():
    return uuid.uuid4()

def utcnow():
    return datetime.now(timezone.utc)

class CallHandoff(Base):
    __tablename__ = 'call_handoffs'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), index=True)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('calls.id', ondelete='CASCADE'), unique=True)
    destination_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('transfer_destinations.id'))
    destination_phone: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default='REQUESTED', index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
