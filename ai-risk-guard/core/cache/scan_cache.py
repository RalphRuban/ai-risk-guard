import hashlib
import json
import logging
from typing import Any

from utils.db import _connect

log = logging.getLogger("ai_risk_guard.cache.scan")


class ScanCache:
    def __init__(self):
        self._initialized = False

    def _init_table(self):
        if self._initialized:
            return
        try:
            with _connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS scan_cache (
                        cache_key TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        results TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        ttl_seconds INTEGER DEFAULT 3600
                    )
                """)
                conn.commit()
            self._initialized = True
        except Exception as e:
            log.error("Failed to initialize scan_cache table: %s", e)
            raise

    def _make_key(self, file_path: str, commit_hash: str = "") -> str:
        raw = f"{file_path}|{commit_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _observe_cache(self, hit: bool):
        try:
            from app.metrics import record_cache_event
            record_cache_event("scan", hit)
        except ImportError:
            pass

    def get(self, file_path: str, commit_hash: str = "") -> list[dict[str, Any]] | None:
        try:
            self._init_table()
            key = self._make_key(file_path, commit_hash)
            with _connect() as conn:
                row = conn.execute(
                    "SELECT results FROM scan_cache WHERE cache_key = ? "
                    "AND (strftime('%s', 'now') - strftime('%s', created_at)) < ttl_seconds",
                    (key,)
                ).fetchone()
            if row:
                self._observe_cache(True)
                return json.loads(row["results"])
            self._observe_cache(False)
            return None
        except Exception as e:
            log.error("ScanCache.get failed: %s", e)
            return None

    def set(self, file_path: str, commit_hash: str, results: list[dict[str, Any]]):
        try:
            self._init_table()
            key = self._make_key(file_path, commit_hash)
            with _connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO scan_cache (cache_key, file_path, results) VALUES (?, ?, ?)",
                    (key, file_path, json.dumps(results))
                )
                conn.commit()
        except Exception as e:
            log.error("ScanCache.set failed: %s", e)

    def get_function(self, file_path: str, function_name: str, commit_hash: str = "") -> list[dict[str, Any]] | None:
        try:
            self._init_table()
            raw = f"{file_path}|func:{function_name}|{commit_hash}"
            key = hashlib.sha256(raw.encode()).hexdigest()
            with _connect() as conn:
                row = conn.execute(
                    "SELECT results FROM scan_cache WHERE cache_key = ? "
                    "AND (strftime('%s', 'now') - strftime('%s', created_at)) < ttl_seconds",
                    (key,)
                ).fetchone()
            if row:
                return json.loads(row["results"])
            return None
        except Exception as e:
            log.error("ScanCache.get_function failed: %s", e)
            return None

    def set_function(self, file_path: str, function_name: str, commit_hash: str, results: list[dict[str, Any]]):
        try:
            self._init_table()
            raw = f"{file_path}|func:{function_name}|{commit_hash}"
            key = hashlib.sha256(raw.encode()).hexdigest()
            with _connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO scan_cache (cache_key, file_path, results) VALUES (?, ?, ?)",
                    (key, file_path, json.dumps(results))
                )
                conn.commit()
        except Exception as e:
            log.error("ScanCache.set_function failed: %s", e)

    def get_functions(self, file_path: str, function_names: list, commit_hash: str = "") -> list[dict[str, Any]]:
        merged = []
        for name in function_names:
            cached = self.get_function(file_path, name, commit_hash)
            if cached:
                merged.extend(cached)
        return merged

    def invalidate(self, file_path: str):
        try:
            self._init_table()
            with _connect() as conn:
                conn.execute(
                    "DELETE FROM scan_cache WHERE file_path = ?",
                    (file_path,)
                )
                conn.commit()
        except Exception as e:
            log.error("ScanCache.invalidate failed: %s", e)
