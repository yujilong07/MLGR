import asyncio
import hashlib
import json
import time
import structlog
from types import SimpleNamespace
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response, StreamingResponse
from openai import RateLimitError
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models.report import Report, ReportImage
from app.models.user import User
from app.services.auth_service import get_current_user, authenticate_token
from app.services.ai_service import (
    stream_conclusion, generate_introduction, improve_section_text,
    build_report_context, CONCLUSION_PROMPT_VERSION, _MODEL,
    needs_chunking, split_report_parts, summarize_part, condensed_report_context,
)
from app.services.cache_service import get_cached, set_cached
from app.services import generation
from app.limiter import limiter, get_user_email


class SectionTextRequest(BaseModel):
    text: str


generate_router = APIRouter()
logger = structlog.get_logger().bind(service="generate")

# Routes are plain `def`: FastAPI runs them in its thread pool, so the (synchronous) database
# and AI calls never stop the event loop that serves everyone else. Streams poll in threads too.
# Streaming routes close their session as soon as the route returns (scope="function"),
# not when the stream ends: otherwise every open stream would hold a database connection.


@generate_router.get('/reports/{id}/stream-conclusion')
@limiter.limit("10/minute", key_func=get_user_email)
def stream_conclusion_endpoint(
    request: Request,
    id: int,
    token: str = Query(...),
    session: Session = Depends(get_session, scope="function"),
):
    current_user = authenticate_token(token, session)
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    images = session.exec(select(ReportImage).where(ReportImage.report_id == id)).all()
    snapshot = SimpleNamespace(
        kind=report.kind, level=report.level, title=report.title, discipline=report.discipline, goal=report.goal,
        introduction=report.introduction, sections=report.sections,
        images=[img for img in images if img.section_path != "u"],
    )
    full_context = build_report_context(snapshot, limit=None)
    # Any change to the report, the prompt or the model gives a new conclusion
    cache_key = "conclusion:" + hashlib.md5(
        f"{CONCLUSION_PROMPT_VERSION}|{_MODEL}|{full_context}".encode()
    ).hexdigest()

    def save_conclusion(text: str):
        # Persist so the downloaded .docx contains the generated conclusion
        fresh = session.get(Report, id)
        if fresh:
            fresh.conclusion = text
            fresh.updated_at = datetime.now(timezone.utc)
            session.add(fresh)
            session.commit()

    def event(**payload):
        return f'data: {json.dumps(payload, ensure_ascii=False)}\n\n'

    async def event_stream():
        cached = await run_in_threadpool(get_cached, cache_key)
        if cached:
            await run_in_threadpool(save_conclusion, cached)
            yield event(token=cached)
            yield event(done=True)
            return

        loop = asyncio.get_running_loop()
        full_text = ""
        try:
            if needs_chunking(snapshot):
                # Big report: condense each part first, then write the conclusion from the parts
                parts = split_report_parts(snapshot)
                summaries = []
                for n, part in enumerate(parts, start=1):
                    yield event(status=f"Аналізуємо частину {n} з {len(parts)}…")
                    summaries.append(await loop.run_in_executor(
                        None, summarize_part, snapshot, part, n, len(parts)))
                yield event(status="Пишемо висновки…")
                report_context = condensed_report_context(snapshot, summaries)
            else:
                report_context = build_report_context(snapshot)

            tokens = stream_conclusion(report_context)
            # Pull tokens one by one in a thread so they reach the browser as they arrive
            while (chunk := await loop.run_in_executor(None, next, tokens, None)) is not None:
                full_text += chunk
                yield event(token=chunk)
        except RateLimitError:
            logger.warning("conclusion_rate_limited", report_id=id)
            yield event(error="Сервіс AI зараз перевантажений — спробуйте ще раз за хвилину.")
            return
        except Exception:
            logger.error("conclusion_failed", report_id=id, exc_info=True)
            yield event(error="Модель не відповіла. Спробуйте ще раз за хвилину.")
            return

        if not full_text.strip():
            yield event(error="Модель повернула порожню відповідь. Спробуйте ще раз.")
            return

        await run_in_threadpool(save_conclusion, full_text)
        yield event(done=True)
        await run_in_threadpool(set_cached, cache_key, full_text, 86400)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@generate_router.post('/reports/{id}/generate-introduction')
@limiter.limit("10/minute", key_func=get_user_email)
def generate_introduction_endpoint(
    request: Request,
    id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    essay_context = None
    if report.kind in ("essay", "course"):
        # The intro of an essay / a course work is written from the topic and what the sections cover
        essay_context = build_report_context(SimpleNamespace(
            kind=report.kind, level=report.level, title=report.title, discipline=report.discipline, goal="",
            introduction=None, sections=report.sections, images=[],
        ), limit=6000)
    source = essay_context or report.goal or ""
    cache_key = "introduction:" + hashlib.md5(f"{report.kind}|{source}".encode()).hexdigest()
    cached = get_cached(cache_key)
    if cached:
        return {"introduction": cached}

    text = generate_introduction(report.goal, essay_context)
    set_cached(cache_key, text, ttl=86400)
    return {"introduction": text}


@generate_router.post('/reports/{id}/improve-section')
@limiter.limit("10/minute", key_func=get_user_email)
def improve_section_endpoint(
    request: Request,
    id: int,
    body: SectionTextRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    return {"improved_text": improve_section_text(body.text)}


@generate_router.post('/reports/{id}/generate')
@limiter.limit("20/minute", key_func=get_user_email)
def generate(
    request: Request,
    id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        # Queued, returns at once; the editor follows /generate/status
        job_id = generation.submit(id, current_user.id)
    except generation.QueueFull:
        logger.warning("generation_queue_full", report_id=id)
        raise HTTPException(status_code=503, detail="Сервер зараз дуже завантажений — спробуйте за хвилину",
                            headers={"Retry-After": "60"})
    return {"task_id": job_id}


_STATUS_MAX_WAIT = 20 * 60


def _documents(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "документ"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "документи"
    return "документів"


def _status_message(job: dict, ahead: int) -> str:
    if job["state"] == generation.QUEUED:
        return f"У черзі: перед вами {ahead} {_documents(ahead)}…" if ahead else "У черзі — зараз почнемо…"
    return "Складаємо документ…"


@generate_router.get('/reports/{id}/generate/status')
def generate_status(
    id: int,
    task_id: str,
    token: str = Query(...),
    session: Session = Depends(get_session, scope="function"),
):
    current_user = authenticate_token(token, session)
    job = generation.get_job(task_id)
    if not job or job.get("user_id") != current_user.id or job.get("report_id") != id:
        raise HTTPException(status_code=404, detail="Not found")

    def event(**payload):
        return f'data: {json.dumps(payload, ensure_ascii=False)}\n\n'

    async def event_stream():
        deadline = time.monotonic() + _STATUS_MAX_WAIT
        while True:
            job, ahead = await run_in_threadpool(generation.progress, task_id)
            if job is None or time.monotonic() > deadline:
                yield event(status="error", progress=0, message=generation.LOST_MESSAGE)
                return
            if job["state"] == generation.DONE:
                yield event(status="done", progress=100, message="Документ готовий!")
                return
            if job["state"] == generation.ERROR:
                yield event(status="error", progress=0, message=job.get("error") or "Помилка генерації")
                return
            yield event(status="pending", progress=50, message=_status_message(job, ahead), queue=ahead)
            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


_DOWNLOAD_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


@generate_router.get('/reports/{id}/download')
def download_report(
    id: int,
    format: str = Query("docx", pattern="^(docx|pdf)$"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    path, data = generation.load_file(session, id, format)
    filename = f"report_{id}.{format}"
    if path:
        return FileResponse(path, filename=filename, media_type=_DOWNLOAD_TYPES[format])
    if data is not None:
        return Response(data, media_type=_DOWNLOAD_TYPES[format],
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    detail = "PDF is not available on this server" if format == "pdf" else "Not found"
    raise HTTPException(status_code=404, detail=detail)
