import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import SessionLocal, get_db
from app.models import Agent, AgentVersion, Call, Campaign, CampaignAttempt, CampaignContact, Contact, PhoneNumber
from app.providers.openai_realtime import RealtimeBridge
from app.providers.twilio import connect_stream_xml, validate_twilio, validate_twilio_ws

router = APIRouter(tags=['voice'])

STATUS_MAP = {'queued': 'QUEUED', 'initiated': 'QUEUED', 'ringing': 'RINGING', 'answered': 'IN_PROGRESS', 'in-progress': 'IN_PROGRESS', 'completed': 'COMPLETED', 'busy': 'BUSY', 'no-answer': 'NO_ANSWER', 'failed': 'FAILED', 'canceled': 'FAILED'}
TERMINAL_CALL_STATES = {'COMPLETED', 'BUSY', 'NO_ANSWER', 'FAILED'}
RETRYABLE_CALL_STATES = {'BUSY', 'NO_ANSWER', 'FAILED'}


def stream_token(call_id):
    return hmac.new(get_settings().secret_key.encode(), str(call_id).encode(), hashlib.sha256).hexdigest()


def valid_stream_token(call_id, token):
    return hmac.compare_digest(stream_token(call_id), token or '')


def stream_url(call_id):
    base = get_settings().public_base_url.rstrip('/')
    if not base.startswith('https://'):
        raise HTTPException(503, 'public_base_url must use HTTPS for Twilio Media Streams')
    return base.replace('https://', 'wss://', 1) + f'/api/v1/voice/stream/{call_id}?token={stream_token(call_id)}'


def stream_response(call_id):
    xml = connect_stream_xml(stream_url(call_id), {'call_id': call_id})
    return Response(content=xml, media_type='application/xml')


async def load_agent_version(db: AsyncSession, pn: PhoneNumber):
    if not pn.agent_id:
        raise HTTPException(503, 'Phone number has no AI agent assigned')
    agent = await db.scalar(select(Agent).where(Agent.id == pn.agent_id, Agent.tenant_id == pn.tenant_id, Agent.active == True))
    if not agent or not agent.active_version_id:
        raise HTTPException(503, 'Agent unavailable')
    version = await db.scalar(select(AgentVersion).where(AgentVersion.id == agent.active_version_id, AgentVersion.tenant_id == pn.tenant_id, AgentVersion.status == 'PUBLISHED'))
    if not version:
        raise HTTPException(503, 'Published agent unavailable')
    return agent, version


async def create_inbound_call(form, pn, db):
    agent, version = await load_agent_version(db, pn)
    contact = await db.scalar(select(Contact).where(Contact.tenant_id == pn.tenant_id, Contact.phone == form.get('From'), Contact.status.notin_(['ARCHIVED'])))
    call = Call(tenant_id=pn.tenant_id, agent_id=agent.id, agent_version_id=version.id, phone_number_id=pn.id, contact_id=contact.id if contact else None, provider_call_id=form.get('CallSid'), direction='INBOUND', from_number=form.get('From'), to_number=form.get('To'), status='IN_PROGRESS')
    db.add(call)
    await db.commit()
    return call


@router.post('/twilio/inbound')
async def inbound(request: Request, db: AsyncSession = Depends(get_db)):
    form = dict(await request.form())
    validate_twilio(request, form)
    to = form.get('To')
    pn = await db.scalar(select(PhoneNumber).where(PhoneNumber.e164 == to, PhoneNumber.active == True, PhoneNumber.provider == 'twilio'))
    if not pn: raise HTTPException(404, 'Phone number not configured')
    if not (pn.capabilities or {}).get('inbound', True): raise HTTPException(403, 'Inbound calling is disabled for this phone number')
    call = await create_inbound_call(form, pn, db)
    return stream_response(call.id)


@router.post('/twilio/outbound/{call_id}')
async def outbound(call_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    form = dict(await request.form())
    validate_twilio(request, form)
    call = await db.scalar(select(Call).where(Call.id == call_id, Call.provider_call_id == form.get('CallSid')))
    if not call: raise HTTPException(404, 'Call not found')
    if call.direction != 'OUTBOUND': raise HTTPException(409, 'Call direction mismatch')
    call.status = 'IN_PROGRESS'
    await db.commit()
    return stream_response(call.id)


@router.post('/twilio/status')
async def status(request: Request, db: AsyncSession = Depends(get_db)):
    form = dict(await request.form())
    validate_twilio(request, form)
    call = await db.scalar(select(Call).where(Call.provider_call_id == form.get('CallSid')))
    if not call: return {'ok': True}
    new_status = STATUS_MAP.get((form.get('CallStatus') or '').lower(), call.status)
    was_terminal = call.status in TERMINAL_CALL_STATES
    call.status = new_status
    if form.get('CallDuration'):
        try: call.duration_seconds = int(form['CallDuration'])
        except ValueError: pass
    if form.get('RecordingUrl'): call.recording_url = form['RecordingUrl']
    if new_status in TERMINAL_CALL_STATES:
        call.ended_at = datetime.now(timezone.utc)

    should_continue = False
    if call.direction == 'OUTBOUND' and new_status in TERMINAL_CALL_STATES and not was_terminal:
        attempt = await db.scalar(select(CampaignAttempt).where(CampaignAttempt.call_id == call.id).order_by(CampaignAttempt.created_at.desc()))
        if attempt:
            campaign = await db.scalar(select(Campaign).where(Campaign.id == attempt.campaign_id, Campaign.tenant_id == call.tenant_id))
            item = await db.scalar(select(CampaignContact).where(CampaignContact.campaign_id == attempt.campaign_id, CampaignContact.contact_id == attempt.contact_id, CampaignContact.tenant_id == call.tenant_id))
            if campaign and item:
                max_attempts = int((campaign.retry_policy or {}).get('max_attempts', 3))
                if new_status == 'COMPLETED':
                    item.state = 'COMPLETED'; attempt.state = 'COMPLETED'
                elif new_status in RETRYABLE_CALL_STATES and item.attempts < max_attempts:
                    item.state = 'RETRY'; attempt.state = 'RETRY'; attempt.error_code = new_status
                else:
                    item.state = 'FAILED'; attempt.state = 'FAILED'; attempt.error_code = new_status
                queued = await db.scalar(select(CampaignContact.id).where(CampaignContact.campaign_id == campaign.id, CampaignContact.tenant_id == call.tenant_id, CampaignContact.state.in_(['QUEUED', 'RETRY'])).limit(1))
                in_progress = await db.scalar(select(CampaignContact.id).where(CampaignContact.campaign_id == campaign.id, CampaignContact.tenant_id == call.tenant_id, CampaignContact.state == 'IN_PROGRESS').limit(1))
                if not queued and not in_progress:
                    campaign.status = 'COMPLETED'
                else:
                    should_continue = campaign.status == 'ACTIVE'
    await db.commit()
    if should_continue:
        from app.workers.tasks import process_campaign
        retry_delay = int((attempt.campaign.retry_policy if attempt else {}).get('backoff_minutes', 0) * 60) if False else 0
        process_campaign.apply_async(args=[str(attempt.campaign_id), str(call.tenant_id)], countdown=retry_delay)
    return {'ok': True}


@router.websocket('/stream/{call_id}')
async def stream(websocket: WebSocket, call_id: uuid.UUID, token: str | None = None):
    if not valid_stream_token(call_id, token):
        await websocket.close(code=1008); return
    try:
        validate_twilio_ws(websocket)
    except HTTPException:
        await websocket.close(code=1008); return
    await websocket.accept()
    bridge = None
    stream_sid = None
    task = None
    try:
        async with SessionLocal() as db:
            call = await db.scalar(select(Call).where(Call.id == call_id))
            if not call: await websocket.close(code=1008); return
            version = await db.scalar(select(AgentVersion).where(AgentVersion.id == call.agent_version_id, AgentVersion.tenant_id == call.tenant_id, AgentVersion.status == 'PUBLISHED'))
        if not version:
            await websocket.close(code=1011); return
        settings = get_settings()
        if not settings.openai_api_key:
            await websocket.close(code=1011); return

        bridge = RealtimeBridge(version.system_instructions, version.voice, version.language)
        await bridge.connect()

        async def ai_loop():
            async for event in bridge.events():
                event_type = event.get('type')
                if event_type in {'response.output_audio.delta', 'response.audio.delta'} and stream_sid and event.get('delta'):
                    await websocket.send_text(json.dumps({'event': 'media', 'streamSid': stream_sid, 'media': {'payload': event['delta']}}))
                elif event_type == 'input_audio_buffer.speech_started':
                    await bridge.cancel()
                elif event_type == 'error':
                    raise RuntimeError(event.get('error', {}).get('message', 'OpenAI Realtime error'))

        while True:
            message = json.loads(await websocket.receive_text())
            event_type = message.get('event')
            if event_type == 'start':
                stream_sid = message['start']['streamSid']
                task = asyncio.create_task(ai_loop())
                await bridge.create_response()
            elif event_type == 'media':
                await bridge.send_audio(message['media']['payload'])
            elif event_type == 'stop':
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if task: task.cancel()
        if bridge: await bridge.close()
        try:
            async with SessionLocal() as db:
                call = await db.scalar(select(Call).where(Call.id == call_id))
                if call and call.status in {'QUEUED', 'RINGING', 'IN_PROGRESS'}:
                    call.status = 'COMPLETED'
                    call.ended_at = datetime.now(timezone.utc)
                    await db.commit()
        except Exception:
            pass
