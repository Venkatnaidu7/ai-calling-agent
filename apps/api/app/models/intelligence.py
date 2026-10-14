import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


def uid():
    return uuid.uuid4()


def utcnow():
    return datetime.now(timezone.utc)


class CallIntelligenceJob(Base):
    __tablename__ = 'call_intelligence_jobs'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), index=True)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('calls.id', ondelete='CASCADE'), unique=True)
    status: Mapped[str] = mapped_column(String(30), default='QUEUED', index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class CallActionItem(Base):
    __tablename__ = 'call_action_items'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), index=True)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('calls.id', ondelete='CASCADE'))
    description: Mapped[str] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(100))
    due_date: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default='OPEN')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (UniqueConstraint('call_id', 'description', name='uq_call_action_item'),)
