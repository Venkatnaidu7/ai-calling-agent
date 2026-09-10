import asyncio
from uuid import UUID
from sqlalchemy import select
from twilio.rest import Client

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Agent, AgentVersion, Call, Campaign, CampaignAttempt, CampaignContact, Contact, PhoneNumber
from app.services.compliance import check_outbound


async def run_campaign(campaign_id: str, tenant_id: str):
    s = get_settings()
    if not s.outbound_enabled or not s.twilio_account_sid or not s.twilio_auth_token:
        return {'status': 'blocked', 'reason': 'OUTBOUND_NOT_READY'}
    tid, cid = UUID(tenant_id), UUID(campaign_id)
    async with SessionLocal() as db:
        campaign = await db.scalar(select(Campaign).where(Campaign.id == cid, Campaign.tenant_id == tid))
        if not campaign or campaign.status != 'ACTIVE': return {'status': 'stopped'}
        phone_id = (campaign.schedule or {}).get('phone_number_id')
        if not phone_id: return {'status': 'blocked', 'reason': 'PHONE_NUMBER_REQUIRED'}
        pn = await db.scalar(select(PhoneNumber).where(PhoneNumber.id == UUID(phone_id), PhoneNumber.tenant_id == tid, PhoneNumber.active == True))
        if not pn or not (pn.capabilities or {}).get('outbound', True): return {'status': 'blocked', 'reason': 'PHONE_OUTBOUND_DISABLED'}
        agent = await db.scalar(select(Agent).where(Agent.id == pn.agent_id, Agent.tenant_id == tid, Agent.active == True))
        if not agent or not agent.active_version_id: return {'status': 'blocked', 'reason': 'AGENT_NOT_PUBLISHED'}
        version = await db.scalar(select(AgentVersion).where(AgentVersion.id == agent.active_version_id, AgentVersion.agent_id == agent.id, AgentVersion.tenant_id == tid, AgentVersion.status == 'PUBLISHED'))
        if not version: return {'status': 'blocked', 'reason': 'AGENT_NOT_PUBLISHED'}
        rows = (await db.scalars(select(CampaignContact).where(CampaignContact.campaign_id == cid, CampaignContact.tenant_id == tid, CampaignContact.state.in_(['QUEUED', 'RETRY'])).order_by(CampaignContact.created_at.asc()).limit(campaign.concurrency))).all()
        client = Client(s.twilio_account_sid, s.twilio_auth_token)
        launched = 0
        for item in rows:
            contact = await db.scalar(select(Contact).where(Contact.id == item.contact_id, Contact.tenant_id == tid))
            if not contact or not contact.phone:
                item.state = 'FAILED'; continue
            gate, reason = await check_outbound(db, tid, contact.id)
            if gate != 'ALLOWED':
                item.state = 'FAILED'; db.add(CampaignAttempt(tenant_id=tid, campaign_id=cid, contact_id=contact.id, state='BLOCKED', error_code=reason)); continue
            item.state = 'IN_PROGRESS'; item.attempts += 1
            call = Call(tenant_id=tid, phone_number_id=pn.id, agent_id=agent.id, agent_version_id=version.id, contact_id=contact.id, direction='OUTBOUND', from_number=pn.e164, to_number=contact.phone, status='QUEUED')
            db.add(call); await db.flush()
            attempt = CampaignAttempt(tenant_id=tid, campaign_id=cid, contact_id=contact.id, call_id=call.id, state='STARTING'); db.add(attempt)
            try:
                base = s.public_base_url.rstrip('/')
                if not base.startswith('https://'): raise RuntimeError('PUBLIC_BASE_URL must use HTTPS')
                tw = client.calls.create(to=contact.phone, from_=pn.e164, url=f'{base}/api/v1/voice/twilio/outbound/{call.id}', method='POST', status_callback=f'{base}/api/v1/voice/twilio/status', status_callback_method='POST', status_callback_event=['initiated', 'ringing', 'answered', 'completed'])
                call.provider_call_id = tw.sid; call.status = 'RINGING'; attempt.state = 'STARTED'; launched += 1
            except Exception as exc:
                call.status = 'FAILED'; attempt.state = 'FAILED'; attempt.error_code = type(exc).__name__; item.state = 'RETRY' if item.attempts < int((campaign.retry_policy or {}).get('max_attempts', 3)) else 'FAILED'
        await db.commit()
        return {'status': 'ok', 'launched': launched}


def run_campaign_sync(campaign_id: str, tenant_id: str):
    return asyncio.run(run_campaign(campaign_id, tenant_id))
