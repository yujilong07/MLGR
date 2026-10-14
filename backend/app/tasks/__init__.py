import os

from celery import Celery

from app.config import settings

celery = Celery(
    "mlgr",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.docx_task"]
)

# Without a separate worker (single Render web service) tasks run in-process;
# results are still stored in Redis, so /generate/status works unchanged
if os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() in ("1", "true", "yes"):
    celery.conf.task_always_eager = True
    celery.conf.task_store_eager_result = True
