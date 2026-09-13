"""
tests/test_health_gemini.py
Tests for GET /api/health/gemini (System Health LLM ENGINE row).

Covers the offline (no key), online (model resolved), degraded (rate-limited /
resolution failure) paths. All Gemini API traffic is neutralized by
conftest.mock_gemini_api; the endpoint resolves the model via GeminiClient.
"""

import pytest

from app.app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def _auth(client, github_id="111", login="alice"):
    with client.session_transaction() as sess:
        sess["user"] = {"github_id": github_id, "login": login}


def test_gemini_health_requires_login(client):
    resp = client.get("/api/health/gemini")
    # Redirect to gh auth gateway when unauthenticated.
    assert resp.status_code in (302, 401)


def test_gemini_health_offline_when_key_missing(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    _auth(client)
    resp = client.get("/api/health/gemini")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "offline"
    assert data["configured"] is False
    assert data["model"] is None


def test_gemini_health_online_when_model_resolves(client, monkeypatch):
    # conftest patches resolve_gemini_model -> "gemini-3.5-flash".
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    _auth(client)
    resp = client.get("/api/health/gemini")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "online"
    assert data["configured"] is True
    assert data["model"] == "gemini-3.5-flash"
    assert data["error"] is None


def test_gemini_health_degraded_when_rate_limited(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    from unittest.mock import patch
    with patch("core.llm.gemini_client.is_rate_limited", return_value=True):
        _auth(client)
        resp = client.get("/api/health/gemini")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "degraded"
    assert data["configured"] is True
    assert "rate-limited" in (data["error"] or "")


def test_gemini_health_degraded_when_resolution_fails(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    from unittest.mock import patch
    with patch(
        "core.llm.gemini_client.resolve_gemini_model",
        side_effect=RuntimeError("boom"),
    ):
        _auth(client)
        resp = client.get("/api/health/gemini")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "degraded"
    assert data["configured"] is True
    assert data["model"] is None
    assert "boom" in (data["error"] or "")