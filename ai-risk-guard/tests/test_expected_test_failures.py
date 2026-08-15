"""
tests/test_expected_test_failures.py

Unit tests for diff-based expected-failure attribution: a regression test that
pins the vulnerable behavior a patch removes is expected to fail and must not
be reported as a regression.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.validator.expected_test_failures import (
    analyze_test_results,
    changed_symbols,
    classify,
    parse_test_outcomes,
)

ORIGINAL = """\
import hashlib
import json
import re
import sqlite3
import subprocess
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

import requests

API_TOKEN = "tok_live_a1b2c3d4e5f6g7h8"


def fetch_url(target_url):
    headers = {"User-Agent": "LinkChecker/1.0", "Authorization": f"Bearer {API_TOKEN}"}
    resp = requests.get(target_url, headers=headers, timeout=15)
    return resp.status_code, resp.text


def extract_title(html):
    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    return match.group(1).strip() if match else "No title"


def extract_links(html, base_url):
    raw = re.findall(r'href=["\\']([^"\\']+)["\\']', html)
    return [urljoin(base_url, link) for link in raw]


def hash_content(content):
    return hashlib.md5(content.encode()).hexdigest()


def save_results(db, url, title, link_count, content_hash, status):
    cursor = db.cursor()
    cursor.execute(
        f"INSERT INTO scan_results VALUES ('{url}', {status}, '{title}', "
        f"{link_count}, '{content_hash}', '{datetime.now(UTC).isoformat()}')"
    )
    db.commit()


def export_json(data, url):
    hostname = urlparse(url).hostname or "unknown"
    with open(f"report_{hostname}.json", "w") as f:
        json.dump(data, f, indent=2)


def run_diagnostics(domain):
    result = subprocess.run(
        f"ping -c 2 {domain}",
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout
"""

PATCHED = """\
import hashlib
import json
import os
import re
import shlex
import sqlite3
import subprocess
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

import requests

API_TOKEN = os.getenv('API_TOKEN')


def validate_url_ssrf(url):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError('Invalid URL scheme')
    return url


def safe_path_join(base_dir, user_path):
    import os
    base = os.path.realpath(base_dir)
    full = os.path.realpath(os.path.join(base, user_path))
    if not full.startswith(base + os.sep) and full != base:
        raise ValueError("Path traversal detected")
    return os.path.normpath(os.path.join(base_dir, user_path))


def fetch_url(target_url):
    headers = {"User-Agent": "LinkChecker/1.0", "Authorization": f"Bearer {API_TOKEN}"}
    resp = requests.get(validate_url_ssrf(target_url), headers=headers, timeout=15)
    return resp.status_code, resp.text


def extract_title(html):
    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    return match.group(1).strip() if match else "No title"


def extract_links(html, base_url):
    raw = re.findall(r'href=["\\']([^"\\']+)["\\']', html)
    return [urljoin(base_url, link) for link in raw]


def hash_content(content):
    return hashlib.sha256(content.encode()).hexdigest()


def save_results(db, url, title, link_count, content_hash, status):
    cursor = db.cursor()
    cursor.execute('INSERT INTO scan_results VALUES (?, ?, ?, ?, ?, ?)',
                   (url, status, title, link_count, content_hash, datetime.now(UTC).isoformat()))
    db.commit()


def export_json(data, url):
    hostname = urlparse(url).hostname or "unknown"
    with open(safe_path_join('.', f'report_{hostname}.json'), 'w') as f:
        json.dump(data, f, indent=2)


def run_diagnostics(domain):
    result = subprocess.run(shlex.split(f'ping -c 2 {domain}'),
                            capture_output=True, text=True, shell=False)
    return result.stdout
"""

TESTS = """\
from unittest.mock import MagicMock, patch

from tests.demo import (
    API_TOKEN,
    export_json,
    extract_links,
    extract_title,
    fetch_url,
    hash_content,
    run_diagnostics,
    save_results,
)


def test_secret_exists():
    assert API_TOKEN == "tok_live_a1b2c3d4e5f6g7h8"


@patch("requests.get")
def test_fetch_url(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><title>Test</title></html>"
    mock_get.return_value = mock_resp

    status, html = fetch_url("https://example.com")
    assert status == 200
    assert "Test" in html
    mock_get.assert_called_once_with(
        "https://example.com",
        headers={
            "User-Agent": "LinkChecker/1.0",
            "Authorization": "Bearer tok_live_a1b2c3d4e5f6g7h8",
        },
        timeout=15,
    )


def test_extract_title():
    assert extract_title("<html><head><title>My Page</title></head></html>") == "My Page"


def test_extract_title_no_match():
    assert extract_title("<html></html>") == "No title"


def test_extract_links():
    html = '<a href="/page1">A</a><a href="https://other.com">B</a>'
    assert extract_links(html, "https://example.com") == [
        "https://example.com/page1",
        "https://other.com",
    ]


def test_hash_content():
    assert hash_content("hello") == "5d41402abc4b2a76b9719d911017c592"


def test_save_results():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    save_results(mock_conn, "https://example.com", "Test Page", 5, "abc123", 200)

    sql = mock_cursor.execute.call_args[0][0]
    assert "https://example.com" in sql
    assert "Test Page" in sql
    assert "INSERT INTO scan_results" in sql
    mock_conn.commit.assert_called_once()


@patch("builtins.open", create=True)
def test_export_json(mock_open):
    mock_file = MagicMock()
    mock_file.write = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    export_json({"url": "https://example.com"}, "https://example.com")
    mock_open.assert_called_once_with("report_example.com.json", "w")


@patch("subprocess.run")
def test_run_diagnostics(mock_run):
    mock_result = MagicMock()
    mock_result.stdout = "PING example.com (93.184.216.34)..."
    mock_run.return_value = mock_result

    result = run_diagnostics("example.com")
    assert "PING example.com" in result
    mock_run.assert_called_once_with(
        "ping -c 2 example.com",
        shell=True,
        capture_output=True,
        text=True,
    )
"""

VERBOSE_OUTPUT = """\
============================= test session starts ==============================
collected 9 items

demo1_test.py::test_secret_exists FAILED                                 [ 11%]
demo1_test.py::test_fetch_url FAILED                                     [ 22%]
demo1_test.py::test_extract_title PASSED                                 [ 33%]
demo1_test.py::test_extract_title_no_match PASSED                        [ 44%]
demo1_test.py::test_extract_links PASSED                                 [ 55%]
demo1_test.py::test_hash_content FAILED                                  [ 66%]
demo1_test.py::test_save_results FAILED                                  [ 77%]
demo1_test.py::test_export_json PASSED                                   [ 88%]
demo1_test.py::test_run_diagnostics FAILED                               [100%]

============================= 4 passed, 5 failed in 1.23s ==============================
"""


class TestChangedSymbols:
    def test_detects_modified_functions_and_secret(self):
        changed = changed_symbols(ORIGINAL, PATCHED)
        for name in ("fetch_url", "hash_content", "save_results", "export_json", "run_diagnostics", "API_TOKEN"):
            assert name in changed, f"{name} should be flagged as changed"

    def test_untouched_symbols_not_changed(self):
        changed = changed_symbols(ORIGINAL, PATCHED)
        assert "extract_title" not in changed
        assert "extract_links" not in changed

    def test_no_diff_yields_empty(self):
        assert changed_symbols(ORIGINAL, ORIGINAL) == set()


class TestParseTestOutcomes:
    def test_parses_verbose_pytest_output(self):
        outcomes = parse_test_outcomes(VERBOSE_OUTPUT)
        assert outcomes["test_secret_exists"] == "FAILED"
        assert outcomes["test_extract_title"] == "PASSED"
        assert len(outcomes) == 9

    def test_parses_parametrized_names(self):
        output = "demo1_test.py::test_values[1] PASSED\ndemo1_test.py::test_values[2] FAILED\n"
        outcomes = parse_test_outcomes(output)
        assert outcomes["test_values"] == "FAILED"

    def test_empty_output(self):
        assert parse_test_outcomes("") == {}


class TestClassify:
    def test_pinning_tests_are_expected_not_regressions(self):
        failing = [
            "test_secret_exists",
            "test_fetch_url",
            "test_hash_content",
            "test_save_results",
            "test_run_diagnostics",
        ]
        result = classify(ORIGINAL, PATCHED, TESTS, failing)
        assert set(result["expected"]) == set(failing)
        assert result["regressions"] == []

    def test_failure_on_unchanged_symbol_is_regression(self):
        result = classify(ORIGINAL, PATCHED, TESTS, ["test_extract_links"])
        assert result["regressions"] == ["test_extract_links"]
        assert result["expected"] == []

    def test_no_diff_means_everything_is_regression(self):
        result = classify(ORIGINAL, ORIGINAL, TESTS, ["test_secret_exists"])
        assert result["regressions"] == ["test_secret_exists"]

    def test_unknown_test_name_is_regression(self):
        result = classify(ORIGINAL, PATCHED, TESTS, ["test_does_not_exist"])
        assert result["regressions"] == ["test_does_not_exist"]

    def test_parametrized_failure_maps_to_function(self):
        result = classify(ORIGINAL, PATCHED, TESTS, ["test_save_results[case1]"])
        assert result["expected"] == ["test_save_results[case1]"]

    def test_returns_empty_lists_without_failures(self):
        result = classify(ORIGINAL, PATCHED, TESTS, [])
        assert result["expected"] == []
        assert result["regressions"] == []

    def test_runtime_exception_on_changed_symbol_is_regression(self):
        """A failing test that RAISES (not asserts) on patched code is a
        regression, even though it references a changed symbol."""
        exc_tests = (
            "from tests.demo import fetch_url, hash_content\n\n"
            "def test_fetch_url():\n"
            "    fetch_url('https://example.com')\n\n"
            "def test_hash_content():\n"
            "    assert hash_content('hello') == '5d41402abc4b2a76b9719d911017c592'\n"
        )
        exc_output = (
            "demo_test.py::test_hash_content FAILED                 [ 50%]\n"
            "demo_test.py::test_fetch_url FAILED                    [100%]\n\n"
            "____ test_hash_content ____\n\n"
            "    def test_hash_content():\n"
            ">       assert hash_content('hello') == '5d41402abc4b2a76b9719d911017c592'\n"
            "E       AssertionError: assert '2cf24dba...' == '5d41402a...'\n\n"
            "____ test_fetch_url ____\n\n"
            "    def test_fetch_url():\n"
            ">       fetch_url('https://example.com')\n"
            "E       TypeError: 'NoneType' object is not callable\n\n"
            "============================= short test summary info ==============================\n"
            "FAILED demo_test.py::test_hash_content\n"
            "FAILED demo_test.py::test_fetch_url\n"
            "========================= 0 passed, 2 failed in 0.5s ==============================\n"
        )
        failing = ["test_hash_content", "test_fetch_url"]
        result = classify(ORIGINAL, PATCHED, exc_tests, failing, exc_output)
        assert result["expected"] == ["test_hash_content"]
        assert result["regressions"] == ["test_fetch_url"]

    def test_assertion_failure_is_expected_even_with_traceback(self):
        """AssertionError in the traceback keeps a pinning test "expected"."""
        result = classify(
            ORIGINAL,
            PATCHED,
            TESTS,
            ["test_secret_exists"],
            "____ test_secret_exists ____\n"
            ">       assert API_TOKEN == 'tok_live_a1b2c3d4e5f6g7h8'\n"
            "E       AssertionError: assert 'tok_live_a1b2c3d4e5f6g7h8' is None\n",
        )
        assert result["expected"] == ["test_secret_exists"]
        assert result["regressions"] == []

    def test_fallback_heuristic_when_no_traceback(self):
        """Without traceback info the reference-based heuristic still applies."""
        result = classify(ORIGINAL, PATCHED, TESTS, ["test_secret_exists"])
        assert result["expected"] == ["test_secret_exists"]


class TestAnalyzeTestResults:
    def test_full_run_separates_expected_from_regressions(self):
        analysis = analyze_test_results(ORIGINAL, PATCHED, TESTS, VERBOSE_OUTPUT)
        assert analysis["expected"] == 5
        assert analysis["regressions"] == 0
        assert set(analysis["expected_failures"]) == {
            "test_secret_exists",
            "test_fetch_url",
            "test_hash_content",
            "test_save_results",
            "test_run_diagnostics",
        }
        assert set(analysis["passing_tests"]) == {
            "test_extract_title",
            "test_extract_title_no_match",
            "test_extract_links",
            "test_export_json",
        }

    def test_analyze_flags_runtime_exception_as_regression(self):
        exc_tests = (
            "from tests.demo import fetch_url, hash_content\n\n"
            "def test_fetch_url():\n"
            "    fetch_url('https://example.com')\n\n"
            "def test_hash_content():\n"
            "    assert hash_content('hello') == '5d41402abc4b2a76b9719d911017c592'\n"
        )
        exc_output = (
            "demo_test.py::test_hash_content FAILED                 [ 50%]\n"
            "demo_test.py::test_fetch_url FAILED                    [100%]\n\n"
            "____ test_hash_content ____\n\n"
            "    def test_hash_content():\n"
            ">       assert hash_content('hello') == '5d41402abc4b2a76b9719d911017c592'\n"
            "E       AssertionError: assert '2cf24dba...' == '5d41402a...'\n\n"
            "____ test_fetch_url ____\n\n"
            "    def test_fetch_url():\n"
            ">       fetch_url('https://example.com')\n"
            "E       TypeError: 'NoneType' object is not callable\n\n"
            "============================= short test summary info ==============================\n"
            "FAILED demo_test.py::test_hash_content\n"
            "FAILED demo_test.py::test_fetch_url\n"
            "========================= 0 passed, 2 failed in 0.5s ==============================\n"
        )
        analysis = analyze_test_results(ORIGINAL, PATCHED, exc_tests, exc_output)
        assert analysis["expected"] == 1
        assert analysis["regressions"] == 1
        assert analysis["expected_failures"] == ["test_hash_content"]
        assert analysis["regression_failures"] == ["test_fetch_url"]
