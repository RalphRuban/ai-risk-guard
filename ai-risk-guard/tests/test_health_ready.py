"""
tests/test_health_ready.py
Tests for the unauthenticated readiness probe (Section A6): GET /api/health/ready
returns 200 when the DB is writable, 503 otherwise, and never requires login.
"""

import pytest

import app.app as app_module
from app.app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def test_health_ready_is_public_and_ok(client):
    resp = client.get("/api/health/ready")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ready"
    assert data["db_writable"] is True
    assert "sandbox_available" in data
    assert "github_configured" in data


def test_health_ready_returns_503_when_db_down(client, monkeypatch):
    monkeypatch.setattr(app_module, "db_health", lambda: False)
    resp = client.get("/api/health/ready")
    assert resp.status_code == 503
    assert resp.get_json()["status"] == "not_ready"


def test_health_ready_requires_no_login(client):
    # No session, no CSRF: the probe must be reachable by platform health checks.
    with client.session_transaction() as sess:
        sess.clear()
    resp = client.get("/api/health/ready")
    assert resp.status_code == 200
