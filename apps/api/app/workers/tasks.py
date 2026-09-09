from app.workers.celery_app import celery
@celery.task(bind=True,max_retries=5)
def health_task(self): return {'status':'ok'}
@celery.task(bind=True,max_retries=5)
def process_call_summary(self,call_id:str): return {'call_id':call_id,'status':'queued'}
