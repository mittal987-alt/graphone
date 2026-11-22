from celery import Celery

from src.config.settings import get_settings

settings = get_settings()
celery_app = Celery(
    "graphone",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=1800,
    task_time_limit=2100,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["src.workers"])
