import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session
from app.limiter import limiter

from app.models.user import User
from app.models.report import Report, ReportImage


@pytest.fixture(autouse=True)
def mock_cache():
    store = {}
    mock_r = MagicMock()
    mock_r.get.side_effect = lambda key: store.get(key)
    mock_r.set.side_effect = lambda key, value, ex=None: store.update({key: value})
    mock_r.delete.side_effect = lambda key: store.pop(key, None)
    with patch("app.services.cache_service.r", mock_r):
        yield mock_r


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://",  # in-memory
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


class FakeRedis:
    """The few Redis commands the app uses (strings and a sorted set), in memory."""

    def __init__(self):
        self.kv, self.zsets = {}, {}

    def get(self, key):
        return self.kv.get(key)

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.kv:
            return None
        self.kv[key] = value
        return True

    def delete(self, *keys):
        for key in keys:
            self.kv.pop(key, None)
            self.zsets.pop(key, None)

    def zadd(self, name, mapping):
        self.zsets.setdefault(name, {}).update(mapping)

    def zrem(self, name, *members):
        for member in members:
            self.zsets.get(name, {}).pop(member, None)

    def zrank(self, name, member):
        ranked = sorted(self.zsets.get(name, {}).items(), key=lambda item: (item[1], item[0]))
        return next((i for i, (m, _) in enumerate(ranked) if m == member), None)

    def zcard(self, name):
        return len(self.zsets.get(name, {}))

    def zremrangebyscore(self, name, low, high):
        zset = self.zsets.get(name, {})
        for member in [m for m, score in zset.items() if low <= score <= high]:
            del zset[member]

    def ping(self):
        return True


@pytest.fixture(name="fake_redis")
def fake_redis_fixture():
    fake = FakeRedis()
    with patch("app.services.cache_service.r", fake):
        yield fake


@pytest.fixture(name="client")
def client_fixture(session):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    limiter.enabled = False
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    limiter.enabled = True


# Reports fixture

@pytest.fixture(name="auth_token")
def auth_token_fixture(client):
    client.post("/auth/register", 
    json= {"username": "testuser",
            "email": "test@example.com",
            "password": "password123"})
    
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "password123"})

    return response.json()["access_token"]

@pytest.fixture(name="auth_headers")
def auth_headers_fixture(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


_REPORT_PAYLOAD = {
    "title": "Work",
    "discipline": "Web-tech",
    "teacher": "Andrew Ng",
    "group": "ITAI-24-2",
    "goal": "learn something",
}


@pytest.fixture(name="report_id")
def report_id_fixture(client, auth_headers):
    response = client.post("/reports", headers=auth_headers, json=_REPORT_PAYLOAD)
    return response.json()["id"]



def make_png(width=40, height=30, color=(200, 30, 30)):
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def uploads_tmp(tmp_path, monkeypatch):
    path = tmp_path / "uploads"
    monkeypatch.setenv("UPLOADS_DIR", str(path))
    return path
