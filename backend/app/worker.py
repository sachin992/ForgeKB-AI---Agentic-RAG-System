from celery import Celery

from app.core.config import settings

celery_app = Celery("smart_rag", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"
celery_app.conf.task_routes = {
    "app.tasks.ingest_datasource_task": {"queue": "ingestion"},
}

celery_app.autodiscover_tasks(["app"])
