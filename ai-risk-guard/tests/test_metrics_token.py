"""
tests/test_metrics_token.py
Tests for Section B7: /api/metrics/prometheus is scrapable with a
METRICS_SCRAPE_TOKEN (Bearer) without a browser session, and keeps requiring a
session when the token is unset.
"""

import pytest

from app.app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def test_metrics_requires_session_when_token_unset(client, monkeypatch):
    monkeypatch.delenv("METRICS_SCRAPE_TOKEN", raising=False)
    resp = client.get("/api/metrics/prometheus")
    assert resp.status_code == 401


def test_metrics_allows_session_when_token_unset(client, monkeypatch):
    monkeypatch.delenv("METRICS_SCRAPE_TOKEN", raising=False)
    with client.session_transaction() as sess:
        sess["user"] = {"github_id": "111", "login": "alice"}
    resp = client.get("/api/metrics/prometheus")
    assert resp.status_code == 200


def test_metrics_bearer_token_without_session(client, monkeypatch):
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", "scrape-secret")
    resp = client.get(
        "/api/metrics/prometheus",
        headers={"Authorization": "Bearer scrape-secret"},
    )
    assert resp.status_code == 200
    assert "text/plain" in resp.content_type


def test_metrics_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", "scrape-secret")
    resp = client.get(
        "/api/metrics/prometheus",
        headers={"Authorization": "Bearer wrong"},
    )
    assert resp.status_code == 401


def test_metrics_rejects_missing_auth_when_token_set(client, monkeypatch):
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", "scrape-secret")
    resp = client.get("/api/metrics/prometheus")
    assert resp.status_code == 401