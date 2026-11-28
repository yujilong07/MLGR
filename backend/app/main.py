from app.logging_config import setup_logging

setup_logging()

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from openai import APIConnectionError, APIStatusError, RateLimitError
from sqlalchemy import text
from sqlmodel import Session, select
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.routes.auth import auth_router
from app.routes.reports import reports_router
from app.routes.generate import generate_router
from app.routes.upload import upload_router
from app.routes.latex import latex_router
from app.limiter import limiter
from app.database import get_session
from app.models.report import ReportImage
from app.services.image_store import ensure_local, local_path
from app.services import cache_service
import structlog

logger = structlog.get_logger().bind(service="app")

app = FastAPI(title="Lab Report Generator")


class StripApiPrefix:
    """In production the frontend calls the API as /api/... on the same origin
    (Render, Caddy); the routes themselves live at the root."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            path = scope["path"]
            if path == "/api" or path.startswith("/api/"):
                new_path = path[len("/api"):] or "/"
                scope = dict(scope, path=new_path, raw_path=new_path.encode())
        await self.app(scope, receive, send)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(StripApiPrefix)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RateLimitError)
async def ai_rate_limited_handler(request: Request, exc: RateLimitError):
    logger.warning("ai_rate_limited", path=str(request.url.path))
    return JSONResponse(status_code=503, headers={"Retry-After": "60"},
                        content={"detail": "Сервіс AI зараз перевантажений — спробуйте за хвилину"})


@app.exception_handler(APIConnectionError)
@app.exception_handler(APIStatusError)
async def ai_unavailable_handler(request: Request, exc: Exception):
    logger.error("ai_unavailable", path=str(request.url.path), error=type(exc).__name__)
    return JSONResponse(status_code=502, content={"detail": "Сервіс AI не відповів — спробуйте ще раз"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        method=request.method,
        path=str(request.url.path),
        exc_info=True,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(reports_router, prefix="/reports", tags=["report"])
app.include_router(generate_router, tags=["generate"])
app.include_router(upload_router, tags=["upload"])
app.include_router(latex_router, tags=["latex"])

import os
UPLOADS_DIR   = os.getenv("UPLOADS_DIR",   "/tmp/uploads")
GENERATED_DIR = os.getenv("GENERATED_DIR", "/tmp/generated")
os.makedirs(UPLOADS_DIR,   exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)


@app.get("/uploads/{filename}")
def serve_upload(filename: str, session: Session = Depends(get_session)):
    """Image files: from the disk cache, or restored from the database after a restart.
    Names are random UUIDs, so (as before with the static mount) no auth is needed."""
    image = session.exec(select(ReportImage).where(ReportImage.filename == filename)).first()
    if not image or not ensure_local(session, image):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(local_path(image), headers={"Cache-Control": "private, max-age=31536000, immutable"})


@app.get("/health")
async def health():
    """Liveness. Touches neither the database nor Redis: an uptime pinger that keeps a free
    Render service awake must not keep Neon awake too (its free compute hours are limited)."""
    return {"status": "ok"}


@app.get("/health/ready")
def ready(session: Session = Depends(get_session)):
    """Readiness for a load balancer / Kubernetes: the database and Redis answer."""
    try:
        session.execute(text("SELECT 1"))
        cache_service.r.ping()
    except Exception:
        logger.warning("not_ready", exc_info=True)
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok"}


# Serve the frontend from the same service when it is shipped alongside (root Dockerfile).
# Mounted last so API routes take precedence.
FRONTEND_DIR = os.getenv("FRONTEND_DIR", str(Path(__file__).resolve().parents[2] / "frontend"))
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
