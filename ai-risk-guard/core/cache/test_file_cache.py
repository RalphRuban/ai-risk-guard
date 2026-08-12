import hashlib
import logging

from utils.db import _connect

log = logging.getLogger("ai_risk_guard.cache.test_file")


class TestFileCache:
    def __init__(self):
        self._initialized = False

    def _init_table(self):
        if self._initialized:
            return
        try:
            with _connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS test_file_cache (
                        cache_key TEXT PRIMARY KEY,
                        repo TEXT NOT NULL,
                        branch TEXT NOT NULL,
                        test_file_path TEXT NOT NULL,
                        content TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        ttl_seconds INTEGER DEFAULT 86400
                    )
                """)
                conn.commit()
            self._initialized = True
        except Exception as e:
            log.error("Failed to initialize test_file_cache table: %s", e)
            raise

    def _make_key(self, repo: str, branch: str, test_file_path: str, commit_sha: str = "") -> str:
        if commit_sha:
            raw = f"{repo}|{branch}|{commit_sha}|{test_file_path}"
        else:
            raw = f"{repo}|{branch}|{test_file_path}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, repo: str, branch: str, test_file_path: str, commit_sha: str = "") -> str | None:
        try:
            self._init_table()
            key = self._make_key(repo, branch, test_file_path, commit_sha)
            with _connect() as conn:
                row = conn.execute(
                    "SELECT content FROM test_file_cache WHERE cache_key = ? "
                    "AND (strftime('%s', 'now') - strftime('%s', created_at)) < ttl_seconds",
                    (key,)
                ).fetchone()
            if row:
                content = row["content"]
                return None if content is None or content == "NOT_FOUND" else content
            return None
        except Exception as e:
            log.error("TestFileCache.get failed: %s", e)
            return None

    def has_entry(self, repo: str, branch: str, test_file_path: str, commit_sha: str = "") -> bool:
        """Return True when a non-expired cache entry exists.

        Unlike :meth:`get`, this is True for both cached content and a cached
        ``NOT_FOUND`` marker, letting callers skip network fetches for paths
        already known to be missing.
        """
        try:
            self._init_table()
            key = self._make_key(repo, branch, test_file_path, commit_sha)
            with _connect() as conn:
                row = conn.execute(
                    "SELECT 1 FROM test_file_cache WHERE cache_key = ? "
                    "AND (strftime('%s', 'now') - strftime('%s', created_at)) < ttl_seconds",
                    (key,)
                ).fetchone()
            return row is not None
        except Exception as e:
            log.error("TestFileCache.has_entry failed: %s", e)
            return False

    def set(self, repo: str, branch: str, test_file_path: str, content: str | None, commit_sha: str = ""):
        try:
            self._init_table()
            key = self._make_key(repo, branch, test_file_path, commit_sha)
            content_to_store = "NOT_FOUND" if content is None else content
            with _connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO test_file_cache "
                    "(cache_key, repo, branch, test_file_path, content, created_at) "
                    "VALUES (?, ?, ?, ?, ?, datetime('now'))",
                    (key, repo, branch, test_file_path, content_to_store)
                )
                conn.commit()
        except Exception as e:
            log.error("TestFileCache.set failed: %s", e)

    def invalidate(self):
        try:
            self._init_table()
            with _connect() as conn:
                conn.execute(
                    "DELETE FROM test_file_cache WHERE "
                    "(strftime('%s', 'now') - strftime('%s', created_at)) >= ttl_seconds"
                )
                conn.commit()
        except Exception as e:
            log.error("TestFileCache.invalidate failed: %s", e)
