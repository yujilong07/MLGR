from app.logging_config import setup_logging

setup_logging()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.routes.auth import auth_router
from app.routes.reports import reports_router
from app.routes.generate import generate_router
from app.limiter import limiter
import structlog

logger = structlog.get_logger().bind(service="app")

app = FastAPI(title="Lab Report Generator")
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


@app.get("/health")
async def health():
    return {"status": "ok"}
