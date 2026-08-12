import hashlib
import logging

from utils.db import _connect

log = logging.getLogger("ai_risk_guard.cache.gemini")


class GeminiCache:
    def __init__(self):
        self._initialized = False

    def _init_table(self):
        if self._initialized:
            return
        try:
            with _connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS gemini_cache (
                        cache_key TEXT PRIMARY KEY,
                        response TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        ttl_seconds INTEGER DEFAULT 86400
                    )
                """)
                conn.commit()
            self._initialized = True
        except Exception as e:
            log.error("Failed to initialize gemini_cache table: %s", e)
            raise

    def _hash_prompt(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()

    def _observe_cache(self, hit: bool):
        try:
            from app.metrics import record_cache_event
            record_cache_event("gemini", hit)
        except ImportError:
            pass

    def get(self, prompt: str) -> str | None:
        try:
            self._init_table()
            key = self._hash_prompt(prompt)
            with _connect() as conn:
                row = conn.execute(
                    "SELECT response FROM gemini_cache WHERE cache_key = ? "
                    "AND (strftime('%s', 'now') - strftime('%s', created_at)) < ttl_seconds",
                    (key,)
                ).fetchone()
            if row:
                self._observe_cache(True)
                return row["response"]
            self._observe_cache(False)
            return None
        except Exception as e:
            log.error("GeminiCache.get failed: %s", e)
            return None

    def set(self, prompt: str, response: str):
        try:
            self._init_table()
            key = self._hash_prompt(prompt)
            with _connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO gemini_cache (cache_key, response, created_at) "
                    "VALUES (?, ?, datetime('now'))",
                    (key, response)
                )
                conn.commit()
        except Exception as e:
            log.error("GeminiCache.set failed: %s", e)

    def invalidate(self):
        try:
            self._init_table()
            with _connect() as conn:
                conn.execute(
                    "DELETE FROM gemini_cache WHERE "
                    "(strftime('%s', 'now') - strftime('%s', created_at)) >= ttl_seconds"
                )
                conn.commit()
        except Exception as e:
            log.error("GeminiCache.invalidate failed: %s", e)

    def invalidate_key(self, prompt: str):
        try:
            self._init_table()
            key = self._hash_prompt(prompt)
            with _connect() as conn:
                conn.execute("DELETE FROM gemini_cache WHERE cache_key = ?", (key,))
                conn.commit()
        except Exception as e:
            log.error("GeminiCache.invalidate_key failed: %s", e)
