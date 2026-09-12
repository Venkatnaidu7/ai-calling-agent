from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import HumanAgent, RoutingGroup, TransferDestination, BusinessHours, CallHandoff, PhoneNumber

ACTIVE_STATES = {'AVAILABLE', 'ONLINE', 'READY'}

async def select_destination(db: AsyncSession, tenant_id, routing_group_id=None):
    if routing_group_id:
        group = await db.scalar(select(RoutingGroup).where(RoutingGroup.id == routing_group_id, RoutingGroup.tenant_id == tenant_id))
        if not group:
            return None
        query = select(HumanAgent).where(HumanAgent.tenant_id == tenant_id, HumanAgent.status.in_(ACTIVE_STATES))
        if group.strategy == 'ROUND_ROBIN':
            return await db.scalar(query.order_by(HumanAgent.updated_at.asc(), HumanAgent.priority.desc()).limit(1))
        return await db.scalar(query.order_by(HumanAgent.priority.desc(), HumanAgent.updated_at.asc()).limit(1))
    return await db.scalar(select(TransferDestination).where(TransferDestination.tenant_id == tenant_id).order_by(TransferDestination.created_at.asc()).limit(1))

async def is_business_hours(db: AsyncSession, tenant_id, now: datetime | None = None) -> bool:
    bh = await db.scalar(select(BusinessHours).where(BusinessHours.tenant_id == tenant_id))
    if not bh:
        return True
    local = now.astimezone(ZoneInfo(bh.timezone or 'UTC')) if now else datetime.now(ZoneInfo(bh.timezone or 'UTC'))
    rule = (bh.hours or {}).get(local.strftime('%a').lower())
    if not isinstance(rule, list):
        return False
    current = local.strftime('%H:%M')
    return any(isinstance(window, (list, tuple)) and len(window) == 2 and str(window[0]) <= current <= str(window[1]) for window in rule)

async def create_or_get_handoff(db: AsyncSession, tenant_id, call, destination, reason=None):
    handoff = await db.scalar(select(CallHandoff).where(CallHandoff.call_id == call.id, CallHandoff.tenant_id == tenant_id))
    if handoff:
        return handoff
    provider = await db.scalar(select(PhoneNumber.provider).where(PhoneNumber.id == call.phone_number_id, PhoneNumber.tenant_id == tenant_id)) or 'twilio'
    handoff = CallHandoff(tenant_id=tenant_id, call_id=call.id, destination_id=getattr(destination, 'id', None), destination_phone=destination.phone, provider=provider, status='REQUESTED', reason=reason)
    db.add(handoff)
    await db.flush()
    return handoff
