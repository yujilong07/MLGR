from fastapi import FastAPI
from app.routes.auth import auth_router
from app.routes.reports import reports_router
from app.routes.generate import generate_router

app = FastAPI(title="Lab Report Generator")

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(reports_router,prefix="/reports", tags=["report"])
app.include_router(generate_router, tags=["generate"])

@app.get("/health")
async def health():
    return {"status": "ok"}