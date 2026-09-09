from celery import Celery
from app.core.config import get_settings
s=get_settings()
celery=Celery('ai_voice',broker=s.redis_url,backend=s.redis_url)
celery.conf.task_default_queue='voice'
