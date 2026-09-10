import asyncio
from sqlalchemy import select
from app.workers.celery_app import celery
from app.services.campaign_runner import run_campaign_sync
from app.services.call_intelligence import IntelligenceError, analyze_call, ensure_job
from app.db.session import SessionLocal
from app.models import Call, CallIntelligenceJob

@celery.task(bind=True, max_retries=5)
def health_task(self): return {'status':'ok'}

@celery.task(bind=True, max_retries=5)
def process_call_summary(self, call_id: str): return process_call_intelligence.delay(call_id).get(disable_sync_subtasks=False)

@celery.task(bind=True, max_retries=4, acks_late=True)
def process_call_intelligence(self, call_id: str):
    async def run():
        async with SessionLocal() as db:
            call=await db.scalar(select(Call).where(Call.id==call_id))
            if not call: raise IntelligenceError('CALL_NOT_FOUND')
            job=await ensure_job(db,call.tenant_id,call.id)
            job.status='PROCESSING'; job.attempts += 1; await db.commit()
            try:
                await analyze_call(db,call.tenant_id,call.id)
                return {'status':'completed','call_id':call_id}
            except IntelligenceError as exc:
                job.status='RETRY' if self.request.retries < self.max_retries else 'FAILED'; job.last_error=str(exc); await db.commit(); raise
    try: return asyncio.run(run())
    except IntelligenceError as exc: raise self.retry(exc=exc,countdown=min(300,30*(2**self.request.retries)))

@celery.task(bind=True, max_retries=3)
def process_campaign(self,campaign_id:str,tenant_id:str):
    try:
        result=run_campaign_sync(campaign_id,tenant_id); state=result.get('status')
        if state=='scheduled': self.apply_async(args=[campaign_id,tenant_id],countdown=max(1,int(result.get('delay_seconds',60))))
        elif state=='ok' and int(result.get('launched',0))>0: self.apply_async(args=[campaign_id,tenant_id],countdown=15)
        return result
    except Exception as exc: raise self.retry(exc=exc,countdown=30)
