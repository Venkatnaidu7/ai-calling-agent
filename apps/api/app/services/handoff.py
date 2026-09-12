from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from twilio.rest import Client as TwilioClient
from plivo import RestClient as PlivoClient
from app.core.config import get_settings
from app.models import HumanAgent, RoutingGroup, TransferDestination, BusinessHours, CallHandoff, PhoneNumber

ACTIVE_STATES = {'AVAILABLE', 'ONLINE', 'READY'}
HANDOFF_STATES = {'REQUESTED', 'TRANSFERRING', 'CONNECTED', 'FAILED'}
VOICE_PROVIDERS = {'twilio', 'plivo'}


async def select_destination(db: AsyncSession, tenant_id, routing_group_id=None):
    if routing_group_id:
        group = await db.scalar(select(RoutingGroup).where(RoutingGroup.id == routing_group_id, RoutingGroup.tenant_id == tenant_id))
        if not group:
            return None
        query = select(HumanAgent).where(HumanAgent.tenant_id == tenant_id, HumanAgent.status.in_(ACTIVE_STATES))
        strategy = (group.strategy or 'ROUND_ROBIN').upper()
        if strategy == 'PRIORITY':
            return await db.scalar(query.order_by(HumanAgent.priority.desc(), HumanAgent.updated_at.asc()).limit(1))
        return await db.scalar(query.order_by(HumanAgent.updated_at.asc(), HumanAgent.priority.desc()).limit(1))
    return await db.scalar(select(TransferDestination).where(TransferDestination.tenant_id == tenant_id).order_by(TransferDestination.created_at.asc()).limit(1))


def _window_contains(rule, current: str) -> bool:
    if isinstance(rule, dict):
        rule = [rule]
    if not isinstance(rule, list):
        return False
    for window in rule:
        if isinstance(window, dict):
            start, end = window.get('start'), window.get('end')
        elif isinstance(window, (list, tuple)) and len(window) == 2:
            start, end = window
        else:
            continue
        if not isinstance(start, str) or not isinstance(end, str):
            continue
        if start <= end and start <= current <= end:
            return True
        if start > end and (current >= start or current <= end):
            return True
    return False


async def is_business_hours(db: AsyncSession, tenant_id, now: datetime | None = None) -> bool:
    bh = await db.scalar(select(BusinessHours).where(BusinessHours.tenant_id == tenant_id))
    if not bh:
        return True
    try:
        zone = ZoneInfo(bh.timezone or 'UTC')
    except ZoneInfoNotFoundError:
        return False
    local = now.astimezone(zone) if now else datetime.now(zone)
    hours = bh.hours or {}
    current = local.strftime('%H:%M')
    today_rule = hours.get(local.strftime('%a').lower())
    if _window_contains(today_rule, current):
        return True
    previous = local - timedelta(days=1)
    previous_rule = hours.get(previous.strftime('%a').lower())
    if isinstance(previous_rule, dict):
        previous_rule = [previous_rule]
    if isinstance(previous_rule, list):
        for window in previous_rule:
            if isinstance(window, dict):
                start, end = window.get('start'), window.get('end')
            elif isinstance(window, (list, tuple)) and len(window) == 2:
                start, end = window
            else:
                continue
            if isinstance(start, str) and isinstance(end, str) and start > end and current <= end:
                return True
    return False


async def create_or_get_handoff(db: AsyncSession, tenant_id, call, destination, reason=None):
    handoff = await db.scalar(select(CallHandoff).where(CallHandoff.call_id == call.id, CallHandoff.tenant_id == tenant_id))
    if handoff:
        return handoff
    provider = await db.scalar(select(PhoneNumber.provider).where(PhoneNumber.id == call.phone_number_id, PhoneNumber.tenant_id == tenant_id))
    provider = (provider or '').lower()
    if provider not in VOICE_PROVIDERS:
        raise HTTPException(400, 'Unsupported voice provider')
    destination_id = destination.id if isinstance(destination, TransferDestination) else None
    handoff = CallHandoff(tenant_id=tenant_id, call_id=call.id, destination_id=destination_id, destination_phone=destination.phone, provider=provider, status='REQUESTED', reason=reason)
    db.add(handoff)
    try:
        await db.flush()
    except IntegrityError:
        # Concurrent API/model-tool requests for the same call must be idempotent.
        await db.rollback()
        handoff = await db.scalar(select(CallHandoff).where(CallHandoff.call_id == call.id, CallHandoff.tenant_id == tenant_id))
        if handoff:
            return handoff
        raise
    return handoff


async def start_transfer(db: AsyncSession, tenant_id, call, destination, reason=None):
    handoff = await create_or_get_handoff(db, tenant_id, call, destination, reason)
    if handoff.status in {'TRANSFERRING', 'CONNECTED'}:
        return handoff
    if handoff.status == 'FAILED':
        raise HTTPException(409, 'Human handoff has already failed for this call')
    if call.status not in {'QUEUED', 'RINGING', 'IN_PROGRESS'}:
        raise HTTPException(409, 'Call is not active')
    if not call.provider_call_id:
        raise HTTPException(409, 'Provider call is not connected')
    base = get_settings().public_base_url.rstrip('/')
    if not base.startswith('https://'):
        raise HTTPException(503, 'public_base_url must use HTTPS for voice transfer')
    provider = handoff.provider
    try:
        if provider == 'twilio':
            s = get_settings()
            if not s.twilio_account_sid or not s.twilio_auth_token:
                raise HTTPException(503, 'Twilio is not configured')
            url = f'{base}/api/v1/handoff/twilio/execute/{call.id}'
            TwilioClient(s.twilio_account_sid, s.twilio_auth_token).calls(call.provider_call_id).update(url=url, method='POST')
        elif provider == 'plivo':
            s = get_settings()
            if not s.plivo_auth_id or not s.plivo_auth_token:
                raise HTTPException(503, 'Plivo is not configured')
            url = f'{base}/api/v1/handoff/plivo/execute/{call.id}'
            PlivoClient(s.plivo_auth_id, s.plivo_auth_token).calls.update(call.provider_call_id, legs='aleg', aleg_url=url, aleg_method='POST')
        else:
            raise HTTPException(400, 'Unsupported voice provider')
    except HTTPException:
        raise
    except Exception as exc:
        handoff.status = 'FAILED'
        handoff.failure_reason = str(exc)[:1000]
        await db.flush()
        raise HTTPException(502, f'Unable to start {provider} human transfer')
    handoff.status = 'TRANSFERRING'
    call.outcome = 'HUMAN_HANDOFF'
    await db.flush()
    return handoff


async def sync_handoff_state(db: AsyncSession, call, provider_status: str):
    """Synchronize transfer state from provider callbacks, idempotently."""
    handoff = await db.scalar(select(CallHandoff).where(CallHandoff.call_id == call.id, CallHandoff.tenant_id == call.tenant_id))
    if not handoff:
        return None
    status = (provider_status or '').upper().replace(' ', '-')
    if handoff.status == 'FAILED' or handoff.status == 'CONNECTED':
        return handoff
    if status in {'ANSWERED', 'IN-PROGRESS', 'IN_PROGRESS'}:
        handoff.status = 'CONNECTED'
        handoff.failure_reason = None
    elif status in {'RINGING', 'EARLY-MEDIA'}:
        handoff.status = 'TRANSFERRING'
    elif status in {'COMPLETED', 'BUSY', 'NO-ANSWER', 'NO_ANSWER', 'FAILED', 'CANCELED', 'CANCELLED'}:
        handoff.status = 'FAILED'
        handoff.failure_reason = status
    return handoff
