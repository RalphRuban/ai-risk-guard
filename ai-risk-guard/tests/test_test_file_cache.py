"""
tests/test_test_file_cache.py
Tests for TestFileCache including NOT_FOUND-marker semantics used to skip
re-fetching test files and dependencies known to be missing.
"""

import uuid

from core.cache.test_file_cache import TestFileCache as _TestFileCache


class TestTestFileCache:
    def setup_method(self):
        self.cache = _TestFileCache()
        self.repo = f"test-repo-{uuid.uuid4().hex}"
        self.branch = f"branch-{uuid.uuid4().hex}"
        self.path = "tests/test_demo1.py"

    def test_miss_returns_none_and_no_entry(self):
        assert self.cache.has_entry(self.repo, self.branch, self.path) is False
        assert self.cache.get(self.repo, self.branch, self.path) is None

    def test_set_content_creates_entry(self):
        self.cache.set(self.repo, self.branch, self.path, "def test_f():\n    pass\n")
        assert self.cache.has_entry(self.repo, self.branch, self.path) is True
        assert self.cache.get(self.repo, self.branch, self.path) is not None

    def test_set_none_records_not_found_marker(self):
        other = "tests/conftest.py"
        self.cache.set(self.repo, self.branch, other, None)
        assert self.cache.has_entry(self.repo, self.branch, other) is True
        assert self.cache.get(self.repo, self.branch, other) is None

    def test_entry_is_scoped_to_path(self):
        self.cache.set(self.repo, self.branch, self.path, "def test_f():\n    pass\n")
        assert self.cache.has_entry(self.repo, self.branch, "tests/other.py") is False

    def test_entry_is_scoped_to_commit_sha(self):
        self.cache.set(self.repo, self.branch, self.path, "v1", commit_sha="abc123")
        assert self.cache.has_entry(self.repo, self.branch, self.path, "abc123") is True
        assert self.cache.get(self.repo, self.branch, self.path, "abc123") == "v1"
        assert self.cache.has_entry(self.repo, self.branch, self.path, "def456") is False
        assert self.cache.get(self.repo, self.branch, self.path, "def456") is None

    def test_empty_sha_falls_back_to_branch(self):
        self.cache.set(self.repo, self.branch, self.path, "v1")
        assert self.cache.has_entry(self.repo, self.branch, self.path) is True
        assert self.cache.get(self.repo, self.branch, self.path) == "v1"
