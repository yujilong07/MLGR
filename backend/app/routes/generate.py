from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.responses import FileResponse

from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session

from app.models.report import Report
from app.models.user import User

from app.services.auth_service import get_current_user
from app.services.ai_service import stream_conclusion, generate_introduction, improve_section_text

from app.services.cache_service import get_cached, set_cached

from app.tasks.docx_task import generate_docx_task
from app.tasks import celery

import os
import hashlib
import json



class SectionTextRequest(BaseModel):
    text: str

generate_router = APIRouter()

@generate_router.get('/reports/{id}/stream-conclusion')
async def stream_conclusion_endpoint(id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    import asyncio
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
            yield f"data: {cached}\n\n"
            return

        full_text = ""
        loop = asyncio.get_event_loop()
        tokens = await loop.run_in_executor(None, lambda: list(stream_conclusion(goal, sections)))
        for token in tokens:
            full_text += token
            yield f"data: {token}\n\n"

        set_cached(cache_key, full_text, ttl=86400)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@generate_router.post('/reports/{id}/generate-introduction')
async def generate_introduction_endpoint(id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    cache_key = "introduction:" + hashlib.md5(report.goal.encode()).hexdigest()
    cached = get_cached(cache_key)
    if cached:
        return {"introduction": cached}

    import asyncio
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, lambda: generate_introduction(report.goal))
    set_cached(cache_key, text, ttl=86400)
    return {"introduction": text}


@generate_router.post('/reports/{id}/improve-section')
async def improve_section_endpoint(id: int, body: SectionTextRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    import asyncio
    loop = asyncio.get_event_loop()
    improved = await loop.run_in_executor(None, lambda: improve_section_text(body.text))
    return {"improved_text": improved}

@generate_router.post('/reports/{id}/generate')
async def generate(id: int,current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")
    
    task = generate_docx_task.delay(id)
    return {"task_id": task.id}

@generate_router.get('/reports/{id}/generate/status')
async def generate_status(id: int, task_id: str, current_user: User = Depends(get_current_user)):
    result = celery.AsyncResult(task_id)
    return {
        "status": result.status,
        "result": result.result if result.successful() else None
    }

@generate_router.get('/reports/{id}/download')
async def downoload_report(id: int,current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")
    
    path = os.path.join('/app/generated', f'report_{id}.docx')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Not found")
    
    return FileResponse(
    path,
    filename=f"report_{id}.docx",
    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
