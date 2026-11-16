from celery import Celery

from core.config import settings

celery_app = Celery(
    "evvent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={
        # Flip published events whose end time has passed to "completed" so
        # they drop out of listings and recommendations automatically.
        "complete-past-events": {
            "task": "tasks.complete_past_events",
            "schedule": 15 * 60,  # every 15 minutes
        },
    },
)
