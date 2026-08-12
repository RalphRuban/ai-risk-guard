"""
core/config/__init__.py
Config loader and registry for AI Risk Guard.
Loads YAML config files and validates them against Pydantic schemas.
"""

import logging
import os
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

from core.config.app_config import AppConfig
from core.config.policy_config import PolicyConfig
from core.config.quality_config import QualityConfig
from core.config.risk_config import RiskConfig
from core.config.sandbox_config import SandboxConfig

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"

M = TypeVar("M", bound=BaseModel)


class ConfigRegistry:
    """Central registry for all configuration objects."""

    def __init__(self):
        self._app: AppConfig | None = None
        self._sandbox: SandboxConfig | None = None
        self._risk: RiskConfig | None = None
        self._policy: PolicyConfig | None = None
        self._quality: QualityConfig | None = None
        self._logger = logging.getLogger("ai_risk_guard.config")

    @property
    def app(self) -> AppConfig:
        if self._app is None:
            self._app = self._load("app.yaml", AppConfig)
        return self._app

    @property
    def sandbox(self) -> SandboxConfig:
        if self._sandbox is None:
            self._sandbox = self._load("sandbox.yaml", SandboxConfig)
        return self._sandbox

    @property
    def risk(self) -> RiskConfig:
        if self._risk is None:
            self._risk = self._load("risk.yaml", RiskConfig)
        return self._risk

    @property
    def policy(self) -> PolicyConfig:
        if self._policy is None:
            self._policy = self._load("policy/default.yaml", PolicyConfig)
        return self._policy

    @property
    def quality(self) -> QualityConfig:
        if self._quality is None:
            self._quality = self._load("quality.yaml", QualityConfig)
        return self._quality

    def reload(self):
        """Force reload all configs from disk."""
        self._app = None
        self._sandbox = None
        self._risk = None
        self._policy = None
        self._quality = None

    def _load(self, yaml_path: str, model_class: type[M]) -> M:
        full_path = _CONFIG_DIR / yaml_path
        if not full_path.exists():
            self._logger.warning("Config file not found: %s. Using defaults.", full_path)
            return model_class()

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            return model_class(**raw)
        except (yaml.YAMLError, Exception) as e:
            self._logger.error(
                "Failed to load config %s: %s. Using defaults.", yaml_path, e
            )
            return model_class()

    @staticmethod
    def env_override(key: str, default: str = "") -> str:
        """Read a value from environment variables with fallback."""
        return os.environ.get(key, default)


# Global singleton
config = ConfigRegistry()

__all__ = [
    "AppConfig",
    "ConfigRegistry",
    "PolicyConfig",
    "QualityConfig",
    "RiskConfig",
    "SandboxConfig",
    "config",
]
