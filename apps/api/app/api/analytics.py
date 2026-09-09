from uuid import UUID
from fastapi import APIRouter,Depends
from sqlalchemy import select,func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import tenant_id
from app.models import Call,UsageRecord
router=APIRouter(prefix='/analytics',tags=['analytics'])
@router.get('/summary')
async def summary(days:int=7,t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    q=select(func.count(Call.id)).where(Call.tenant_id==UUID(t));total=await db.scalar(q) or 0
    answered=await db.scalar(select(func.count(Call.id)).where(Call.tenant_id==UUID(t),Call.status.in_(['ANSWERED','IN_PROGRESS','COMPLETED']))) or 0
    completed=await db.scalar(select(func.count(Call.id)).where(Call.tenant_id==UUID(t),Call.status=='COMPLETED')) or 0
    avg=await db.scalar(select(func.avg(Call.duration_seconds)).where(Call.tenant_id==UUID(t))) or 0
    return {'total_calls':total,'answered':answered,'completed':completed,'average_duration_seconds':float(avg),'transfer_rate':0}
@router.get('/usage')
async def usage(t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):return (await db.scalars(select(UsageRecord).where(UsageRecord.tenant_id==UUID(t)).order_by(UsageRecord.created_at.desc()).limit(100))).all()
