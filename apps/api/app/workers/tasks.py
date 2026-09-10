from app.workers.celery_app import celery
from app.services.campaign_runner import run_campaign_sync


@celery.task(bind=True, max_retries=5)
def health_task(self):
    return {'status': 'ok'}


@celery.task(bind=True, max_retries=5)
def process_call_summary(self, call_id: str):
    return {'call_id': call_id, 'status': 'queued'}


@celery.task(bind=True, max_retries=3)
def process_campaign(self, campaign_id: str, tenant_id: str):
    try:
        return run_campaign_sync(campaign_id, tenant_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
