import hashlib
import logging
import threading
import time
from typing import Any

log = logging.getLogger("ai_risk_guard.cache.sandbox")


class SandboxCache:
    """Bounded, TTL'd result cache for sandbox runs, safe for concurrent use.

    The cache is mutated from the validator thread pool, so every entry is
    read/written under a lock. Entries expire after ``ttl_seconds`` and the
    cache is capped at ``max_entries`` (oldest entries dropped first).
    """

    def __init__(self, max_entries: int = 256, ttl_seconds: int = 3600):
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = threading.RLock()
        self._max_entries = max(max_entries, 1)
        self._ttl_seconds = float(ttl_seconds)

    def _make_key(self, code: str, test_file_content: str, mode: str, variant: str = "") -> str:
        raw = f"{code}|{test_file_content}|{mode}|{variant}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _now(self) -> float:
        return time.monotonic()

    def _prune(self, now: float):
        cutoff = now - self._ttl_seconds
        expired = [k for k, (ts, _) in self._cache.items() if ts < cutoff]
        for k in expired:
            del self._cache[k]
        if len(self._cache) <= self._max_entries:
            return
        oldest = sorted(self._cache.items(), key=lambda kv: kv[1][0])
        for k, _ in oldest[: len(self._cache) - self._max_entries]:
            del self._cache[k]

    def get(self, code: str, test_file_content: str = "", mode: str = "secure_validation", variant: str = "") -> dict[str, Any] | None:
        key = self._make_key(code, test_file_content, mode, variant)
        with self._lock:
            now = self._now()
            self._prune(now)
            entry = self._cache.get(key)
            if entry is None:
                return None
            inserted_at, result = entry
            if inserted_at < now - self._ttl_seconds:
                del self._cache[key]
                return None
            return result

    def set(self, code: str, test_file_content: str, mode: str, result: dict[str, Any], variant: str = ""):
        key = self._make_key(code, test_file_content, mode, variant)
        with self._lock:
            now = self._now()
            self._prune(now)
            self._cache[key] = (now, dict(result))
            if len(self._cache) > self._max_entries:
                self._prune(now)

    def invalidate(self):
        with self._lock:
            self._cache.clear()