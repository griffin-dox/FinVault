import os
from celery import Celery

# Celery configuration from environment
BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URI", "redis://localhost:6379/0"))
BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URI", "redis://localhost:6379/0"))

celery = Celery(
    "finvault",
    broker=BROKER_URL,
    backend=BACKEND_URL,
    include=[
        "app.services.tasks",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Periodic tasks (requires running celery beat)
celery.conf.beat_schedule = {
    "aggregate-geo-tiles-daily": {
        "task": "aggregate_geo_tiles_daily",
        "schedule": 24 * 60 * 60,  # every 24 hours
    },
}
