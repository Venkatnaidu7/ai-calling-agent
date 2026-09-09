from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select,func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import tenant_id,current_claims
from app.models import Agent,AgentVersion
from app.schemas.agent import *
router=APIRouter(prefix='/agents',tags=['agents'])
@router.post('',response_model=AgentOut)
async def create_agent(data:AgentCreate,tid:str=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    a=Agent(tenant_id=UUID(tid),name=data.name,description=data.description); db.add(a); await db.flush(); db.add(AgentVersion(tenant_id=UUID(tid),agent_id=a.id,version=1)); await db.commit(); await db.refresh(a)
    return AgentOut(id=str(a.id),tenant_id=str(a.tenant_id),name=a.name,description=a.description,active_version_id=None,active=a.active)
@router.get('',response_model=list[AgentOut])
async def list_agents(tid:str=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    rows=(await db.scalars(select(Agent).where(Agent.tenant_id==UUID(tid)).order_by(Agent.created_at.desc()))).all()
    return [AgentOut(id=str(a.id),tenant_id=str(a.tenant_id),name=a.name,description=a.description,active_version_id=str(a.active_version_id) if a.active_version_id else None,active=a.active) for a in rows]
@router.post('/{agent_id}/versions',response_model=AgentVersionOut)
async def create_version(agent_id:UUID,data:AgentVersionCreate,tid:str=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    a=await db.scalar(select(Agent).where(Agent.id==agent_id,Agent.tenant_id==UUID(tid)))
    if not a: raise HTTPException(404,'Agent not found')
    n=(await db.scalar(select(func.max(AgentVersion.version)).where(AgentVersion.agent_id==a.id))) or 0
    v=AgentVersion(tenant_id=UUID(tid),agent_id=a.id,version=n+1,**data.model_dump()); db.add(v); await db.commit(); await db.refresh(v); return v
@router.get('/{agent_id}/versions',response_model=list[AgentVersionOut])
async def versions(agent_id:UUID,tid:str=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    a=await db.scalar(select(Agent).where(Agent.id==agent_id,Agent.tenant_id==UUID(tid)))
    if not a: raise HTTPException(404,'Agent not found')
    return (await db.scalars(select(AgentVersion).where(AgentVersion.agent_id==agent_id,AgentVersion.tenant_id==UUID(tid)).order_by(AgentVersion.version.desc()))).all()
@router.post('/{agent_id}/versions/{version_id}/publish',response_model=AgentVersionOut)
async def publish(agent_id:UUID,version_id:UUID,tid:str=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    a=await db.scalar(select(Agent).where(Agent.id==agent_id,Agent.tenant_id==UUID(tid))); v=await db.scalar(select(AgentVersion).where(AgentVersion.id==version_id,AgentVersion.agent_id==agent_id,AgentVersion.tenant_id==UUID(tid)))
    if not a or not v: raise HTTPException(404,'Agent/version not found')
    await db.execute(AgentVersion.__table__.update().where(AgentVersion.agent_id==a.id).values(status='ARCHIVED')); v.status='PUBLISHED'; a.active_version_id=v.id; await db.commit(); await db.refresh(v); return v
