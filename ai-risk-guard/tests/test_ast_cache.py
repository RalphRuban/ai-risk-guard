"""
tests/test_ast_cache.py
Tests for AST parse cache with SQLite backend and TTL enforcement.
"""

import ast
import os
import pickle
import tempfile
from pathlib import Path
from unittest.mock import patch

from core.cache.ast_cache import ASTCache, _SafeASTUnpickler


class TestASTCache:
    def setup_method(self):
        import utils.db as udb
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        self._db_patcher = patch.object(udb, "DB_PATH", Path(self._tmp))
        self._db_patcher.start()
        self.cache = ASTCache()
        self.file_path = "test_ast.py"
        self.content_hash = "abc123def456"

    def teardown_method(self):
        self._db_patcher.stop()
        try: os.unlink(self._tmp)
        except (PermissionError, FileNotFoundError): pass

    def test_set_and_get_roundtrip(self):
        tree = ast.parse("x = 1")
        self.cache.set(self.file_path, self.content_hash, tree)
        result = self.cache.get(self.file_path, self.content_hash)
        assert result is not None
        assert isinstance(result, ast.Module)
        assert len(result.body) == 1

    def test_get_miss_returns_none(self):
        result = self.cache.get("nonexistent.py", "deadbeef")
        assert result is None

    def test_invalidate_clears_entries(self):
        tree = ast.parse("y = 2")
        self.cache.set(self.file_path, self.content_hash, tree)
        self.cache.invalidate(self.file_path)
        assert self.cache.get(self.file_path, self.content_hash) is None

    def test_safe_unpickler_rejects_non_ast(self):
        payload = pickle.dumps(int)
        import io
        buf = io.BytesIO(payload)
        with self._expect_unpickling_error():
            _SafeASTUnpickler(buf).load()

    def _expect_unpickling_error(self):
        import pytest
        return pytest.raises(pickle.UnpicklingError)

    def test_make_key_deterministic(self):
        key1 = self.cache._make_key("foo.py", "hash1")
        key2 = self.cache._make_key("foo.py", "hash1")
        key3 = self.cache._make_key("foo.py", "hash2")
        assert key1 == key2
        assert key1 != key3
        assert len(key1) == 64
        assert all(c in "0123456789abcdef" for c in key1)
