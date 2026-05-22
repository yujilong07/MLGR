import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session

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


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",  # in-memory
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# Reports fixture

@pytest.fixture(name="auth_token")
def auth_token_fixture(client):
    client.post("/auth/register", 
    json= {"username": "testuser",
            "email": "test@example.com",
            "password": "password123"})
    
    response = client.post("/auth/login", data={
    "username": "test@example.com",
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

