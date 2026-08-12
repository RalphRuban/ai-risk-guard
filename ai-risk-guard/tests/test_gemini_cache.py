"""
tests/test_gemini_cache.py
Tests for Gemini API response cache with SQLite backend and TTL enforcement.
"""

from core.cache.gemini_cache import GeminiCache


class TestGeminiCache:
    def setup_method(self):
        self.cache = GeminiCache()

    def test_set_and_get_roundtrip(self):
        prompt = "def foo(): pass"
        response = "def foo(): return 42"
        self.cache.set(prompt, response)
        result = self.cache.get(prompt)
        assert result == response

    def test_get_miss_returns_none(self):
        result = self.cache.get("nonexistent prompt")
        assert result is None

    def test_invalidate_removes_expired(self):
        self.cache.set("some prompt", "some response")
        self.cache.invalidate()
        # invalidate only removes expired entries, so recent entry should survive
        result = self.cache.get("some prompt")
        assert result is not None

    def test_invalidate_removes_stale_entries(self):
        from utils.db import _connect
        self.cache.set("stale_key", "stale_value")
        with _connect() as conn:
            conn.execute(
                "UPDATE gemini_cache SET created_at = datetime('now', '-2 days') WHERE cache_key = ?",
                (self.cache._hash_prompt("stale_key"),)
            )
            conn.commit()
        self.cache.invalidate()
        result = self.cache.get("stale_key")
        assert result is None

    def test_same_prompt_same_hash(self):
        hash1 = self.cache._hash_prompt("hello world")
        hash2 = self.cache._hash_prompt("hello world")
        hash3 = self.cache._hash_prompt("hello world!")
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64
        assert all(c in "0123456789abcdef" for c in hash1)

    def test_observe_cache_no_crash_without_metrics(self):
        self.cache._observe_cache(True)
        self.cache._observe_cache(False)

    def test_invalidate_key_removes_specific_entry(self):
        prompt_a = "prompt A"
        prompt_b = "prompt B"
        self.cache.set(prompt_a, "response A")
        self.cache.set(prompt_b, "response B")
        self.cache.invalidate_key(prompt_a)
        assert self.cache.get(prompt_a) is None
        assert self.cache.get(prompt_b) == "response B"

    def test_invalidate_key_noop_on_missing_key(self):
        self.cache.set("existing", "value")
        self.cache.invalidate_key("nonexistent")
        assert self.cache.get("existing") == "value"
