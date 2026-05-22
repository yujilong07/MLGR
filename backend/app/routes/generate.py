import asyncio
import os
import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models.report import Report
from app.models.user import User
from app.services.auth_service import get_current_user, authenticate_token
from app.services.ai_service import stream_conclusion, generate_introduction, improve_section_text
from app.services.cache_service import get_cached, set_cached
from app.tasks.docx_task import generate_docx_task
from app.tasks import celery
from app.limiter import limiter, get_user_email


class SectionTextRequest(BaseModel):
    text: str


generate_router = APIRouter()


@generate_router.get('/reports/{id}/stream-conclusion')
@limiter.limit("10/minute", key_func=get_user_email)
async def stream_conclusion_endpoint(
    request: Request,
    id: int,
    token: str = Query(...),
    session: Session = Depends(get_session),
):
    current_user = authenticate_token(token, session)
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    content = report.goal + json.dumps(report.sections or {})
    cache_key = "conclusion:" + hashlib.md5(content.encode()).hexdigest()
    goal = report.goal
    sections = report.sections or {}

    async def event_stream():
        cached = get_cached(cache_key)
        if cached:
            yield f'data: {json.dumps({"token": cached})}\n\n'
            yield f'data: {json.dumps({"done": True})}\n\n'
            return

        full_text = ""
        loop = asyncio.get_event_loop()
        chunks = await loop.run_in_executor(None, lambda: list(stream_conclusion(goal, sections)))
        for chunk in chunks:
            full_text += chunk
            yield f'data: {json.dumps({"token": chunk})}\n\n'

        yield f'data: {json.dumps({"done": True})}\n\n'
        set_cached(cache_key, full_text, ttl=86400)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@generate_router.post('/reports/{id}/generate-introduction')
@limiter.limit("10/minute", key_func=get_user_email)
async def generate_introduction_endpoint(
    request: Request,
    id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    cache_key = "introduction:" + hashlib.md5(report.goal.encode()).hexdigest()
    cached = get_cached(cache_key)
    if cached:
        return {"introduction": cached}

    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, lambda: generate_introduction(report.goal))
    set_cached(cache_key, text, ttl=86400)
    return {"introduction": text}


@generate_router.post('/reports/{id}/improve-section')
@limiter.limit("10/minute", key_func=get_user_email)
async def improve_section_endpoint(
    request: Request,
    id: int,
    body: SectionTextRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    loop = asyncio.get_event_loop()
    improved = await loop.run_in_executor(None, lambda: improve_section_text(body.text))
    return {"improved_text": improved}


@generate_router.post('/reports/{id}/generate')
async def generate(
    id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    task = generate_docx_task.delay(id)
    return {"task_id": task.id}


@generate_router.get('/reports/{id}/generate/status')
async def generate_status(
    id: int,
    task_id: str,
    token: str = Query(...),
    session: Session = Depends(get_session),
):
    authenticate_token(token, session)

    async def event_stream():
        while True:
            result = celery.AsyncResult(task_id)
            if result.successful():
                yield f'data: {json.dumps({"status": "done", "progress": 100, "message": "Документ готовий!"})}\n\n'
                return
            elif result.failed():
                yield f'data: {json.dumps({"status": "error", "progress": 0, "message": "Помилка генерації"})}\n\n'
                return
            else:
                yield f'data: {json.dumps({"status": "pending", "progress": 50, "message": "Генерується..."})}\n\n'
            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@generate_router.get('/reports/{id}/download')
async def download_report(
    id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    path = os.path.join(os.getenv("GENERATED_DIR", "/app/generated"), f'report_{id}.docx')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Not found")

    return FileResponse(
        path,
        filename=f"report_{id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
