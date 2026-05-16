import redis
from app.config import settings

r = redis.from_url(settings.redis_url, decode_responses=True)

def get_cached(key: str):
    return r.get(key)

def set_cached(key: str, value: str, ttl: int):
    r.set(key, value, ex=ttl)

def delete_cached(key: str):
    r.delete(key)

