import os

from sqlmodel import create_engine, Session
from app.config import settings

DATABASE_URL = settings.database_url


def _engine_options(url: str) -> dict:
    options = {"pool_pre_ping": True}
    if url.startswith("postgres"):
        # Every process (uvicorn worker, Celery worker, instance) has its own pool of
        # pool_size + max_overflow connections. With several of them point DATABASE_URL at
        # Neon's pooled host (…-pooler.…neon.tech), or Postgres runs out of connections.
        options.update(
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            # Neon drops idle connections when its compute goes to sleep
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "300")),
            connect_args={"connect_timeout": 10, "keepalives": 1, "keepalives_idle": 30,
                          "keepalives_interval": 10, "keepalives_count": 3},
        )
    return options


engine = create_engine(DATABASE_URL, **_engine_options(DATABASE_URL))


def get_session():
    with Session(engine) as session:
        yield session
