from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import HumanAgent, RoutingGroup, TransferDestination, BusinessHours

ACTIVE_STATES = {"AVAILABLE", "ONLINE", "READY"}

async def select_destination(db: AsyncSession, tenant_id, routing_group_id=None):
    if routing_group_id:
        group = await db.scalar(select(RoutingGroup).where(RoutingGroup.id == routing_group_id, RoutingGroup.tenant_id == tenant_id))
        if not group:
            return None
        agents = (await db.scalars(select(HumanAgent).where(HumanAgent.tenant_id == tenant_id, HumanAgent.status.in_(ACTIVE_STATES)).order_by(HumanAgent.priority.desc(), HumanAgent.updated_at.asc()))).all()
        return agents[0] if agents else None
    return await db.scalar(select(TransferDestination).where(TransferDestination.tenant_id == tenant_id).order_by(TransferDestination.created_at.asc()).limit(1))

async def is_business_hours(db: AsyncSession, tenant_id, now: datetime | None = None) -> bool:
    bh = await db.scalar(select(BusinessHours).where(BusinessHours.tenant_id == tenant_id))
    if not bh:
        return True
    now = now or datetime.now(bh.timezone and __import__('zoneinfo').ZoneInfo(bh.timezone))
    day = now.strftime('%a').lower()
    rule = (bh.hours or {}).get(day)
    if not rule:
        return False
    return any(str(start) <= now.strftime('%H:%M') <= str(end) for start, end in rule if isinstance(rule, list))
