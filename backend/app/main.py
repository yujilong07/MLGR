from app.logging_config import setup_logging

setup_logging()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.routes.auth import auth_router
from app.routes.reports import reports_router
from app.routes.generate import generate_router
from app.routes.upload import upload_router
from app.limiter import limiter
import structlog

logger = structlog.get_logger().bind(service="app")

app = FastAPI(title="Lab Report Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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

import os
UPLOADS_DIR   = os.getenv("UPLOADS_DIR",   "/app/uploads")
GENERATED_DIR = os.getenv("GENERATED_DIR", "/app/generated")
os.makedirs(UPLOADS_DIR,   exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok"}
