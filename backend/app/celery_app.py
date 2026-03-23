from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "failure_log_analyzer",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.task_track_started = True
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.autodiscover_tasks(["app.tasks"])

# register signal handlers
import app.celery_signals  # noqa: E402,F401
