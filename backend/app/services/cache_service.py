import structlog
import redis
from app.config import settings

r = redis.from_url(settings.redis_url, decode_responses=True)

logger = structlog.get_logger().bind(service="cache")


def get_cached(key: str):
    value = r.get(key)
    # skip blacklist keys — they're checked on every request and would spam logs
    if not key.startswith("blacklist:"):
        category = key.split(":")[0]
        if value is not None:
            logger.info("cache_hit", key_category=category)
        else:
            logger.info("cache_miss", key_category=category)
    return value


def set_cached(key: str, value: str, ttl: int):
    r.set(key, value, ex=ttl)


def delete_cached(key: str):
    r.delete(key)
