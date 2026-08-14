"""Tests for the LLM-readable regression-test explanation (Phase F).

The reporter renders a technical regression-test block on every finding of a
file. When Gemini is available, ``LLMTriage.explain_regression_tests`` produces
one readable paragraph that replaces that block in each finding card, and the
technical detail is kept collapsed once per file in the Patch & Validation
section. Everything fails open to the deterministic block.
"""

from unittest.mock import MagicMock, patch

import pytest

from core.config import config
from core.triage.llm_triage import LLMTriage
from services.github import reporter

# Captured before the conftest autouse fixture patches the method to None, so
# unit tests can restore the real implementation where needed.
_REAL_EXPLAIN = LLMTriage.explain_regression_tests

_MEANINGFUL_TEST_RESULTS = {
    "success": True,
    "mode": "docker",
    "output": (
        "demo1_test.py::test_secret_exists FAILED\n"
        "demo1_test.py::test_fetch_url FAILED\n"
        "demo1_test.py::test_hash_content FAILED\n"
        "demo1_test.py::test_save_results FAILED\n"
        "demo1_test.py::test_run_diagnostics FAILED\n"
        "demo1_test.py::test_extract_title PASSED\n"
        "demo1_test.py::test_extract_links PASSED\n"
        "demo1_test.py::test_export_json PASSED\n"
        "demo1_test.py::test_save_preview PASSED\n"
        "4 passed, 5 failed in 1.23s\n"
    ),
    "expected_failures": [
        "test_secret_exists",
        "test_fetch_url",
        "test_hash_content",
        "test_save_results",
        "test_run_diagnostics",
    ],
    "regression_failures": [],
    "mocked_env_vars": ["SECRET_API_KEY", "DATABASE_URL"],
    "rebind": {"rebound": True, "rebound_map": {"tests.demo": "demo"}},
}


def _make_client(response=None, enabled=True):
    client = MagicMock()
    client.enabled = enabled
    client.cached_generate.return_value = response
    return client


def _make_triage(client):
    with patch("core.triage.llm_triage.GeminiClient", return_value=client):
        triage = LLMTriage()
    return triage


def _finding(diff=None, **test_override):
    test_results = dict(_MEANINGFUL_TEST_RESULTS)
    test_results.update(test_override)
    return {
        "vulnerability": {
            "type": "COMMAND_INJECTION",
            "file": "src/server.py",
            "line": 10,
            "severity": "HIGH",
            "is_new": True,
        },
        "rule_id": "CMD001",
        "risk": 8.5,
        "quality_score": 0.8,
        "candidate_id": "baseline_ast",
        "validation": {
            "success": True,
            "score": 1.0,
            "details": {
                "syntax": {"success": True},
                "sandbox": {"success": True},
                "rescan": {"success": True, "remaining_vulnerabilities": []},
                "policy": {"success": True},
            },
            "test_results": test_results,
        },
        "diff": diff
        or (
            "--- a/src/server.py\n+++ b/src/server.py\n"
            "@@ -1 +1 @@\n-import os\n+import shlex\n"
        ),
    }


@pytest.fixture(autouse=True)
def _clear_regression_cache():
    reporter._regression_explanation_cache.clear()
    yield
    reporter._regression_explanation_cache.clear()


# ---------------------------------------------------------------------------
# LLMTriage.explain_regression_tests unit tests
# ---------------------------------------------------------------------------


def test_explain_disabled_returns_none(monkeypatch):
    monkeypatch.setattr(LLMTriage, "explain_regression_tests", _REAL_EXPLAIN)
    client = _make_client(response="All 11 tests passed, no regressions.")
    triage = _make_triage(client)
    with patch.object(config.app.regression_explain, "enabled", False):
        assert triage.explain_regression_tests(_MEANINGFUL_TEST_RESULTS) is None
    client.cached_generate.assert_not_called()


def test_explain_none_when_client_disabled(monkeypatch):
    monkeypatch.setattr(LLMTriage, "explain_regression_tests", _REAL_EXPLAIN)
    client = _make_client(response="text", enabled=False)
    triage = _make_triage(client)
    assert triage.explain_regression_tests(_MEANINGFUL_TEST_RESULTS) is None
    client.cached_generate.assert_not_called()


def test_explain_none_without_meaningful_data(monkeypatch):
    monkeypatch.setattr(LLMTriage, "explain_regression_tests", _REAL_EXPLAIN)
    client = _make_client(response="text")
    triage = _make_triage(client)
    assert triage.explain_regression_tests({}) is None
    assert triage.explain_regression_tests({"success": True, "mode": "docker"}) is None
    client.cached_generate.assert_not_called()


def test_explain_returns_trimmed_client_text(monkeypatch):
    monkeypatch.setattr(LLMTriage, "explain_regression_tests", _REAL_EXPLAIN)
    client = _make_client(response="  \nAll 11 tests passed.\n  ")
    triage = _make_triage(client)
    result = triage.explain_regression_tests(_MEANINGFUL_TEST_RESULTS)
    assert result == "All 11 tests passed."
    client.cached_generate.assert_called_once()
    prompt = client.cached_generate.call_args[0][0]
    assert "Expected failures (pin removed vulnerabilities)" in prompt
    assert "test_secret_exists" in prompt
    assert "SECRET_API_KEY" in prompt
    assert "tests.demo -> demo" in prompt


def test_explain_clips_test_names_to_max(monkeypatch):
    monkeypatch.setattr(LLMTriage, "explain_regression_tests", _REAL_EXPLAIN)
    client = _make_client(response="ok")
    triage = _make_triage(client)
    results = dict(_MEANINGFUL_TEST_RESULTS)
    results["expected_failures"] = [f"test_{i}" for i in range(10)]
    with patch.object(config.app.regression_explain, "max_test_names_in_prompt", 3):
        triage.explain_regression_tests(results)
    prompt = client.cached_generate.call_args[0][0]
    assert "test_0, test_1, test_2, ..." in prompt


# ---------------------------------------------------------------------------
# Reporter integration tests
# ---------------------------------------------------------------------------


def test_format_report_replaces_block_when_explanation_present(monkeypatch):
    findings = [_finding()]
    monkeypatch.setattr(
        reporter, "_regression_explanation", lambda tr: "The 5 expected failures pin the removed vulnerabilities."
    )
    report = reporter.format_report(findings, scan_number=1)
    assert "**Regression tests**" in report
    assert "The 5 expected failures pin the removed vulnerabilities." in report
    assert "🧪 Regression test details" in report
    assert report.count("4 passed, 5 expected, 0 skipped") == 1
    assert "pin the removed vulnerabilities" in report
    assert "**Patch evaluation**" in report
    assert "Patch quality" in report


def test_format_report_dedupes_llm_call(monkeypatch):
    mock_explain = MagicMock(return_value="Readable explanation.")
    monkeypatch.setattr(LLMTriage, "explain_regression_tests", mock_explain)
    tr = dict(_MEANINGFUL_TEST_RESULTS)
    reporter._regression_explanation(tr)
    reporter._regression_explanation(tr)
    assert mock_explain.call_count == 1

    mock_explain.reset_mock()
    findings = [_finding(), _finding()]
    report = reporter.format_report(findings, scan_number=1)
    assert report.count("**Regression tests**") == 2
    assert mock_explain.call_count <= 1


def test_format_report_falls_back_when_no_explanation():
    findings = [_finding()]
    report = reporter.format_report(findings, scan_number=1)
    assert "**Regression tests**" not in report
    assert "✅ No regressions" in report
    assert "pin the removed vulnerabilities" in report
    assert "🧪 Regression test details" not in report
    assert "**Patch evaluation**" in report