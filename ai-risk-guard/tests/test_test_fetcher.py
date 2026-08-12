"""
tests/test_test_fetcher.py
Tests for relevance-aware test discovery and dependency/conftest staging.
"""

from unittest.mock import patch

from core.scanner.test_file_fetcher import (
    discover_and_fetch_test_file,
    fetch_test_dependencies,
    is_relevant_test,
)


class _FakeCache:
    def __init__(self, entries=None):
        self.entries = dict(entries or {})

    def get(self, repo, branch, path, commit_sha=""):
        return self.entries.get((branch, commit_sha, path), self.entries.get(path))

    def set(self, repo, branch, path, content, commit_sha=""):
        self.entries[(branch, commit_sha, path)] = content

    def has_entry(self, repo, branch, path, commit_sha=""):
        return (branch, commit_sha, path) in self.entries or (path in self.entries and not commit_sha)


class TestRelevance:
    def test_accepts_test_importing_source_module(self):
        assert is_relevant_test("from demo1 import fetch_url\n", "demo1.py") is True

    def test_accepts_dotted_import_of_source_module(self):
        assert is_relevant_test("from src.demo1 import fetch_url\n", "demo1.py") is True

    def test_accepts_mirror_helper_named_after_source(self):
        assert is_relevant_test("from tests.foo import fetch_url\n", "foo.py") is True

    def test_rejects_test_importing_unrelated_module(self):
        assert is_relevant_test("from tests.demo import fetch_url\n", "demo1.py") is False

    def test_rejects_when_no_imports(self):
        assert is_relevant_test("def test_x():\n    assert True\n", "demo1.py") is False

    def test_rejects_empty_source(self):
        assert is_relevant_test("from demo1 import fetch_url\n", "") is False


class TestDiscoverRelevance:
    def _run(self, cache, source, fetch_map):
        def fake_fetch(repo, branch, path, token, ref="", timeout=10):
            return fetch_map.get(path)

        with patch(
            "core.scanner.test_file_fetcher.fetch_test_file_content",
            side_effect=fake_fetch,
        ):
            return discover_and_fetch_test_file("repo", "branch", source, "token", cache)

    def test_prefers_relevant_candidate_over_first_existing(self):
        cache = _FakeCache()
        fetch_map = {
            "demo1_test.py": "def test_helper():\n    assert True\n",
            "tests/test_demo1.py": "from demo1 import fetch_url\n\ndef test_f():\n    assert fetch_url()\n",
        }
        content, path = self._run(cache, "demo1.py", fetch_map)
        assert path == "tests/test_demo1.py"
        assert "demo1" in content

    def test_falls_back_to_first_existing_when_none_relevant(self):
        cache = _FakeCache()
        fetch_map = {
            "Demo1_test.py": "from tests.demo import fetch_url\n\ndef test_f():\n    assert fetch_url()\n",
        }
        _content, path = self._run(cache, "demo1.py", fetch_map)
        assert path == "Demo1_test.py"
        assert "tests.demo" in _content

    def test_cache_hit_relevant_shortcircuits(self):
        cache = _FakeCache({
            "tests/test_demo1.py": "from demo1 import fetch_url\n\ndef test_f():\n    assert fetch_url()\n",
        })

        with patch(
            "core.scanner.test_file_fetcher.fetch_test_file_content",
            side_effect=AssertionError("network must not be hit"),
        ):
            _content, path = discover_and_fetch_test_file("repo", "branch", "demo1.py", "token", cache)
        assert path == "tests/test_demo1.py"

    def test_returns_none_when_no_candidate_exists(self):
        cache = _FakeCache()
        _content, path = self._run(cache, "demo1.py", {})
        assert _content is None
        assert path is None

    def test_skips_network_for_cached_missing_candidates(self):
        cache = _FakeCache()
        self._run(cache, "demo1.py", {})

        with patch(
            "core.scanner.test_file_fetcher.fetch_test_file_content",
            side_effect=AssertionError("network must not be hit"),
        ):
            _content, path = discover_and_fetch_test_file("repo", "branch", "demo1.py", "token", cache)
        assert _content is None
        assert path is None

    def test_same_sha_served_from_cache(self):
        cache = _FakeCache()
        cache.set("repo", "branch", "tests/test_demo1.py",
                  "from demo1 import fetch_url\n\ndef test_f():\n    assert fetch_url()\n", "sha1")

        with patch(
            "core.scanner.test_file_fetcher.fetch_test_file_content",
            side_effect=AssertionError("network must not be hit"),
        ):
            _content, path = discover_and_fetch_test_file("repo", "branch", "demo1.py", "token", cache, commit_sha="sha1")
        assert path == "tests/test_demo1.py"

    def test_new_sha_invalidates_cached_candidate(self):
        cache = _FakeCache({"tests/test_demo1.py": "from demo1 import fetch_url\n\ndef test_f():\n    assert fetch_url()\n"})
        fetch_map = {"tests/test_demo1.py": "from demo1 import fetch_url\n\ndef test_f():\n    assert fetch_url()\n"}

        def fake_fetch(repo, branch, path, token, ref="", timeout=10):
            return fetch_map.get(path)

        with patch(
            "core.scanner.test_file_fetcher.fetch_test_file_content",
            side_effect=fake_fetch,
        ):
            content, path = discover_and_fetch_test_file("repo", "branch", "demo1.py", "token", cache, commit_sha="sha2")
        assert path == "tests/test_demo1.py"
        assert "demo1" in content


class TestFetchDependencies:
    def _run(self, cache, source, test_content, fetch_map, known=None):
        def fake_fetch(repo, branch, path, token, ref="", timeout=10):
            return fetch_map.get(path)

        with patch(
            "core.scanner.test_file_fetcher.fetch_test_file_content",
            side_effect=fake_fetch,
        ):
            return fetch_test_dependencies(
                "repo", "branch", source, test_content, "token", cache, known_packages=known or frozenset()
            )

    def test_fetches_helper_modules_and_conftest(self):
        cache = _FakeCache()
        fetch_map = {
            "tests/helpers.py": "def make_client():\n    return object()\n",
            "conftest.py": "import pytest\n",
        }
        deps = self._run(
            cache,
            "demo1.py",
            "from tests.helpers import make_client\n\ndef test_c():\n    assert make_client()\n",
            fetch_map,
        )
        paths = {d["path"] for d in deps}
        assert "tests/helpers.py" in paths
        assert "conftest.py" in paths
        assert all(d["content"] for d in deps)

    def test_excludes_module_under_test(self):
        cache = _FakeCache()
        fetch_map = {
            "demo1.py": "def fetch_url():\n    return 'ok'\n",
        }
        deps = self._run(cache, "demo1.py", "from demo1 import fetch_url\n\ndef test_f():\n    assert fetch_url()\n", fetch_map)
        assert deps == []

    def test_excludes_stdlib_and_known_packages(self):
        cache = _FakeCache()
        deps = self._run(
            cache,
            "demo1.py",
            "import os\nfrom dotenv import load_dotenv\n\ndef test_x():\n    load_dotenv()\n",
            {},
            known=frozenset({"dotenv"}),
        )
        assert deps == []

    def test_uses_cache_for_deps(self):
        cache = _FakeCache({"tests/helpers.py": "def make_client():\n    return object()\n"})

        def fake_fetch(repo, branch, path, token, ref="", timeout=10):
            if path == "tests/helpers.py":
                raise AssertionError("cached dep must not hit network")

        with patch(
            "core.scanner.test_file_fetcher.fetch_test_file_content",
            side_effect=fake_fetch,
        ):
            deps = fetch_test_dependencies(
                "repo",
                "branch",
                "demo1.py",
                "from tests.helpers import make_client\n\ndef test_c():\n    assert make_client()\n",
                "token",
                cache,
            )
        assert {d["path"] for d in deps} == {"tests/helpers.py"}

    def test_skips_network_for_cached_missing_deps(self):
        cache = _FakeCache()
        self._run(
            cache,
            "demo1.py",
            "from tests.helpers import make_client\n\ndef test_c():\n    assert make_client()\n",
            {},
        )

        with patch(
            "core.scanner.test_file_fetcher.fetch_test_file_content",
            side_effect=AssertionError("network must not be hit"),
        ):
            deps = fetch_test_dependencies(
                "repo",
                "branch",
                "demo1.py",
                "from tests.helpers import make_client\n\ndef test_c():\n    assert make_client()\n",
                "token",
                cache,
            )
        assert deps == []

    def test_deps_same_sha_served_from_cache(self):
        cache = _FakeCache()
        for path in ("tests/helpers/__init__.py", "tests/__init__.py", "conftest.py", "tests/conftest.py"):
            cache.set("repo", "branch", path, None, "sha1")
        cache.set("repo", "branch", "tests/helpers.py",
                  "def make_client():\n    return object()\n", "sha1")

        with patch(
            "core.scanner.test_file_fetcher.fetch_test_file_content",
            side_effect=AssertionError("network must not be hit"),
        ):
            deps = fetch_test_dependencies(
                "repo",
                "branch",
                "demo1.py",
                "from tests.helpers import make_client\n\ndef test_c():\n    assert make_client()\n",
                "token",
                cache,
                commit_sha="sha1",
            )
        assert {d["path"] for d in deps} == {"tests/helpers.py"}

    def test_deps_new_sha_refetches(self):
        cache = _FakeCache()
        fetch_map = {"tests/helpers.py": "def make_client():\n    return object()\n"}

        def fake_fetch(repo, branch, path, token, ref="", timeout=10):
            return fetch_map.get(path)

        with patch(
            "core.scanner.test_file_fetcher.fetch_test_file_content",
            side_effect=fake_fetch,
        ):
            deps = fetch_test_dependencies(
                "repo",
                "branch",
                "demo1.py",
                "from tests.helpers import make_client\n\ndef test_c():\n    assert make_client()\n",
                "token",
                cache,
                commit_sha="sha2",
            )
        assert "tests/helpers.py" in {d["path"] for d in deps}
