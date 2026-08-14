"""
tests/test_env_required.py
Tests for production startup env checks (Section A4): APP_ENV=production must
fail startup when required secrets are missing, while dev continues with
warnings only.
"""

import pytest

from app.app import _check_required_env

_REQUIRED = (
    "GITHUB_WEBHOOK_SECRET",
    "GITHUB_APP_ID",
    "GITHUB_PRIVATE_KEY",
    "GITHUB_APP_CLIENT_ID",
    "GITHUB_APP_CLIENT_SECRET",
    "FLASK_SECRET_KEY",
)


def test_non_production_does_not_raise(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    for var in _REQUIRED:
        monkeypatch.delenv(var, raising=False)
    _check_required_env()


def test_production_with_all_required_present(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    for var in _REQUIRED:
        monkeypatch.setenv(var, "x")
    _check_required_env()


def test_production_missing_required_raises(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    for var in _REQUIRED:
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(RuntimeError, match="APP_ENV=production requires"):
        _check_required_env()


def test_production_missing_flask_secret_raises(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    for var in _REQUIRED:
        if var == "FLASK_SECRET_KEY":
            monkeypatch.delenv(var, raising=False)
        else:
            monkeypatch.setenv(var, "x")
    with pytest.raises(RuntimeError, match="FLASK_SECRET_KEY"):
        _check_required_env()