import _ast
import ast
import hashlib
import io
import logging
import pickle
from typing import Any

from utils.db import _connect

log = logging.getLogger("ai_risk_guard.cache.ast")


class _SafeASTUnpickler(pickle.Unpickler):
    """Restrict unpickling to AST node types only."""
    def find_class(self, module, name):
        if module in ("ast", "_ast"):
            cls = getattr(ast, name, None) or getattr(_ast, name, None)
            if cls is not None:
                return cls
        raise pickle.UnpicklingError(f"Refusing to load {module}.{name}")


class ASTCache:
    def __init__(self):
        self._initialized = False

    @staticmethod
    def _observe_cache(hit: bool):
        try:
            from app.metrics import record_cache_event
            record_cache_event("ast", hit)
        except ImportError:
            pass

    def _init_table(self):
        if self._initialized:
            return
        try:
            with _connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ast_cache (
                        cache_key TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL DEFAULT '',
                        tree BLOB NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        ttl_seconds INTEGER DEFAULT 86400
                    )
                """)
                try:
                    conn.execute("ALTER TABLE ast_cache ADD COLUMN file_path TEXT NOT NULL DEFAULT ''")
                except Exception:
                    pass
                conn.commit()
            self._initialized = True
        except Exception as e:
            log.error("Failed to initialize ast_cache table: %s", e)
            raise

    def _make_key(self, file_path: str, content_hash: str) -> str:
        raw = f"{file_path}|{content_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, file_path: str, content_hash: str) -> Any | None:
        try:
            self._init_table()
            key = self._make_key(file_path, content_hash)
            with _connect() as conn:
                row = conn.execute(
                    "SELECT tree FROM ast_cache WHERE cache_key = ? "
                    "AND (strftime('%s', 'now') - strftime('%s', created_at)) < ttl_seconds",
                    (key,)
                ).fetchone()
            if row:
                blob = row["tree"]
                if isinstance(blob, memoryview):
                    blob = bytes(blob)
                elif not isinstance(blob, bytes):
                    blob = bytes(blob, encoding="utf-8")
                self._observe_cache(True)
                return _SafeASTUnpickler(io.BytesIO(blob)).load()
            self._observe_cache(False)
            return None
        except Exception as e:
            log.error("ASTCache.get failed: %s", e)
            return None

    def set(self, file_path: str, content_hash: str, tree: Any):
        try:
            self._init_table()
            key = self._make_key(file_path, content_hash)
            with _connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO ast_cache (cache_key, file_path, tree, created_at) VALUES (?, ?, ?, datetime('now'))",
                    (key, file_path, pickle.dumps(tree))
                )
                conn.commit()
        except Exception as e:
            log.error("ASTCache.set failed: %s", e)

    def invalidate(self, file_path: str):
        try:
            self._init_table()
            with _connect() as conn:
                conn.execute(
                    "DELETE FROM ast_cache WHERE file_path = ?",
                    (file_path,)
                )
                conn.commit()
        except Exception as e:
            log.error("ASTCache.invalidate failed: %s", e)
