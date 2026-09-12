from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import tenant_id
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Campaign, CampaignContact, Contact, PhoneNumber
from app.schemas.campaign import CampaignContactAdd, CampaignContactOut, CampaignCreate, CampaignOut, CampaignStats, CampaignUpdate
from app.workers.tasks import process_campaign

router = APIRouter(prefix='/campaigns', tags=['campaigns'])


def as_campaign(x: Campaign) -> CampaignOut:
    return CampaignOut.model_validate(x)


async def get_campaign(campaign_id: UUID, tenant: str, db: AsyncSession) -> Campaign:
    x = await db.scalar(select(Campaign).where(Campaign.id == campaign_id, Campaign.tenant_id == UUID(tenant)))
    if not x:
        raise HTTPException(404, 'Campaign not found')
    return x


def phone_id(campaign: Campaign) -> UUID | None:
    value = (campaign.schedule or {}).get('phone_number_id')
    try:
        return UUID(str(value)) if value else None
    except (ValueError, TypeError):
        return None


def scheduled_start(schedule: dict | None):
    value = (schedule or {}).get('start_at')
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def provider_ready(provider: str, settings) -> bool:
    provider = provider.strip().lower()
    if provider == 'twilio':
        return bool(settings.twilio_account_sid and settings.twilio_auth_token)
    if provider == 'plivo':
        return bool(settings.plivo_auth_id and settings.plivo_auth_token)
    return False


async def campaign_phone(campaign: Campaign, tenant: str, db: AsyncSession) -> PhoneNumber:
    pid = phone_id(campaign)
    if not pid:
        raise HTTPException(409, 'Campaign has no phone number')
    pn = await db.scalar(select(PhoneNumber).where(PhoneNumber.id == pid, PhoneNumber.tenant_id == UUID(tenant), PhoneNumber.active == True))
    if not pn:
        raise HTTPException(409, 'Campaign phone number is not active')
    provider = (pn.provider or 'twilio').strip().lower()
    if provider not in {'twilio', 'plivo'}:
        raise HTTPException(400, f'Unsupported voice provider: {provider}')
    if not (pn.capabilities or {}).get('outbound', True):
        raise HTTPException(403, 'Outbound calling is disabled for this phone number')
    if not provider_ready(provider, get_settings()):
        raise HTTPException(503, f'{provider.title()} is not configured')
    return pn


@router.get('', response_model=list[CampaignOut])
async def list_campaigns(t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Campaign).where(Campaign.tenant_id == UUID(t)).order_by(Campaign.created_at.desc()))).all()
    return [as_campaign(x) for x in rows]


@router.post('', response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(data: CampaignCreate, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    tid = UUID(t)
    pn = await db.scalar(select(PhoneNumber).where(PhoneNumber.id == data.phone_number_id, PhoneNumber.tenant_id == tid))
    if not pn:
        raise HTTPException(404, 'Phone number not found')
    if (pn.provider or 'twilio').strip().lower() not in {'twilio', 'plivo'}:
        raise HTTPException(400, f'Unsupported voice provider: {pn.provider}')
    if not (pn.capabilities or {}).get('outbound', True):
        raise HTTPException(403, 'Outbound calling is disabled for this phone number')
    schedule = dict(data.schedule)
    schedule['phone_number_id'] = str(data.phone_number_id)
    x = Campaign(tenant_id=tid, name=data.name, schedule=schedule, retry_policy=data.retry_policy, concurrency=data.concurrency, status='DRAFT')
    db.add(x)
    await db.commit(); await db.refresh(x)
    return as_campaign(x)


@router.get('/{campaign_id}/contacts', response_model=list[CampaignContactOut])
async def list_contacts(campaign_id: UUID, state: str | None = Query(None, max_length=30), t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    x = await get_campaign(campaign_id, t, db)
    stmt = select(CampaignContact).where(CampaignContact.campaign_id == x.id, CampaignContact.tenant_id == UUID(t)).order_by(CampaignContact.created_at.asc())
    if state: stmt = stmt.where(CampaignContact.state == state.upper())
    return [CampaignContactOut.model_validate(i) for i in (await db.scalars(stmt)).all()]


@router.get('/{campaign_id}/stats', response_model=CampaignStats)
async def campaign_stats(campaign_id: UUID, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    x = await get_campaign(campaign_id, t, db); tid = UUID(t)
    rows = (await db.execute(select(CampaignContact.state, func.count(CampaignContact.id)).where(CampaignContact.campaign_id == x.id, CampaignContact.tenant_id == tid).group_by(CampaignContact.state))).all()
    counts = {state: int(n) for state, n in rows}
    return CampaignStats(total=sum(counts.values()), queued=counts.get('QUEUED', 0), in_progress=counts.get('IN_PROGRESS', 0), completed=counts.get('COMPLETED', 0), failed=counts.get('FAILED', 0), retryable=counts.get('RETRY', 0))


@router.post('/{campaign_id}/start', response_model=CampaignOut)
async def start_campaign(campaign_id: UUID, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    x = await get_campaign(campaign_id, t, db)
    if x.status in {'ACTIVE', 'SCHEDULED'}: return as_campaign(x)
    pn = await campaign_phone(x, t, db)
    s = get_settings()
    if not s.outbound_enabled: raise HTTPException(403, 'Outbound calling is disabled')
    count = await db.scalar(select(func.count(CampaignContact.id)).where(CampaignContact.campaign_id == x.id, CampaignContact.state.in_(['QUEUED', 'RETRY']))) or 0
    if count == 0: raise HTTPException(409, 'Campaign has no callable contacts queued')
    start_at = scheduled_start(x.schedule)
    x.status = 'SCHEDULED' if start_at and start_at > datetime.now(timezone.utc) else 'ACTIVE'
    await db.commit(); await db.refresh(x)
    process_campaign.delay(str(x.id), t)
    return as_campaign(x)


@router.post('/{campaign_id}/pause', response_model=CampaignOut)
async def pause_campaign(campaign_id: UUID, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    x = await get_campaign(campaign_id, t, db)
    if x.status not in {'ACTIVE', 'SCHEDULED'}: raise HTTPException(409, 'Campaign is not running')
    x.status = 'PAUSED'; await db.commit(); await db.refresh(x)
    return as_campaign(x)


@router.post('/{campaign_id}/resume', response_model=CampaignOut)
async def resume_campaign(campaign_id: UUID, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    x = await get_campaign(campaign_id, t, db)
    if x.status != 'PAUSED': raise HTTPException(409, 'Campaign is not paused')
    x.status = 'ACTIVE'; await db.commit(); await db.refresh(x)
    process_campaign.delay(str(x.id), t)
    return as_campaign(x)


@router.get('/{campaign_id}', response_model=CampaignOut)
async def get_campaign_endpoint(campaign_id: UUID, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    return as_campaign(await get_campaign(campaign_id, t, db))


@router.patch('/{campaign_id}', response_model=CampaignOut)
async def update_campaign(campaign_id: UUID, data: CampaignUpdate, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    x = await get_campaign(campaign_id, t, db)
    if x.status == 'ACTIVE': raise HTTPException(409, 'Pause the campaign before editing it')
    changes = data.model_dump(exclude_unset=True)
    if 'phone_number_id' in changes:
        pn = await db.scalar(select(PhoneNumber).where(PhoneNumber.id == changes['phone_number_id'], PhoneNumber.tenant_id == UUID(t)))
        if not pn: raise HTTPException(404, 'Phone number not found')
        if (pn.provider or 'twilio').strip().lower() not in {'twilio', 'plivo'}:
            raise HTTPException(400, f'Unsupported voice provider: {pn.provider}')
        schedule = dict(x.schedule or {}); schedule['phone_number_id'] = str(changes.pop('phone_number_id')); changes['schedule'] = schedule
    for k, v in changes.items(): setattr(x, k, v)
    await db.commit(); await db.refresh(x)
    return as_campaign(x)


@router.post('/{campaign_id}/contacts', response_model=list[CampaignContactOut])
async def add_contacts(campaign_id: UUID, data: CampaignContactAdd, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    x = await get_campaign(campaign_id, t, db)
    if x.status == 'ACTIVE': raise HTTPException(409, 'Pause the campaign before changing contacts')
    tid = UUID(t)
    contacts = (await db.scalars(select(Contact).where(Contact.id.in_(data.contact_ids), Contact.tenant_id == tid))).all()
    found = {c.id for c in contacts}; missing = [str(cid) for cid in data.contact_ids if cid not in found]
    if missing: raise HTTPException(404, f'Contacts not found: {", ".join(missing)}')
    existing = set((await db.scalars(select(CampaignContact.contact_id).where(CampaignContact.campaign_id == x.id, CampaignContact.contact_id.in_(data.contact_ids)))).all())
    added = []
    for c in contacts:
        if c.id in existing: continue
        item = CampaignContact(tenant_id=tid, campaign_id=x.id, contact_id=c.id, state='QUEUED', attempts=0); db.add(item); added.append(item)
    await db.commit()
    for item in added: await db.refresh(item)
    return [CampaignContactOut.model_validate(i) for i in added]
