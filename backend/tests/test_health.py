"""Smoke tests for the M0 backend skeleton."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert isinstance(body["llm_enabled"], bool)


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["health"] == "/health"


def test_cors_preflight():
    resp = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
