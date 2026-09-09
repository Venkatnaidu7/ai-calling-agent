from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.rest import Client

from app.db.session import get_db
from app.api.deps import tenant_id
from app.models import Call, Contact, PhoneNumber
from app.services.compliance import check_outbound
from app.core.config import get_settings

router = APIRouter(prefix='/calls', tags=['calls'])


def twilio_client() -> Client:
    s = get_settings()
    if not s.twilio_account_sid or not s.twilio_auth_token:
        raise HTTPException(503, 'Twilio is not configured')
    return Client(s.twilio_account_sid, s.twilio_auth_token)


def public_url(path: str) -> str:
    base = get_settings().public_base_url.rstrip('/')
    if not base.startswith('https://'):
        raise HTTPException(503, 'public_base_url must use HTTPS for Twilio voice webhooks')
    return f'{base}{path}'


@router.get('')
async def list_calls(status: str | None = Query(None, max_length=30), direction: str | None = Query(None, max_length=20), contact_id: UUID | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    stmt = select(Call).where(Call.tenant_id == UUID(t)).order_by(Call.created_at.desc()).offset(offset).limit(limit)
    if status: stmt = stmt.where(Call.status == status.upper())
    if direction: stmt = stmt.where(Call.direction == direction.upper())
    if contact_id: stmt = stmt.where(Call.contact_id == contact_id)
    return (await db.scalars(stmt)).all()


@router.get('/summary')
async def call_summary(t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    tid = UUID(t)
    total = await db.scalar(select(func.count(Call.id)).where(Call.tenant_id == tid)) or 0
    active = await db.scalar(select(func.count(Call.id)).where(Call.tenant_id == tid, Call.status.in_(['QUEUED', 'RINGING', 'IN_PROGRESS']))) or 0
    completed = await db.scalar(select(func.count(Call.id)).where(Call.tenant_id == tid, Call.status == 'COMPLETED')) or 0
    failed = await db.scalar(select(func.count(Call.id)).where(Call.tenant_id == tid, Call.status.in_(['FAILED', 'NO_ANSWER', 'BUSY']))) or 0
    return {'total': total, 'active': active, 'completed': completed, 'failed': failed}


@router.get('/{call_id}')
async def get_call(call_id: UUID, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    x = await db.scalar(select(Call).where(Call.id == call_id, Call.tenant_id == UUID(t)))
    if not x: raise HTTPException(404, 'Call not found')
    return x


@router.post('/{call_id}/hangup')
async def hangup(call_id: UUID, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    x = await db.scalar(select(Call).where(Call.id == call_id, Call.tenant_id == UUID(t)))
    if not x: raise HTTPException(404, 'Call not found')
    if x.status not in {'QUEUED', 'RINGING', 'IN_PROGRESS'}: raise HTTPException(409, 'Call is not active')
    if not x.provider_call_id: raise HTTPException(409, 'Provider call is not connected')
    try:
        twilio_client().calls(x.provider_call_id).update(status='completed')
    except Exception as exc:
        raise HTTPException(502, f'Unable to terminate provider call: {exc}')
    x.status = 'COMPLETED'; await db.commit()
    return {'call_id': str(x.id), 'status': x.status}


@router.post('/outbound')
async def outbound(contact_id: UUID, phone_number_id: UUID, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    s = get_settings()
    if not s.outbound_enabled: raise HTTPException(403, 'Outbound calling is disabled')
    tid = UUID(t)
    c = await db.scalar(select(Contact).where(Contact.id == contact_id, Contact.tenant_id == tid))
    pn = await db.scalar(select(PhoneNumber).where(PhoneNumber.id == phone_number_id, PhoneNumber.tenant_id == tid))
    if not c or not pn: raise HTTPException(404, 'Contact or phone number not found')
    if not pn.active or not (pn.capabilities or {}).get('outbound', True): raise HTTPException(403, 'Outbound calling is disabled for this phone number')
    gate, reason = await check_outbound(db, tid, contact_id)
    if gate != 'ALLOWED': raise HTTPException(403, reason)
    if not pn.agent_id: raise HTTPException(409, 'Phone number has no AI agent assigned')
    if not s.twilio_account_sid or not s.twilio_auth_token: raise HTTPException(503, 'Twilio is not configured')
    call = Call(tenant_id=tid, phone_number_id=pn.id, agent_id=pn.agent_id, contact_id=c.id, direction='OUTBOUND', from_number=pn.e164, to_number=c.phone, status='QUEUED')
    db.add(call); await db.flush()
    url = public_url(f'/api/v1/voice/twilio/outbound/{call.id}')
    status_url = public_url('/api/v1/voice/twilio/status')
    try:
        tw = twilio_client().calls.create(to=c.phone, from_=pn.e164, url=url, method='POST', status_callback=status_url, status_callback_method='POST', status_callback_event=['initiated', 'ringing', 'answered', 'completed'])
    except Exception as exc:
        await db.rollback()
        raise HTTPException(502, f'Unable to start Twilio call: {exc}')
    call.provider_call_id = tw.sid
    call.status = 'RINGING'
    await db.commit()
    return {'call_id': str(call.id), 'provider_call_id': tw.sid, 'status': call.status}
