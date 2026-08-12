import hashlib
import logging
from typing import Any

log = logging.getLogger("ai_risk_guard.cache.sandbox")


class SandboxCache:
    def __init__(self):
        self._cache: dict[str, dict[str, Any]] = {}

    def _make_key(self, code: str, test_file_content: str, mode: str, variant: str = "") -> str:
        raw = f"{code}|{test_file_content}|{mode}|{variant}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, code: str, test_file_content: str = "", mode: str = "secure_validation", variant: str = "") -> dict[str, Any] | None:
        key = self._make_key(code, test_file_content, mode, variant)
        return self._cache.get(key)

    def set(self, code: str, test_file_content: str, mode: str, result: dict[str, Any], variant: str = ""):
        key = self._make_key(code, test_file_content, mode, variant)
        self._cache[key] = result

    def invalidate(self):
        self._cache.clear()
