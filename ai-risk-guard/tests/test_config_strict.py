"""
tests/test_config_strict.py
Tests for strict config loading (Section A3): malformed YAML or a Pydantic
validation error must fail fast by default, while CONFIG_STRICT=0 restores the
lenient dev behavior (log + defaults).
"""

import pytest

import core.config as config_module
from core.config import ConfigRegistry
from core.config.app_config import AppConfig


def _registry(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_DIR", tmp_path)
    return ConfigRegistry()


def test_missing_file_uses_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("CONFIG_STRICT", raising=False)
    registry = _registry(tmp_path, monkeypatch)
    cfg = registry._load("app.yaml", AppConfig)
    assert isinstance(cfg, AppConfig)
    assert cfg.server.port == 8000


def test_strict_mode_raises_on_bad_yaml(tmp_path, monkeypatch):
    monkeypatch.delenv("CONFIG_STRICT", raising=False)
    (tmp_path / "app.yaml").write_text("server:\n    port: [8000\n", encoding="utf-8")
    registry = _registry(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError, match="Invalid configuration file app.yaml"):
        registry._load("app.yaml", AppConfig)


def test_strict_mode_raises_on_validation_error(tmp_path, monkeypatch):
    monkeypatch.delenv("CONFIG_STRICT", raising=False)
    (tmp_path / "app.yaml").write_text("server:\n  port: \"abc\"\n", encoding="utf-8")
    registry = _registry(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError, match="Invalid configuration file app.yaml"):
        registry._load("app.yaml", AppConfig)


def test_lenient_mode_falls_back_to_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_STRICT", "0")
    (tmp_path / "app.yaml").write_text("server:\n  port: \"abc\"\n", encoding="utf-8")
    registry = _registry(tmp_path, monkeypatch)
    cfg = registry._load("app.yaml", AppConfig)
    assert isinstance(cfg, AppConfig)
    assert cfg.server.port == 8000
