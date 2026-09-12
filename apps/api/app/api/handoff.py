from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import tenant_id
from app.db.session import get_db
from app.models import HumanAgent, RoutingGroup, TransferDestination, Call
from app.services.handoff import select_destination

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

@router.post('/resolve')
async def resolve(call_id: UUID, routing_group_id: UUID | None=None, t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    call=await db.scalar(select(Call).where(Call.id == call_id, Call.tenant_id == UUID(t)))
    if not call: raise HTTPException(404,'Call not found')
    destination=await select_destination(db, UUID(t), routing_group_id)
    if not destination: raise HTTPException(409,'No human agent is available')
    return {'call_id': str(call.id), 'destination_id': str(destination.id), 'phone': destination.phone, 'name': destination.name}
