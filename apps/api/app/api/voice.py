import asyncio,hashlib,hmac,json,uuid
from fastapi import APIRouter,Request,WebSocket,HTTPException,WebSocketDisconnect,Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import SessionLocal
from app.models import PhoneNumber,Agent,AgentVersion,Call
from app.providers.twilio import validate_twilio,validate_twilio_ws,connect_stream_xml
from app.providers.openai_realtime import RealtimeBridge
from app.core.config import get_settings
router=APIRouter(tags=['voice'])
def stream_token(call_id):return hmac.new(get_settings().secret_key.encode(),str(call_id).encode(),hashlib.sha256).hexdigest()
def valid_stream_token(call_id,token):return hmac.compare_digest(stream_token(call_id),token or '')
@router.post('/twilio/inbound')
async def inbound(request:Request,db:AsyncSession=Depends(__import__('app.db.session',fromlist=['get_db']).get_db)):
    form=dict(await request.form());validate_twilio(request,form);to=form.get('To');pn=await db.scalar(select(PhoneNumber).where(PhoneNumber.e164==to,PhoneNumber.active==True))
    if not pn:raise HTTPException(404,'Phone number not configured')
    agent=await db.scalar(select(Agent).where(Agent.id==pn.agent_id,Agent.tenant_id==pn.tenant_id,Agent.active==True))
    if not agent or not agent.active_version_id:raise HTTPException(503,'Agent unavailable')
    v=await db.scalar(select(AgentVersion).where(AgentVersion.id==agent.active_version_id,AgentVersion.tenant_id==pn.tenant_id,AgentVersion.status=='PUBLISHED'))
    if not v:raise HTTPException(503,'Published agent unavailable')
    call=Call(tenant_id=pn.tenant_id,agent_id=agent.id,agent_version_id=v.id,phone_number_id=pn.id,provider_call_id=form.get('CallSid'),direction='INBOUND',from_number=form.get('From'),to_number=to,status='ANSWERED');db.add(call);await db.flush();await db.commit()
    base=get_settings().public_base_url;ws=base.replace('https://','wss://').replace('http://','ws://')+f'/api/v1/voice/stream/{call.id}?token={stream_token(call.id)}'
    return connect_stream_xml(ws,{'call_id':call.id})
@router.post('/twilio/status')
async def status(request:Request,db:AsyncSession=Depends(__import__('app.db.session',fromlist=['get_db']).get_db)):
    form=dict(await request.form());validate_twilio(request,form);call=await db.scalar(select(Call).where(Call.provider_call_id==form.get('CallSid')))
    if call:call.status=form.get('CallStatus','').upper();await db.commit()
    return {'ok':True}
@router.websocket('/voice/stream/{call_id}')
async def stream(websocket:WebSocket,call_id:uuid.UUID,token:str|None=None):
    if not valid_stream_token(call_id,token):await websocket.close(code=1008);return
    try:validate_twilio_ws(websocket)
    except HTTPException:await websocket.close(code=1008);return
    await websocket.accept();bridge=None;stream_sid=None;task=None
    try:
        async with SessionLocal() as db:
            call=await db.scalar(select(Call).where(Call.id==call_id));
            if not call:await websocket.close(code=1008);return
            v=await db.scalar(select(AgentVersion).where(AgentVersion.id==call.agent_version_id,AgentVersion.tenant_id==call.tenant_id))
        bridge=RealtimeBridge(v.system_instructions,v.voice,v.language);await bridge.connect()
        async def ai_loop():
            async for e in bridge.events():
                if e.get('type') in {'response.output_audio.delta','response.audio.delta'} and stream_sid and e.get('delta'):
                    await websocket.send_text(json.dumps({'event':'media','streamSid':stream_sid,'media':{'payload':e['delta']}}))
                elif e.get('type')=='input_audio_buffer.speech_started':await bridge.cancel()
        while True:
            m=json.loads(await websocket.receive_text());et=m.get('event')
            if et=='start':stream_sid=m['start']['streamSid'];task=asyncio.create_task(ai_loop())
            elif et=='media':await bridge.send_audio(m['media']['payload'])
            elif et=='stop':break
    except (WebSocketDisconnect,Exception):pass
    finally:
        if task:task.cancel()
        if bridge:await bridge.close()
