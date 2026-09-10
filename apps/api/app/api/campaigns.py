from uuid import UUID
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
    schedule = dict(data.schedule)
    schedule['phone_number_id'] = str(data.phone_number_id)
    x = Campaign(tenant_id=tid, name=data.name, schedule=schedule, retry_policy=data.retry_policy, concurrency=data.concurrency, status='DRAFT')
    db.add(x)
    await db.commit(); await db.refresh(x)
    return as_campaign(x)


# Static sub-routes must be declared before /{campaign_id}.
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
    x = await get_campaign(campaign_id, t, db); s = get_settings()
    if x.status == 'ACTIVE': return as_campaign(x)
    if not phone_id(x): raise HTTPException(409, 'Campaign has no phone number')
    if not s.outbound_enabled: raise HTTPException(403, 'Outbound calling is disabled')
    if not s.twilio_account_sid or not s.twilio_auth_token: raise HTTPException(503, 'Twilio is not configured')
    count = await db.scalar(select(func.count(CampaignContact.id)).where(CampaignContact.campaign_id == x.id, CampaignContact.state.in_(['QUEUED', 'RETRY']))) or 0
    if count == 0: raise HTTPException(409, 'Campaign has no callable contacts queued')
    x.status = 'ACTIVE'; await db.commit(); await db.refresh(x)
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
