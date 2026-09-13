import asyncio
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.db.session import SessionLocal, get_db
from app.models import Agent, AgentVersion, Call, Campaign, CampaignAttempt, CampaignContact, Contact, PhoneNumber, Transcript, TranscriptSegment
from app.providers.openai_realtime import RealtimeBridge, HANDOFF_TOOL
from app.providers.twilio import connect_stream_xml, validate_twilio, validate_twilio_ws
from app.services.call_intelligence import ensure_job
from app.services.handoff import select_destination, is_business_hours, start_transfer
from app.services.billing import record_voice_minutes

logger = logging.getLogger(__name__)
router = APIRouter(tags=['voice'])
STATUS_MAP={'queued':'QUEUED','initiated':'QUEUED','ringing':'RINGING','answered':'IN_PROGRESS','in-progress':'IN_PROGRESS','completed':'COMPLETED','busy':'BUSY','no-answer':'NO_ANSWER','failed':'FAILED','canceled':'FAILED'}
TERMINAL_CALL_STATES={'COMPLETED','BUSY','NO_ANSWER','FAILED'}
RETRYABLE_CALL_STATES={'BUSY','NO_ANSWER','FAILED'}

def stream_token(call_id): return hmac.new(get_settings().secret_key.encode(),str(call_id).encode(),hashlib.sha256).hexdigest()
def valid_stream_token(call_id,token): return hmac.compare_digest(stream_token(call_id),token or '')
def stream_url(call_id):
    base=get_settings().public_base_url.rstrip('/')
    if not base.startswith('https://'): raise HTTPException(503,'public_base_url must use HTTPS for Twilio Media Streams')
    return base.replace('https://','wss://',1)+f'/api/v1/voice/stream/{call_id}?token={stream_token(call_id)}'
def stream_response(call_id): return Response(content=connect_stream_xml(stream_url(call_id),{'call_id':call_id}),media_type='application/xml')

async def load_agent_version(db: AsyncSession,pn: PhoneNumber):
    if not pn.agent_id: raise HTTPException(503,'Phone number has no AI agent assigned')
    agent=await db.scalar(select(Agent).where(Agent.id==pn.agent_id,Agent.tenant_id==pn.tenant_id,Agent.active==True))
    if not agent or not agent.active_version_id: raise HTTPException(503,'Agent unavailable')
    version=await db.scalar(select(AgentVersion).where(AgentVersion.id==agent.active_version_id,AgentVersion.tenant_id==pn.tenant_id,AgentVersion.status=='PUBLISHED'))
    if not version: raise HTTPException(503,'Published agent unavailable')
    return agent,version

async def create_inbound_call(form,pn,db):
    agent,version=await load_agent_version(db,pn)
    contact=await db.scalar(select(Contact).where(Contact.tenant_id==pn.tenant_id,Contact.phone==form.get('From'),Contact.status.notin_(['ARCHIVED'])))
    call=Call(tenant_id=pn.tenant_id,agent_id=agent.id,agent_version_id=version.id,phone_number_id=pn.id,contact_id=contact.id if contact else None,provider_call_id=form.get('CallSid'),direction='INBOUND',from_number=form.get('From'),to_number=form.get('To'),status='IN_PROGRESS')
    db.add(call); await db.commit(); return call

async def execute_handoff_tool(call_id, tenant_id, arguments):
    try:
        call_uuid=uuid.UUID(str(call_id)); tid=uuid.UUID(str(tenant_id))
        reason=str(arguments.get('reason') or '').strip()[:1000]
        if not reason: return {'ok':False,'code':'REASON_REQUIRED','message':'A handoff reason is required.'}, False
        routing_group_id=arguments.get('routing_group_id'); destination_id=arguments.get('destination_id')
        rg=uuid.UUID(str(routing_group_id)) if routing_group_id else None
        did=uuid.UUID(str(destination_id)) if destination_id else None
    except (ValueError,TypeError,AttributeError):
        return {'ok':False,'code':'INVALID_ARGUMENTS','message':'Invalid handoff arguments.'}, False
    async with SessionLocal() as db:
        call=await db.scalar(select(Call).where(Call.id==call_uuid,Call.tenant_id==tid))
        if not call: return {'ok':False,'code':'CALL_NOT_FOUND','message':'The active call could not be found.'}, False
        if call.status not in {'QUEUED','RINGING','IN_PROGRESS'}: return {'ok':False,'code':'CALL_NOT_ACTIVE','message':'The call is no longer active.'}, False
        if not call.provider_call_id: return {'ok':False,'code':'PROVIDER_NOT_CONNECTED','message':'The voice provider is not connected.'}, False
        if not await is_business_hours(db,tid): return {'ok':False,'code':'OUTSIDE_BUSINESS_HOURS','message':'Human support is currently outside business hours.'}, False
        if did:
            from app.models import TransferDestination
            destination=await db.scalar(select(TransferDestination).where(TransferDestination.id==did,TransferDestination.tenant_id==tid))
        else: destination=await select_destination(db,tid,rg)
        if not destination: return {'ok':False,'code':'NO_AGENT_AVAILABLE','message':'No human support agent is currently available.'}, False
        try:
            handoff=await start_transfer(db,tid,call,destination,reason); await db.commit()
            return {'ok':True,'status':handoff.status,'destination':destination.name}, True
        except HTTPException as exc:
            await db.rollback(); return {'ok':False,'code':'TRANSFER_FAILED','message':str(exc.detail)}, False
        except Exception:
            await db.rollback(); logger.exception('handoff_tool_failed',extra={'call_id':str(call_uuid)})
            return {'ok':False,'code':'TRANSFER_FAILED','message':'Unable to start human transfer.'}, False

@router.post('/twilio/inbound')
async def inbound(request:Request,db:AsyncSession=Depends(get_db)):
    form=dict(await request.form()); validate_twilio(request,form); to=form.get('To')
    pn=await db.scalar(select(PhoneNumber).where(PhoneNumber.e164==to,PhoneNumber.active==True,PhoneNumber.provider=='twilio'))
    if not pn: raise HTTPException(404,'Phone number not configured')
    if not (pn.capabilities or {}).get('inbound',True): raise HTTPException(403,'Inbound calling is disabled for this phone number')
    return stream_response((await create_inbound_call(form,pn,db)).id)

@router.post('/twilio/outbound/{call_id}')
async def outbound(call_id:uuid.UUID,request:Request,db:AsyncSession=Depends(get_db)):
    form=dict(await request.form()); validate_twilio(request,form)
    call=await db.scalar(select(Call).where(Call.id==call_id,Call.provider_call_id==form.get('CallSid')))
    if not call: raise HTTPException(404,'Call not found')
    if call.direction!='OUTBOUND': raise HTTPException(409,'Call direction mismatch')
    call.status='IN_PROGRESS'; await db.commit(); return stream_response(call.id)

@router.post('/twilio/status')
async def status(request:Request,db:AsyncSession=Depends(get_db)):
    form=dict(await request.form()); validate_twilio(request,form)
    call=await db.scalar(select(Call).where(Call.provider_call_id==form.get('CallSid')))
    if not call: return {'ok':True}
    new_status=STATUS_MAP.get((form.get('CallStatus') or '').lower(),call.status); was_terminal=call.status in TERMINAL_CALL_STATES
    call.status=new_status
    if form.get('CallDuration'):
        try: call.duration_seconds=int(form['CallDuration'])
        except ValueError: pass
    if form.get('RecordingUrl'): call.recording_url=form['RecordingUrl']
    if new_status in TERMINAL_CALL_STATES: call.ended_at=datetime.now(timezone.utc)
    continue_campaign_id=None; retry_delay=0; intelligence=False
    if call.direction=='OUTBOUND' and new_status in TERMINAL_CALL_STATES and not was_terminal:
        await record_voice_minutes(db,call.tenant_id,call.duration_seconds)
        attempt=await db.scalar(select(CampaignAttempt).where(CampaignAttempt.call_id==call.id).order_by(CampaignAttempt.created_at.desc()))
        if attempt:
            campaign=await db.scalar(select(Campaign).where(Campaign.id==attempt.campaign_id,Campaign.tenant_id==call.tenant_id))
            item=await db.scalar(select(CampaignContact).where(CampaignContact.campaign_id==attempt.campaign_id,CampaignContact.contact_id==attempt.contact_id,CampaignContact.tenant_id==call.tenant_id))
            if campaign and item:
                max_attempts=max(1,int((campaign.retry_policy or {}).get('max_attempts',3)))
                if new_status=='COMPLETED': item.state,attempt.state='COMPLETED','COMPLETED'
                elif new_status in RETRYABLE_CALL_STATES and item.attempts<max_attempts: item.state,attempt.state,attempt.error_code='RETRY','RETRY',new_status; retry_delay=max(0,int((campaign.retry_policy or {}).get('backoff_minutes',0)))*60
                else: item.state,attempt.state,attempt.error_code='FAILED','FAILED',new_status
                queued=await db.scalar(select(CampaignContact.id).where(CampaignContact.campaign_id==campaign.id,CampaignContact.tenant_id==call.tenant_id,CampaignContact.state.in_(['QUEUED','RETRY'])).limit(1))
                active=await db.scalar(select(CampaignContact.id).where(CampaignContact.campaign_id==campaign.id,CampaignContact.tenant_id==call.tenant_id,CampaignContact.state=='IN_PROGRESS').limit(1))
                if not queued and not active: campaign.status='COMPLETED'
                elif campaign.status=='ACTIVE': continue_campaign_id=campaign.id
    if new_status in TERMINAL_CALL_STATES and get_settings().intelligence_enabled: await ensure_job(db,call.tenant_id,call.id); intelligence=True
    from app.services.handoff import sync_handoff_state
    await sync_handoff_state(db,call,form.get('CallStatus')); await db.commit()
    if continue_campaign_id:
        from app.workers.tasks import process_campaign
        process_campaign.apply_async(args=[str(continue_campaign_id),str(call.tenant_id)],countdown=retry_delay)
    if intelligence:
        from app.workers.tasks import process_call_intelligence
        process_call_intelligence.apply_async(args=[str(call.id)],countdown=5)
    return {'ok':True}

@router.websocket('/stream/{call_id}')
async def stream(websocket:WebSocket,call_id:uuid.UUID,token:str|None=None):
    if not valid_stream_token(call_id,token): await websocket.close(code=1008); return
    try: validate_twilio_ws(websocket)
    except HTTPException: await websocket.close(code=1008); return
    await websocket.accept(); bridge=None; stream_sid=None; task=None
    try:
        async with SessionLocal() as db:
            call=await db.scalar(select(Call).where(Call.id==call_id))
            if not call: await websocket.close(code=1008); return
            version=await db.scalar(select(AgentVersion).where(AgentVersion.id==call.agent_version_id,AgentVersion.tenant_id==call.tenant_id,AgentVersion.status=='PUBLISHED'))
            transcript=await db.scalar(select(Transcript).where(Transcript.call_id==call.id,Transcript.tenant_id==call.tenant_id))
            if not transcript:
                transcript=Transcript(tenant_id=call.tenant_id,call_id=call.id,language=version.language if version else None,status='PROCESSING'); db.add(transcript); await db.commit()
        if not version or not get_settings().openai_api_key: await websocket.close(code=1011); return
        bridge=RealtimeBridge(version.system_instructions,version.voice,version.language,[HANDOFF_TOOL]); await bridge.connect()
        async def ai_loop():
            async for event in bridge.events():
                kind=event.get('type')
                if kind in {'response.output_audio.delta','response.audio.delta'} and stream_sid and event.get('delta'): await websocket.send_text(json.dumps({'event':'media','streamSid':stream_sid,'media':{'payload':event['delta']}}))
                elif kind=='response.function_call_arguments.done' and event.get('name')=='transfer_to_human':
                    try: args=json.loads(event.get('arguments') or '{}')
                    except json.JSONDecodeError: args={}
                    result,success=await execute_handoff_tool(call_id,call.tenant_id,args); await bridge.tool_result(event.get('call_id'),result,create_response=not success)
                    if success: await bridge.close(); return
                elif kind in {'conversation.item.input_audio_transcription.completed','conversation.item.input_audio_transcription.segment'}:
                    text=event.get('transcript') or event.get('text')
                    if text:
                        async with SessionLocal() as db:
                            tr=await db.scalar(select(Transcript).where(Transcript.call_id==call_id,Transcript.tenant_id==call.tenant_id))
                            if tr:
                                if kind.endswith('.segment') and event.get('id'):
                                    existing=await db.scalar(select(TranscriptSegment).where(TranscriptSegment.transcript_id==tr.id,TranscriptSegment.tenant_id==call.tenant_id,TranscriptSegment.text==text,TranscriptSegment.started_at==event.get('start')))
                                    if existing: continue
                                db.add(TranscriptSegment(tenant_id=call.tenant_id,transcript_id=tr.id,speaker=event.get('speaker') or 'CUSTOMER',text=text,started_at=event.get('start'),ended_at=event.get('end')); await db.commit()
                elif kind in {'response.audio_transcript.done','response.output_audio_transcript.done','response.output_text.done'}:
                    text=event.get('transcript') or event.get('text')
                    if text:
                        async with SessionLocal() as db:
                            tr=await db.scalar(select(Transcript).where(Transcript.call_id==call_id,Transcript.tenant_id==call.tenant_id))
                            if tr: db.add(TranscriptSegment(tenant_id=call.tenant_id,transcript_id=tr.id,speaker='ASSISTANT',text=text)); await db.commit()
                elif kind=='input_audio_buffer.speech_started': await bridge.cancel()
                elif kind=='error': logger.error('realtime_error',extra={'call_id':str(call_id),'error':event.get('error')})
        while True:
            message=json.loads(await websocket.receive_text()); kind=message.get('event')
            if kind=='start': stream_sid=message['start']['streamSid']; task=asyncio.create_task(ai_loop()); await bridge.create_response()
            elif kind=='media': await bridge.send_audio(message['media']['payload'])
            elif kind=='stop': break
    except WebSocketDisconnect: pass
    except Exception: logger.exception('voice_stream_failed',extra={'call_id':str(call_id)})
    finally:
        if task: task.cancel()
        if bridge: await bridge.close()
        intelligence=False
        try:
            async with SessionLocal() as db:
                call=await db.scalar(select(Call).where(Call.id==call_id))
                if call and get_settings().intelligence_enabled: await ensure_job(db,call.tenant_id,call.id); intelligence=True
                await db.commit()
            if intelligence:
                from app.workers.tasks import process_call_intelligence
                process_call_intelligence.apply_async(args=[str(call_id)],countdown=5)
        except Exception: logger.exception('voice_stream_cleanup_failed',extra={'call_id':str(call_id)})

@router.post('/plivo/inbound')
async def plivo_inbound(request:Request,db:AsyncSession=Depends(get_db)):
    from app.providers.plivo import stream_xml, validate_webhook
    form=dict(await request.form()); validate_webhook(request,form); to=form.get('To')
    pn=await db.scalar(select(PhoneNumber).where(PhoneNumber.e164==to,PhoneNumber.active==True,PhoneNumber.provider=='plivo'))
    if not pn: raise HTTPException(404,'Plivo phone number not configured')
    if not (pn.capabilities or {}).get('inbound',True): raise HTTPException(403,'Inbound calling is disabled for this phone number')
    agent,version=await load_agent_version(db,pn); contact=await db.scalar(select(Contact).where(Contact.tenant_id==pn.tenant_id,Contact.phone==form.get('From'),Contact.status.notin_(['ARCHIVED'])))
    call=Call(tenant_id=pn.tenant_id,agent_id=agent.id,agent_version_id=version.id,phone_number_id=pn.id,contact_id=contact.id if contact else None,provider_call_id=form.get('CallUUID'),direction='INBOUND',from_number=form.get('From'),to_number=to,status='IN_PROGRESS'); db.add(call); await db.commit()
    return Response(content=stream_xml(call.id),media_type='application/xml')

@router.post('/plivo/outbound/{call_id}')
async def plivo_outbound(call_id:uuid.UUID,request:Request,db:AsyncSession=Depends(get_db)):
    from app.providers.plivo import stream_xml, validate_webhook
    form=dict(await request.form()); validate_webhook(request,form)
    call=await db.scalar(select(Call).where(Call.id==call_id,Call.provider_call_id==form.get('CallUUID')))
    if not call: raise HTTPException(404,'Call not found')
    if call.direction!='OUTBOUND': raise HTTPException(409,'Call direction mismatch')
    call.status='IN_PROGRESS'; await db.commit(); return Response(content=stream_xml(call.id),media_type='application/xml')

@router.post('/plivo/status')
async def plivo_status(request:Request,db:AsyncSession=Depends(get_db)):
    from app.providers.plivo import validate_webhook
    form=dict(await request.form()); validate_webhook(request,form)
    call=await db.scalar(select(Call).where(Call.provider_call_id==form.get('CallUUID')))
    if not call: return {'ok':True}
    raw=form.get('CallStatus') or form.get('HangupCause') or ''; new_status=STATUS_MAP.get(str(raw).lower(),call.status); was_terminal=call.status in TERMINAL_CALL_STATES; call.status=new_status
    duration=form.get('Duration') or form.get('BillDuration')
    if duration:
        try: call.duration_seconds=int(duration)
        except ValueError: pass
    if new_status in TERMINAL_CALL_STATES:
        call.ended_at=datetime.now(timezone.utc)
        if not was_terminal: await record_voice_minutes(db,call.tenant_id,call.duration_seconds)
    from app.services.handoff import sync_handoff_state
    await sync_handoff_state(db,call,raw); await db.commit(); return {'ok':True}
