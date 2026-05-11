from fastapi import FastAPI
from app.routes.auth import auth_router

app = FastAPI(title="Lab Report Generator")

app.include_router(auth_router, prefix="/auth", tags=["auth"])

@app.get("/health")
async def health():
    return {"status": "ok"}