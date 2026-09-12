from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse, Dial
from plivo import RestClient as PlivoClient
from plivo import plivoxml
from app.api.deps import tenant_id
from app.db.session import get_db
from app.core.config import get_settings
from app.models import HumanAgent, RoutingGroup, TransferDestination, Call, CallHandoff, PhoneNumber
from app.providers.twilio import validate_twilio
from app.providers.plivo import validate_webhook
from app.services.handoff import select_destination, is_business_hours, create_or_get_handoff

router = APIRouter(prefix='/handoff', tags=['human-handoff'])

class HumanAgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=7, max_length=32)
    status: str = Field(default='OFFLINE', max_length=20)
    priority: int = Field(default=0, ge=0, le=1000)
    department: str | None = Field(default=None, max_length=100)

class RoutingGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    strategy: str = Field(default='ROUND_ROBIN', max_length=30)

class DestinationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=7, max_length=32)
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
    x=RoutingGroup(tenant_id=UUID(t), **data.model_dump()); db.add(x); await db.commit(); await db.refresh(x); return x

@router.get('/destinations')
async def list_destinations(t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    return (await db.scalars(select(TransferDestination).where(TransferDestination.tenant_id == UUID(t)).order_by(TransferDestination.created_at.asc()))).all()

@router.post('/destinations')
async def create_destination(data: DestinationCreate, t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    if data.routing_group_id and not await db.scalar(select(RoutingGroup.id).where(RoutingGroup.id == data.routing_group_id, RoutingGroup.tenant_id == UUID(t))): raise HTTPException(404,'Routing group not found')
    x=TransferDestination(tenant_id=UUID(t), **data.model_dump()); db.add(x); await db.commit(); await db.refresh(x); return x

@router.get('/{call_id}')
async def get_handoff(call_id: UUID, t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    x=await db.scalar(select(CallHandoff).where(CallHandoff.call_id==call_id, CallHandoff.tenant_id==UUID(t)))
    if not x: raise HTTPException(404,'Handoff not found')
    return x

@router.post('/{call_id}/transfer')
async def transfer(call_id: UUID, data: TransferRequest, t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    tid=UUID(t)
    call=await db.scalar(select(Call).where(Call.id==call_id, Call.tenant_id==tid))
    if not call: raise HTTPException(404,'Call not found')
    if call.status not in {'QUEUED','RINGING','IN_PROGRESS'}: raise HTTPException(409,'Call is not active')
    if not call.provider_call_id: raise HTTPException(409,'Provider call is not connected')
    if data.require_business_hours and not await is_business_hours(db, tid): raise HTTPException(409,'Human handoff is outside configured business hours')
    destination=None
    if data.destination_id:
        destination=await db.scalar(select(TransferDestination).where(TransferDestination.id==data.destination_id,TransferDestination.tenant_id==tid))
        if not destination: raise HTTPException(404,'Transfer destination not found')
    else:
        destination=await select_destination(db,tid,data.routing_group_id)
    if not destination: raise HTTPException(409,'No human agent is available')
    provider=(await db.scalar(select(PhoneNumber.provider).where(PhoneNumber.id==call.phone_number_id,PhoneNumber.tenant_id==tid))) or 'twilio'
    if provider not in {'twilio','plivo'}: raise HTTPException(400,'Unsupported voice provider')
    handoff=await create_or_get_handoff(db,tid,call,destination,data.reason)
    if handoff.status in {'CONNECTED','TRANSFERRING'}: return {'call_id':str(call.id),'status':handoff.status,'destination_phone':handoff.destination_phone}
    base=get_settings().public_base_url.rstrip('/')
    if not base.startswith('https://'): raise HTTPException(503,'public_base_url must use HTTPS for voice transfer')
    try:
        if provider=='twilio':
            s=get_settings()
            if not s.twilio_account_sid or not s.twilio_auth_token: raise HTTPException(503,'Twilio is not configured')
            url=f'{base}/api/v1/handoff/twilio/execute/{call.id}'
            TwilioClient(s.twilio_account_sid,s.twilio_auth_token).calls(call.provider_call_id).update(url=url,method='POST')
        else:
            s=get_settings()
            if not s.plivo_auth_id or not s.plivo_auth_token: raise HTTPException(503,'Plivo is not configured')
            url=f'{base}/api/v1/handoff/plivo/execute/{call.id}'
            PlivoClient(s.plivo_auth_id,s.plivo_auth_token).calls.update(call.provider_call_id,legs='aleg',aleg_url=url,aleg_method='POST')
    except HTTPException:
        raise
    except Exception as exc:
        handoff.status='FAILED'; handoff.failure_reason=str(exc)[:1000]; await db.commit()
        raise HTTPException(502,f'Unable to start {provider} human transfer')
    handoff.status='TRANSFERRING'; call.outcome='HUMAN_HANDOFF'; await db.commit()
    return {'call_id':str(call.id),'status':handoff.status,'provider':provider,'destination_phone':destination.phone}

@router.post('/twilio/execute/{call_id}')
async def twilio_execute(call_id: UUID, request: Request, db: AsyncSession=Depends(get_db)):
    form=dict(await request.form()); validate_twilio(request,form)
    call=await db.scalar(select(Call).where(Call.id==call_id,Call.provider_call_id==form.get('CallSid')))
    handoff=await db.scalar(select(CallHandoff).where(CallHandoff.call_id==call_id))
    if not call or not handoff: raise HTTPException(404,'Handoff not found')
    response=VoiceResponse(); dial=Dial(timeout=20,answer_on_bridge=True); dial.number(handoff.destination_phone); response.append(dial)
    handoff.status='CONNECTED'; await db.commit()
    return Response(content=str(response),media_type='application/xml')

@router.post('/plivo/execute/{call_id}')
async def plivo_execute(call_id: UUID, request: Request, db: AsyncSession=Depends(get_db)):
    form=dict(await request.form()); validate_webhook(request,form)
    call_uuid=form.get('CallUUID')
    call=await db.scalar(select(Call).where(Call.id==call_id,Call.provider_call_id==call_uuid))
    handoff=await db.scalar(select(CallHandoff).where(CallHandoff.call_id==call_id))
    if not call or not handoff: raise HTTPException(404,'Handoff not found')
    response=plivoxml.ResponseElement(); dial=plivoxml.DialElement(); dial.add(plivoxml.NumberElement(handoff.destination_phone)); response.add(dial)
    handoff.status='CONNECTED'; await db.commit()
    return Response(content=response.to_string(),media_type='application/xml')

@router.post('/resolve')
async def resolve(call_id: UUID, routing_group_id: UUID | None=None, t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    call=await db.scalar(select(Call).where(Call.id == call_id, Call.tenant_id == UUID(t)))
    if not call: raise HTTPException(404,'Call not found')
    destination=await select_destination(db, UUID(t), routing_group_id)
    if not destination: raise HTTPException(409,'No human agent is available')
    return {'call_id': str(call.id), 'destination_id': str(destination.id), 'phone': destination.phone, 'name': destination.name}
