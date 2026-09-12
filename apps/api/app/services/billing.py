from calendar import monthrange
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Plan, Subscription, UsageRecord


def current_period() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(day=monthrange(now.year, now.month)[1], hour=23, minute=59, second=59, microsecond=999999)
    return start, end


async def current_usage(db: AsyncSession, tenant_id: UUID, metric: str = 'voice_minutes') -> float:
    start, end = current_period()
    value = await db.scalar(
        select(func.coalesce(func.sum(UsageRecord.quantity), 0)).where(
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.metric == metric,
            UsageRecord.period_start == start,
            UsageRecord.period_end == end,
        )
    )
    return float(value or 0)


async def enforce_call_limit(db: AsyncSession, tenant_id: UUID) -> None:
    sub = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant_id))
    if not sub or not sub.plan_id or sub.status in {'CANCELED', 'UNPAID', 'PAST_DUE'}:
        if sub and sub.status in {'CANCELED', 'UNPAID', 'PAST_DUE'}:
            raise HTTPException(402, 'Active billing subscription required')
        return
    plan = await db.scalar(select(Plan).where(Plan.id == sub.plan_id))
    if not plan:
        raise HTTPException(402, 'Billing plan is unavailable')
    limit = (plan.limits or {}).get('minutes')
    if limit is None:
        return
    used = await current_usage(db, tenant_id)
    if used >= float(limit):
        raise HTTPException(402, 'Monthly voice-minute limit reached')


async def record_voice_minutes(db: AsyncSession, tenant_id: UUID, seconds: int | None) -> UsageRecord | None:
    if seconds is None or seconds <= 0:
        return None
    start, end = current_period()
    record = UsageRecord(
        tenant_id=tenant_id,
        metric='voice_minutes',
        quantity=round(seconds / 60.0, 4),
        period_start=start,
        period_end=end,
    )
    db.add(record)
    return record
