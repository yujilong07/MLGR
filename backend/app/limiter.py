from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from jose import jwt, JWTError
from app.config import settings

limiter = Limiter(key_func=get_remote_address)


def get_user_email(request: Request) -> str:
    try:
        # Authorization header (regular requests)
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        # query param fallback for EventSource / SSE (can't set headers)
        if not token:
            token = request.query_params.get("token", "")
        if not token:
            return get_remote_address(request)
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        email = payload.get("email")
        return email or get_remote_address(request)
    except (JWTError, Exception):
        return get_remote_address(request)
