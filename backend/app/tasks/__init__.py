from celery import Celery

celery = Celery(
    "mlgr",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
    include=["app.tasks.docx_task"]
)