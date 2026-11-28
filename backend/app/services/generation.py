"""Building the .docx / .pdf of a report.

* One build per report at a time: a second click while it is queued or running gets the same job.
* A build takes several CPU seconds and 0.1–0.3 GB of RAM, so at most GENERATION_CONCURRENCY of
  them run at once in one web process; the rest wait in a queue and the editor shows the place
  in it. With a separate Celery worker (CELERY_TASK_ALWAYS_EAGER off) the worker's --concurrency
  is that limit instead.
* Job state lives in Redis and the files in the database, so any instance can answer
  /generate/status and /download: the web service can run as several instances behind a
  load balancer.
"""
import glob
import json
import os
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Lock

import structlog
from sqlalchemy import delete
from sqlmodel import Session, select

from app.database import engine
from app.models.report import GeneratedFile, Report, ReportImage
from app.services import cache_service
from app.services.docx_builder import apply_toc_pages, build_report_docx
from app.services.image_store import ensure_all_local
from app.services.pdf_builder import build_report_pdf

logger = structlog.get_logger().bind(service="generation")

CONCURRENCY = max(1, int(os.getenv("GENERATION_CONCURRENCY", "2")))
MAX_QUEUE = int(os.getenv("GENERATION_MAX_QUEUE", "40"))
FILES_TTL = timedelta(hours=float(os.getenv("GENERATED_TTL_HOURS", "24")))
JOB_TTL = 3600        # seconds the job state is kept in Redis
STALE_RUNNING = 300   # no build takes 5 minutes: the instance that ran it is gone
STALE_QUEUED = 900

QUEUED, RUNNING, DONE, ERROR = "queued", "running", "done", "error"
FORMATS = ("docx", "pdf")
_QUEUE = "gen:queue"  # sorted set: job id -> time it was queued

LOST_MESSAGE = "Сервер перезапустився під час генерації — спробуйте ще раз"
FAILED_MESSAGE = "Не вдалося скласти документ"


class QueueFull(Exception):
    pass


def _redis():
    return cache_service.r  # looked up on every call: tests swap the client


def _job_key(job_id: str) -> str:
    return f"gen:job:{job_id}"


def _active_key(report_id: int) -> str:
    return f"gen:report:{report_id}"


def _save_job(job_id: str, **state):
    _redis().set(_job_key(job_id), json.dumps(state), ex=JOB_TTL)


def get_job(job_id: str) -> dict | None:
    raw = _redis().get(_job_key(job_id))
    if not raw:
        return None
    job = json.loads(raw)
    age = time.time() - job.get("ts", 0)
    if (job["state"] == RUNNING and age > STALE_RUNNING) or (job["state"] == QUEUED and age > STALE_QUEUED):
        job = {**job, "state": ERROR, "error": LOST_MESSAGE}
    return job


def progress(job_id: str) -> tuple[dict | None, int]:
    """The job and how many builds are queued ahead of it (on all instances)."""
    job = get_job(job_id)
    ahead = 0
    if job and job["state"] == QUEUED:
        ahead = _redis().zrank(_QUEUE, job_id) or 0
    return job, ahead


def submit(report_id: int, user_id: int) -> str:
    r = _redis()
    job_id = uuid.uuid4().hex
    if not r.set(_active_key(report_id), job_id, nx=True, ex=JOB_TTL):
        current = r.get(_active_key(report_id))
        job = get_job(current) if current else None
        if job and job["state"] in (QUEUED, RUNNING):
            return current  # double click, a second tab: that build is already on its way
        r.set(_active_key(report_id), job_id, ex=JOB_TTL)

    r.zremrangebyscore(_QUEUE, 0, time.time() - STALE_QUEUED)  # lost when an instance died
    if r.zcard(_QUEUE) >= MAX_QUEUE:
        r.delete(_active_key(report_id))
        raise QueueFull()

    _save_job(job_id, report_id=report_id, user_id=user_id, state=QUEUED, ts=time.time())
    r.zadd(_QUEUE, {job_id: time.time()})
    try:
        _dispatch(job_id, report_id)
    except Exception:
        _finish(job_id, report_id, user_id, ERROR, FAILED_MESSAGE)
        raise
    logger.info("generation_queued", report_id=report_id, job_id=job_id)
    return job_id


_executor: ThreadPoolExecutor | None = None
_executor_lock = Lock()


def _dispatch(job_id: str, report_id: int):
    from app.tasks import celery

    if celery.conf.task_always_eager:
        # No worker (one Render service): build in this process, CONCURRENCY at a time
        global _executor
        with _executor_lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(max_workers=CONCURRENCY, thread_name_prefix="docbuild")
        _executor.submit(run_job, job_id, report_id)
    else:
        from app.tasks.docx_task import generate_docx_task
        generate_docx_task.apply_async(args=[report_id, job_id], task_id=job_id)


def _finish(job_id: str, report_id: int, user_id, state: str, error: str | None = None):
    r = _redis()
    r.zrem(_QUEUE, job_id)
    _save_job(job_id, report_id=report_id, user_id=user_id, state=state, ts=time.time(), error=error)
    # The next click starts a new build, with the edits made since
    if r.get(_active_key(report_id)) == job_id:
        r.delete(_active_key(report_id))


def run_job(job_id: str, report_id: int) -> bool:
    user_id = (get_job(job_id) or {}).get("user_id")
    r = _redis()
    r.zrem(_QUEUE, job_id)
    _save_job(job_id, report_id=report_id, user_id=user_id, state=RUNNING, ts=time.time())
    t0 = time.perf_counter()
    try:
        found = build_documents(report_id, version=job_id)
    except Exception:
        logger.error("generation_failed", report_id=report_id, job_id=job_id, exc_info=True)
        _finish(job_id, report_id, user_id, ERROR, FAILED_MESSAGE)
        return False
    if not found:
        _finish(job_id, report_id, user_id, ERROR, "Звіт не знайдено")
        return False
    _finish(job_id, report_id, user_id, DONE)
    logger.info("generation_done", report_id=report_id, job_id=job_id,
                elapsed_ms=round((time.perf_counter() - t0) * 1000))
    return True


# ── the build itself ─────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _read(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def build_documents(report_id: int, version: str | None = None) -> bool:
    """Builds the .docx and the .pdf (whose layout also gives the real TOC page numbers for the
    .docx) and stores both. False when the report does not exist."""
    version = version or uuid.uuid4().hex
    # expire_on_commit=False: the objects stay readable after the session closes. It closes
    # before the build so no database connection is held for the seconds the build takes.
    with Session(engine, expire_on_commit=False) as session:
        report = session.get(Report, report_id)
        if not report:
            return False
        # Files may be gone from disk after a restart: restore them from the database first
        images = ensure_all_local(session, session.exec(
            select(ReportImage).where(ReportImage.report_id == report_id)).all())

    # A directory of its own, so two builds never write into the same file
    with tempfile.TemporaryDirectory(prefix="mlgr-build-") as tmp:
        docx_path = build_report_docx(report, images=images, out_dir=tmp)
        pdf = None
        try:
            pdf_path, pages = build_report_pdf(report, images=images, out_dir=tmp)
            apply_toc_pages(docx_path, pages)
            pdf = _read(pdf_path)
        except Exception:
            # The .docx is still useful without the PDF; an outdated PDF must not stay behind
            logger.warning("pdf_render_failed", report_id=report_id, exc_info=True)
        files = {"docx": _read(docx_path), "pdf": pdf}

    store_files(report_id, files, version)
    return True


def store_files(report_id: int, files: dict, version: str):
    now = _utcnow()
    with Session(engine) as session:
        session.execute(delete(GeneratedFile).where(GeneratedFile.report_id == report_id))
        for fmt, data in files.items():
            if data is not None:
                session.add(GeneratedFile(report_id=report_id, format=fmt, version=version,
                                          size=len(data), data=data, created_at=now))
        # Files nobody needs any more: the editor rebuilds before every download anyway
        session.execute(delete(GeneratedFile).where(GeneratedFile.created_at < now - FILES_TTL))
        session.commit()
    for fmt, data in files.items():
        if data is not None:
            _cache_put(report_id, fmt, version, data)


def delete_files(session: Session, report_id: int):
    """Before the report itself is deleted (the caller commits)."""
    session.execute(delete(GeneratedFile).where(GeneratedFile.report_id == report_id))


# ── local disk copy: saves pulling the bytes from the database on every download ──

def _cache_dir() -> str:
    return os.getenv("GENERATED_DIR", "/app/generated")


def _cache_path(report_id: int, fmt: str, version: str) -> str:
    return os.path.join(_cache_dir(), f"report_{report_id}.{version}.{fmt}")


def _cache_put(report_id: int, fmt: str, version: str, data: bytes) -> str | None:
    path = _cache_path(report_id, fmt, version)
    try:
        os.makedirs(_cache_dir(), exist_ok=True)
        for old in glob.glob(os.path.join(_cache_dir(), f"report_{report_id}.*.{fmt}")):
            if old != path:
                os.remove(old)
        tmp = f"{path}.{uuid.uuid4().hex}.part"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        return path
    except OSError:
        logger.warning("generated_cache_write_failed", report_id=report_id, exc_info=True)
        return None


def load_file(session: Session, report_id: int, fmt: str) -> tuple[str | None, bytes | None]:
    """(path of a local copy, None) or (None, bytes); (None, None) when nothing is built."""
    where = (GeneratedFile.report_id == report_id, GeneratedFile.format == fmt)
    version = session.exec(select(GeneratedFile.version).where(*where)).first()
    if version is None:
        return None, None
    path = _cache_path(report_id, fmt, version)
    if os.path.exists(path):
        return path, None
    data = session.exec(select(GeneratedFile.data).where(*where)).first()
    if data is None:
        return None, None
    path = _cache_put(report_id, fmt, version, data)
    return (path, None) if path else (None, data)
