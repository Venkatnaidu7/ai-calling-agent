from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse, Dial
from plivo import plivoxml
from app.api.deps import tenant_id
from app.db.session import get_db
from app.core.config import get_settings
from app.models import HumanAgent, RoutingGroup, TransferDestination, Call, CallHandoff
from app.providers.twilio import validate_twilio
from app.providers.plivo import validate_webhook
from app.services.handoff import select_destination, is_business_hours, start_transfer, sync_handoff_state

router = APIRouter(prefix='/handoff', tags=['human-handoff'])

class HumanAgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=7, max_length=32, pattern=r'^\+[1-9]\d{6,30}$')
    status: str = Field(default='OFFLINE', max_length=20)
    priority: int = Field(default=0, ge=0, le=1000)
    department: str | None = Field(default=None, max_length=100)

class RoutingGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    strategy: str = Field(default='ROUND_ROBIN', max_length=30)

class DestinationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=7, max_length=32, pattern=r'^\+[1-9]\d{6,30}$')
    routing_group_id: UUID | None = None

class TransferRequest(BaseModel):
    routing_group_id: UUID | None = None
    destination_id: UUID | None = None
    reason: str | None = Field(default=None, max_length=1000)
    require_business_hours: bool = True

@router.get('/agents')
async def list_agents(t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    return (await db.scalars(select(HumanAgent).where(HumanAgent.tenant_id == UUID(t)).order_by(HumanAgent.priority.desc(), HumanAgent.created_at.asc()))).all()

@router.post('/agents')
async def create_agent(data: HumanAgentCreate, t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    x=HumanAgent(tenant_id=UUID(t), **data.model_dump()); db.add(x); await db.commit(); await db.refresh(x); return x

@router.get('/groups')
async def list_groups(t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    return (await db.scalars(select(RoutingGroup).where(RoutingGroup.tenant_id == UUID(t)).order_by(RoutingGroup.created_at.asc()))).all()

@router.post('/groups')
async def create_group(data: RoutingGroupCreate, t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    strategy=data.strategy.upper()
    if strategy not in {'ROUND_ROBIN','PRIORITY'}: raise HTTPException(422,'strategy must be ROUND_ROBIN or PRIORITY')
    x=RoutingGroup(tenant_id=UUID(t), name=data.name, strategy=strategy); db.add(x); await db.commit(); await db.refresh(x); return x

@router.get('/destinations')
async def list_destinations(t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    return (await db.scalars(select(TransferDestination).where(TransferDestination.tenant_id == UUID(t)).order_by(TransferDestination.created_at.asc()))).all()

@router.post('/destinations')
async def create_destination(data: DestinationCreate, t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    if data.routing_group_id and not await db.scalar(select(RoutingGroup.id).where(RoutingGroup.id == data.routing_group_id, RoutingGroup.tenant_id == UUID(t))): raise HTTPException(404,'Routing group not found')
    x=TransferDestination(tenant_id=UUID(t), **data.model_dump()); db.add(x); await db.commit(); await db.refresh(x); return x

@router.get('/resolve')
async def resolve(call_id: UUID, routing_group_id: UUID | None=None, t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    call=await db.scalar(select(Call).where(Call.id == call_id, Call.tenant_id == UUID(t)))
    if not call: raise HTTPException(404,'Call not found')
    destination=await select_destination(db, UUID(t), routing_group_id)
    if not destination: raise HTTPException(409,'No human agent is available')
    return {'call_id': str(call.id), 'destination_id': str(destination.id), 'phone': destination.phone, 'name': destination.name}

@router.get('/{call_id}')
async def get_handoff(call_id: UUID, t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    x=await db.scalar(select(CallHandoff).where(CallHandoff.call_id==call_id, CallHandoff.tenant_id==UUID(t)))
    if not x: raise HTTPException(404,'Handoff not found')
    return x

@router.post('/{call_id}/transfer')
async def transfer(call_id: UUID, data: TransferRequest, t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    tid=UUID(t); call=await db.scalar(select(Call).where(Call.id==call_id, Call.tenant_id==tid))
    if not call: raise HTTPException(404,'Call not found')
    if call.status not in {'QUEUED','RINGING','IN_PROGRESS'}: raise HTTPException(409,'Call is not active')
    if not call.provider_call_id: raise HTTPException(409,'Provider call is not connected')
    if data.require_business_hours and not await is_business_hours(db, tid): raise HTTPException(409,'Human handoff is outside configured business hours')
    destination = None
    if data.destination_id:
        destination=await db.scalar(select(TransferDestination).where(TransferDestination.id==data.destination_id,TransferDestination.tenant_id==tid))
        if not destination: raise HTTPException(404,'Transfer destination not found')
    else: destination=await select_destination(db,tid,data.routing_group_id)
    if not destination: raise HTTPException(409,'No human agent is available')
    handoff=await start_transfer(db,tid,call,destination,data.reason); await db.commit()
    return {'call_id':str(call.id),'status':handoff.status,'provider':handoff.provider,'destination_phone':handoff.destination_phone}

@router.post('/twilio/execute/{call_id}')
async def twilio_execute(call_id: UUID, request: Request, db: AsyncSession=Depends(get_db)):
    form=dict(await request.form()); validate_twilio(request,form)
    call=await db.scalar(select(Call).where(Call.id==call_id,Call.provider_call_id==form.get('CallSid')))
    handoff=await db.scalar(select(CallHandoff).where(CallHandoff.call_id==call_id, CallHandoff.status=='TRANSFERRING'))
    if not call or not handoff: raise HTTPException(404,'Handoff not found')
    base=get_settings().public_base_url.rstrip('/')
    action=f'{base}/api/v1/handoff/twilio/action/{call.id}'
    status=f'{base}/api/v1/handoff/twilio/leg-status/{call.id}'
    response=VoiceResponse(); dial=Dial(timeout=20,answer_on_bridge=True,action=action,method='POST')
    dial.number(handoff.destination_phone,status_callback=status,status_callback_event='initiated ringing answered completed',status_callback_method='POST')
    response.append(dial)
    return Response(content=str(response),media_type='application/xml')

@router.post('/twilio/leg-status/{call_id}')
async def twilio_leg_status(call_id: UUID, request: Request, db: AsyncSession=Depends(get_db)):
    form=dict(await request.form()); validate_twilio(request,form)
    call=await db.scalar(select(Call).where(Call.id==call_id,Call.tenant_id==select(Call.tenant_id).scalar_subquery()))
    if not call or call.provider_call_id != form.get('ParentCallSid'): raise HTTPException(404,'Call not found')
    handoff=await db.scalar(select(CallHandoff).where(CallHandoff.call_id==call_id,CallHandoff.tenant_id==call.tenant_id))
    if handoff:
        await sync_handoff_state(db,call,form.get('CallStatus'))
        await db.commit()
    return {'ok':True}

@router.post('/twilio/action/{call_id}')
async def twilio_action(call_id: UUID, request: Request, db: AsyncSession=Depends(get_db)):
    form=dict(await request.form()); validate_twilio(request,form)
    call=await db.scalar(select(Call).where(Call.id==call_id))
    handoff=await db.scalar(select(CallHandoff).where(CallHandoff.call_id==call_id,CallHandoff.status.in_(['TRANSFERRING','CONNECTED'])))
    if not call or not handoff: raise HTTPException(404,'Handoff not found')
    status=(form.get('DialCallStatus') or '').lower()
    if status in {'completed','answered'}: handoff.status='CONNECTED'
    else: handoff.status='FAILED'; handoff.failure_reason=status or 'transfer_failed'
    await db.commit()
    response=VoiceResponse()
    if handoff.status=='FAILED':
        # Resume the AI stream instead of terminating the caller when the human leg fails.
        from app.api.voice import stream_response
        return stream_response(call.id)
    response.hangup()
    return Response(content=str(response),media_type='application/xml')

@router.post('/plivo/execute/{call_id}')
async def plivo_execute(call_id: UUID, request: Request, db: AsyncSession=Depends(get_db)):
    form=dict(await request.form()); validate_webhook(request,form)
    call_uuid=form.get('CallUUID')
    call=await db.scalar(select(Call).where(Call.id==call_id,Call.provider_call_id==call_uuid))
    handoff=await db.scalar(select(CallHandoff).where(CallHandoff.call_id==call_id, CallHandoff.status=='TRANSFERRING'))
    if not call or not handoff: raise HTTPException(404,'Handoff not found')
    base=get_settings().public_base_url.rstrip('/')
    action=f'{base}/api/v1/handoff/plivo/action/{call.id}'
    callback=f'{base}/api/v1/handoff/plivo/leg-status/{call.id}'
    response=plivoxml.ResponseElement(); dial=plivoxml.DialElement(timeout=20,action=action,method='POST',callback_url=callback,callback_method='POST')
    dial.add(plivoxml.NumberElement(handoff.destination_phone)); response.add(dial)
    return Response(content=response.to_string(),media_type='application/xml')

@router.post('/plivo/leg-status/{call_id}')
async def plivo_leg_status(call_id: UUID, request: Request, db: AsyncSession=Depends(get_db)):
    form=dict(await request.form()); validate_webhook(request,form)
    call_uuid=form.get('DialALegUUID') or form.get('CallUUID')
    call=await db.scalar(select(Call).where(Call.id==call_id))
    if not call or (call.provider_call_id and call.provider_call_id != call_uuid): raise HTTPException(404,'Call not found')
    handoff=await db.scalar(select(CallHandoff).where(CallHandoff.call_id==call_id,CallHandoff.tenant_id==call.tenant_id))
    if handoff:
        action=(form.get('DialAction') or '').lower(); status=form.get('DialBLegStatus') or form.get('CallStatus') or action
        await sync_handoff_state(db,call,'ANSWERED' if action in {'answer','connected'} else status); await db.commit()
    return {'ok':True}

@router.post('/plivo/action/{call_id}')
async def plivo_action(call_id: UUID, request: Request, db: AsyncSession=Depends(get_db)):
    form=dict(await request.form()); validate_webhook(request,form)
    call=await db.scalar(select(Call).where(Call.id==call_id))
    handoff=await db.scalar(select(CallHandoff).where(CallHandoff.call_id==call_id,CallHandoff.status.in_(['TRANSFERRING','CONNECTED'])))
    if not call or not handoff: raise HTTPException(404,'Handoff not found')
    status=(form.get('DialStatus') or '').lower()
    if status in {'completed','answered'}: handoff.status='CONNECTED'
    else: handoff.status='FAILED'; handoff.failure_reason=status or 'transfer_failed'
    await db.commit()
    if handoff.status=='FAILED':
        from app.providers.plivo import stream_xml
        return Response(content=stream_xml(call.id),media_type='application/xml')
    return Response(content='<Response></Response>',media_type='application/xml')
