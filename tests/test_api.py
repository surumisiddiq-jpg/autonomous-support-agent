from fastapi.testclient import TestClient

from api.main import app
from config.settings import settings

client = TestClient(app)
HEADERS = {"X-API-Token": settings.API_TOKEN}


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_missing_token_is_rejected():
    response = client.post(
        "/api/v1/agent/chat",
        json={
            "thread_id": "test-auth",
            "user_message": "hello",
        },
    )

    assert response.status_code == 401


def test_invalid_token_is_rejected():
    response = client.post(
        "/api/v1/agent/chat",
        headers={"X-API-Token": "invalid-token"},
        json={
            "thread_id": "test-auth",
            "user_message": "hello",
        },
    )

    assert response.status_code == 401


def test_chat_endpoint_requires_valid_payload():
    response = client.post(
        "/api/v1/agent/chat",
        headers=HEADERS,
        json={"thread_id": "test-validation"},
    )

    assert response.status_code == 422


def test_approve_requires_existing_pending_transaction(monkeypatch):
    from service import agent_service

    class EmptyState:
        next = ()

    class FakeGraph:
        def get_state(self, config):
            return EmptyState()

    monkeypatch.setattr(
        agent_service,
        "compiled_agent",
        FakeGraph(),
    )

    response = client.post(
        "/api/v1/admin/override",
        headers=HEADERS,
        json={
            "thread_id": "missing-thread",
            "action": "APPROVE",
        },
    )

    assert response.status_code == 400
