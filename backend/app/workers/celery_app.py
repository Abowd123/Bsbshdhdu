from celery import Celery

from app.core.config import settings

celery_app = Celery("wolfhost", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "monitor-bots-health": {
        "task": "app.workers.tasks.monitor_bots_health",
        "schedule": 30.0,
    },
    "collect-bots-stats": {
        "task": "app.workers.tasks.collect_bots_stats",
        "schedule": 10.0,
    },
}
