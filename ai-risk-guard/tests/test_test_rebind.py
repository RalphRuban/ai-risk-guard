"""
tests/test_test_rebind.py
Tests for best-effort test-import rebinding to the patched module.
"""

from core.validator.test_rebind import (
    _module_names,
    _source_module_path,
    rebind_test_imports,
)


class TestRebindTestImports:
    def test_rebinds_full_match_import_from(self):
        test_content = (
            "from tests.demo import fetch_url, API_TOKEN\n"
            "\n"
            "\n"
            "def test_fetch():\n"
            "    assert fetch_url() == API_TOKEN\n"
        )
        source_code = "API_TOKEN = 'x'\n\ndef fetch_url():\n    return 'ok'\n"
        content, info = rebind_test_imports(test_content, source_code, "demo1.py", {"tests"})
        assert info["rebound"] is True
        assert info["skip"] is False
        assert info["rebound_map"] == {"tests.demo": "demo1"}
        assert "from demo1 import fetch_url, API_TOKEN" in content
        assert "from tests.demo" not in content

    def test_skips_when_partial_names_missing(self):
        test_content = (
            "from tests.demo import fetch_url, API_TOKEN\n"
            "\n"
            "\n"
            "def test_fetch():\n"
            "    assert fetch_url() == API_TOKEN\n"
        )
        source_code = "def fetch_url():\n    return 'ok'\n"
        content, info = rebind_test_imports(test_content, source_code, "demo1.py", {"tests"})
        assert info["skip"] is True
        assert info["rebound"] is False
        assert "API_TOKEN" in info["reason"]
        assert content == test_content

    def test_skip_reports_offending_modules(self):
        test_content = (
            "from tests.demo import fetch_url, API_TOKEN\n"
            "from tests.helpers import fetch_url, make_client\n"
            "\n"
            "\n"
            "def test_fetch():\n"
            "    assert fetch_url() == API_TOKEN\n"
            "    assert make_client()\n"
        )
        source_code = "def fetch_url():\n    return 'ok'\n"
        _content, info = rebind_test_imports(test_content, source_code, "demo1.py", {"tests"})
        assert info["skip"] is True
        assert info["missing_modules"] == ["tests.demo", "tests.helpers"]

    def test_leaves_third_party_import_untouched_when_no_names_match(self):
        test_content = "from dotenv import load_dotenv\n\ndef test_env():\n    load_dotenv()\n"
        source_code = "def fetch_url():\n    return 'ok'\n"
        content, info = rebind_test_imports(test_content, source_code, "demo1.py", {"dotenv"})
        assert info["rebound"] is False
        assert info["skip"] is False
        assert content == test_content

    def test_leaves_plain_import_untouched(self):
        test_content = "import tests.demo\n\ndef test_fetch():\n    assert tests.demo.fetch_url()\n"
        source_code = "def fetch_url():\n    return 'ok'\n"
        content, info = rebind_test_imports(test_content, source_code, "demo1.py", {"tests"})
        assert info["rebound"] is False
        assert info["skip"] is False
        assert content == test_content

    def test_no_change_without_candidate_roots(self):
        test_content = "from tests.demo import fetch_url\n"
        content, info = rebind_test_imports(test_content, "def fetch_url(): pass", "demo1.py", set())
        assert content == test_content
        assert info["rebound"] is False

    def test_handles_syntax_error_gracefully(self):
        test_content = "def broken("
        content, info = rebind_test_imports(test_content, "def fetch_url(): pass", "demo1.py", {"tests"})
        assert content == test_content
        assert info["rebound"] is False

    def test_skips_when_source_fails_to_parse(self):
        test_content = "from tests.demo import fetch_url\n\n\ndef test_f():\n    fetch_url()\n"
        content, info = rebind_test_imports(test_content, "def broken(", "demo1.py", {"tests"})
        assert info["skip"] is True
        assert info["rebound"] is False
        assert "could not be parsed" in info["reason"]
        assert content == test_content

    def test_subdir_source_filename_uses_dotted_path(self):
        test_content = "from tests.demo import fetch_url\n\n\ndef test_fetch():\n    fetch_url()\n"
        source_code = "def fetch_url():\n    return 'ok'\n"
        content, info = rebind_test_imports(test_content, source_code, "src/demo1.py", {"tests"})
        assert info["rebound"] is True
        assert "from src.demo1 import fetch_url" in content

    def test_requires_source_code_and_filename(self):
        content, info = rebind_test_imports("from tests.demo import fetch_url", "def fetch_url(): pass", "", {"tests"})
        assert content == "from tests.demo import fetch_url"
        assert info["rebound"] is False
        content, info = rebind_test_imports("from tests.demo import fetch_url", "", "demo1.py", {"tests"})
        assert content == "from tests.demo import fetch_url"
        assert info["rebound"] is False


class TestModuleNames:
    def test_collects_functions_classes_constants_imports(self):
        code = (
            "import os\n"
            "from urllib import parse\n"
            "API_TOKEN = 'abc'\n"
            "def fetch_url():\n"
            "    return 'x'\n"
            "class Client:\n"
            "    pass\n"
            "value = 1\n"
            "value += 2\n"
            "counter: int = 0\n"
        )
        names = _module_names(code)
        for expected in ("os", "parse", "API_TOKEN", "fetch_url", "Client", "value", "counter"):
            assert expected in names

    def test_empty_on_syntax_error(self):
        assert _module_names("def (") == set()


class TestSourceModulePath:
    def test_flat_file(self):
        assert _source_module_path("demo1.py") == "demo1"

    def test_subdirectory(self):
        assert _source_module_path("src/demo1.py") == "src.demo1"

    def test_windows_separators(self):
        assert _source_module_path("src\\demo1.py") == "src.demo1"
