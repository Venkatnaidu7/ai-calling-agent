from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import tenant_id
from app.db.session import get_db
from app.models import Call, CallActionItem, CallSummary, Transcript, TranscriptSegment
from app.services.call_intelligence import ensure_job

router = APIRouter(prefix='/calls', tags=['call-intelligence'])

@router.get('/{call_id}/intelligence')
async def get_intelligence(call_id: UUID, t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    tid=UUID(t)
    call=await db.scalar(select(Call).where(Call.id==call_id,Call.tenant_id==tid))
    if not call: raise HTTPException(404,'Call not found')
    transcript=await db.scalar(select(Transcript).where(Transcript.call_id==call_id,Transcript.tenant_id==tid))
    summary=await db.scalar(select(CallSummary).where(CallSummary.call_id==call_id,CallSummary.tenant_id==tid))
    segments=[]
    if transcript:
        rows=(await db.scalars(select(TranscriptSegment).where(TranscriptSegment.transcript_id==transcript.id,TranscriptSegment.tenant_id==tid).order_by(TranscriptSegment.started_at.asc().nulls_last(),TranscriptSegment.created_at.asc()))).all()
        segments=[{'speaker':x.speaker,'text':x.text,'started_at':x.started_at,'ended_at':x.ended_at,'confidence':x.confidence} for x in rows]
    actions=(await db.scalars(select(CallActionItem).where(CallActionItem.call_id==call_id,CallActionItem.tenant_id==tid).order_by(CallActionItem.created_at.asc()))).all()
    return {'call_id':str(call_id),'transcript':{'status':transcript.status if transcript else 'NOT_STARTED','segments':segments},'summary':summary,'action_items':actions}

@router.post('/{call_id}/intelligence/process')
async def process_intelligence(call_id: UUID,t=Depends(tenant_id),db: AsyncSession=Depends(get_db)):
    tid=UUID(t); call=await db.scalar(select(Call).where(Call.id==call_id,Call.tenant_id==tid))
    if not call: raise HTTPException(404,'Call not found')
    job=await ensure_job(db,tid,call_id); await db.commit()
    from app.workers.tasks import process_call_intelligence
    process_call_intelligence.apply_async(args=[str(call_id)])
    return {'call_id':str(call_id),'status':job.status}

@router.get('/intelligence/search')
async def search_intelligence(q: str=Query(min_length=2,max_length=200),limit:int=Query(50,ge=1,le=200),t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    tid=UUID(t); pattern=f'%{q}%'
    stmt=(select(Call,CallSummary).join(CallSummary,CallSummary.call_id==Call.id,isouter=True).where(Call.tenant_id==tid,or_(CallSummary.summary.ilike(pattern),CallSummary.intent.ilike(pattern),CallSummary.outcome.ilike(pattern),CallSummary.next_action.ilike(pattern))).order_by(Call.created_at.desc()).limit(limit))
    rows=(await db.execute(stmt)).all()
    return [{'call_id':str(call.id),'status':call.status,'direction':call.direction,'created_at':call.created_at,'summary':summary} for call,summary in rows]
