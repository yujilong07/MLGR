from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from app.database import get_session
from app.models.report import Report
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.ai_service import stream_conclusion
from app.services.cache_service import get_cached, set_cached
import hashlib
import json

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