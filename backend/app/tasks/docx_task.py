from app.tasks import celery
from app.services import generation


@celery.task
def generate_docx_task(report_id: int, job_id: str | None = None):
    """Runs on the Celery worker. With CELERY_TASK_ALWAYS_EAGER (no worker) the web process
    builds in its own limited pool instead (services/generation.py)."""
    if job_id:
        return generation.run_job(job_id, report_id)
    return generation.build_documents(report_id)
