"""
tests/test_ngrok_bypass_warning.py
The tunnel deployment (deploy/azure-vm-tunnel-setup.sh) terminates HTTPS on a
free ngrok static domain, which shows a browser interstitial on first visit
unless responses carry the "ngrok-skip-browser-warning" header. The header is
emitted on every response only when NGROK_BYPASS_WARNING is set, and must never
leak into ordinary deployments or tests.
"""

from app.app import app as flask_app


def _client():
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def test_header_present_when_tunnel_enabled(monkeypatch):
    monkeypatch.setenv("NGROK_BYPASS_WARNING", "true")
    resp = _client().get("/api/health/ready")
    assert resp.status_code == 200
    assert resp.headers.get("ngrok-skip-browser-warning") == "true"


def test_header_absent_by_default(monkeypatch):
    monkeypatch.delenv("NGROK_BYPASS_WARNING", raising=False)
    resp = _client().get("/api/health/ready")
    assert resp.status_code == 200
    assert "ngrok-skip-browser-warning" not in resp.headers