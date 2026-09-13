from celery import Celery
from app.core.config import get_settings

s = get_settings()
celery = Celery('ai_voice', broker=s.redis_url, backend=s.redis_url)
celery.conf.update(
    task_default_queue='voice',
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_track_started=True,
)
