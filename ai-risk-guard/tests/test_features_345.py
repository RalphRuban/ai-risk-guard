"""
tests/test_features_345.py

Unit tests for Features 3 (Incremental PR), 4 (Test Synthesis), 5 (Quality Scoring).
Run with: pytest tests/test_features_345.py -v
"""

import os
import sys
import tempfile
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# =========================================================
# HELPERS
# =========================================================

def write_temp_file(content, suffix=".py"):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode="w", encoding="utf-8")
    tmp.write(content)
    tmp.close()
    return tmp.name


# =========================================================
# FIXTURES
# =========================================================

# No fixture needed - tests clean up their own temp files


# =========================================================
# FEATURE 3: DIFF ENGINE TESTS
# =========================================================

class TestDiffEngineFunctions:
    """Test function-level diff parsing for incremental scanning."""

    def setup_method(self):
        from core.scanner.diff_engine import DiffAwareScanner
        self.diff = DiffAwareScanner()

    def test_get_function_line_ranges_simple(self):
        code = "def foo():\n    pass\n\ndef bar():\n    x = 1\n"
        ranges = self.diff.get_function_line_ranges(code)
        assert "foo" in ranges
        assert "bar" in ranges
        assert ranges["foo"][0] == 1
        assert ranges["bar"][0] == 4

    def test_get_function_line_ranges_async(self):
        code = "async def fetch():\n    return 1\n"
        ranges = self.diff.get_function_line_ranges(code)
        assert "fetch" in ranges
        assert ranges["fetch"][0] == 1

    def test_get_function_line_ranges_syntax_error(self):
        code = "def broken(\n"
        ranges = self.diff.get_function_line_ranges(code)
        assert ranges == {}

    def test_get_function_line_ranges_empty(self):
        assert self.diff.get_function_line_ranges("") == {}
        assert self.diff.get_function_line_ranges("x = 1") == {}

    def test_get_modified_functions_returns_correct_names(self):
        code = "def foo():\n    x = 1\n\ndef bar():\n    y = 2\n\ndef baz():\n    z = 3\n"
        diff_map = {"file.py": {2, 5}}
        modified = self.diff.get_modified_functions("file.py", code, diff_map)
        assert "foo" in modified
        assert "bar" in modified
        assert "baz" not in modified

    def test_get_modified_functions_no_match(self):
        code = "def foo():\n    x = 1\n"
        diff_map = {"other.py": {1}}
        modified = self.diff.get_modified_functions("file.py", code, diff_map)
        assert modified == []

    def test_get_modified_functions_empty_diff(self):
        code = "def foo():\n    x = 1\n"
        modified = self.diff.get_modified_functions("file.py", code, {})
        assert modified == []

    def test_get_modified_functions_normalized_paths(self):
        code = "def foo():\n    x = 1\n"
        diff_map = {"file.py": {1}}
        modified = self.diff.get_modified_functions("file.py", code, diff_map)
        assert "foo" in modified
        # Test with backslash path (Windows)
        modified2 = self.diff.get_modified_functions("C:\\project\\file.py", code, diff_map)
        assert "foo" in modified2

    def test_parse_diff_with_headers(self):
        diff_text = (
            "diff --git a/file.py b/file.py\n"
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -1,3 +1,4 @@\n"
            " def existing():\n"
            "+    x = 1\n"
        )
        diff_map = self.diff.parse_diff(diff_text)
        assert diff_map == {"file.py": {2}}

    def test_parse_diff_headerless_hunk_uses_default_file(self):
        """GitHub's PR files API patch omits diff --git / +++ headers; hunks
        must be attributed to the file being scanned via default_file."""
        diff_text = (
            "@@ -0,0 +1,3 @@\n"
            "+#!/usr/bin/env python3\n"
            "+def foo():\n"
            "+    return 1\n"
        )
        diff_map = self.diff.parse_diff(diff_text, default_file="demo1.py")
        assert diff_map == {"demo1.py": {1, 2, 3}}

    def test_parse_diff_headerless_without_default_file(self):
        diff_text = "@@ -0,0 +1,2 @@\n+line1\n+line2\n"
        diff_map = self.diff.parse_diff(diff_text)
        assert diff_map == {}

    def test_parse_diff_empty(self):
        assert self.diff.parse_diff("") == {}
        assert self.diff.parse_diff(None) == {}

    def test_should_scan_line_after_headerless_parse(self):
        diff_map = self.diff.parse_diff(
            "@@ -0,0 +1,2 @@\n+line1\n+line2\n", default_file="demo1.py"
        )
        assert self.diff.should_scan_line("C:\\tmp\\demo1.py", 1, diff_map) is True
        assert self.diff.should_scan_line("C:\\tmp\\demo1.py", 2, diff_map) is True
        assert self.diff.should_scan_line("C:\\tmp\\demo1.py", 5, diff_map) is False


# =========================================================
# FEATURE 3: VULNERABILITY SCANNER SCOPE TESTS
# =========================================================

class TestScannerScopeFilter:
    """Test scope_filter in VulnerabilityScanner."""

    def setup_method(self):
        from core.scanner.vulnerability_scanner import VulnerabilityScanner
        self.scanner = VulnerabilityScanner()

    def test_scope_filter_restricts_scanning(self):
        content = (
            "import os\n"
            "def safe_func():\n"
            "    pass\n"
            "def unsafe_func():\n"
            "    os.system('ls')\n"
        )
        path = write_temp_file(content)
        # Only scan safe_func — should not find os.system
        findings = self.scanner.scan_file(path, scope_filter={"safe_func"})
        os.unlink(path)
        assert all(f["type"] != "COMMAND_INJECTION" for f in findings)

    def test_scope_filter_includes_modified(self):
        content = (
            "import os\n"
            "def safe_func():\n"
            "    pass\n"
            "def unsafe_func():\n"
            "    os.system('ls')\n"
        )
        path = write_temp_file(content)
        findings = self.scanner.scan_file(path, scope_filter={"unsafe_func"})
        os.unlink(path)
        assert any(f["type"] == "COMMAND_INJECTION" for f in findings)

    def test_scope_filter_none_scans_all(self):
        content = "import os\nos.system('ls')\n"
        path = write_temp_file(content)
        findings = self.scanner.scan_file(path, scope_filter=None)
        os.unlink(path)
        assert any(f["type"] == "COMMAND_INJECTION" for f in findings)

    def test_scope_filter_empty_scans_none(self):
        content = (
            "import os\n"
            "def safe_func():\n"
            "    os.system('ls')\n"
        )
        path = write_temp_file(content)
        findings = self.scanner.scan_file(path, scope_filter=set())
        os.unlink(path)
        assert not any(f["type"] == "COMMAND_INJECTION" for f in findings)


# =========================================================
# FEATURE 3: SCAN CACHE TESTS
# =========================================================

class TestScanCache:
    """Test function-level caching in ScanCache."""

    def setup_method(self):
        from core.cache.scan_cache import ScanCache
        self.cache = ScanCache()
        self.file_path = "test_cache.py"
        self.commit_hash = "abc123"

    def test_set_and_get_full_file(self):
        data = [{"type": "COMMAND_INJECTION", "line": 2}]
        self.cache.set(self.file_path, self.commit_hash, data)
        result = self.cache.get(self.file_path, self.commit_hash)
        assert result == data

    def test_get_miss_returns_none(self):
        result = self.cache.get("nonexistent.py", "deadbeef")
        assert result is None

    def test_set_and_get_function(self):
        data = [{"type": "HARDCODED_SECRET", "line": 5}]
        self.cache.set_function(self.file_path, "my_func", self.commit_hash, data)
        result = self.cache.get_function(self.file_path, "my_func", self.commit_hash)
        assert result == data

    def test_get_functions_merges_results(self):
        func1 = [{"type": "A", "line": 1}]
        func2 = [{"type": "B", "line": 2}]
        self.cache.set_function(self.file_path, "func1", self.commit_hash, func1)
        self.cache.set_function(self.file_path, "func2", self.commit_hash, func2)
        merged = self.cache.get_functions(self.file_path, ["func1", "func2"], self.commit_hash)
        assert len(merged) == 2

    def test_get_functions_partial_miss(self):
        self.cache.set_function(self.file_path, "func1", self.commit_hash, [{"type": "A"}])
        merged = self.cache.get_functions(self.file_path, ["func1", "func_missing"], self.commit_hash)
        assert len(merged) == 1

    def test_invalidate_clears_file(self):
        self.cache.set(self.file_path, self.commit_hash, [{"type": "A"}])
        self.cache.invalidate(self.file_path)
        assert self.cache.get(self.file_path, self.commit_hash) is None



# =========================================================
# FEATURE 5: PATCH SCORER TESTS
# =========================================================

class TestPatchScorer:
    """Test multi-factor patch quality scoring."""

    def setup_method(self):
        from core.quality.patch_scorer import PatchScorer
        self.scorer = PatchScorer()

    def test_perfect_score(self):
        candidate = {
            "validation_details": {
                "syntax": {"success": True},
                "rescan": {"success": True},
            },
            "test_results": {"success": True, "mode": "docker"},
            "validation_score": 1.0,
            "formatting_diff": 0,
        }
        score = self.scorer.score(candidate, {"metrics": {"complexity": 1}})
        assert score == 1.0

    def test_zero_score(self):
        candidate = {
            "validation_details": {
                "syntax": {"success": False},
                "rescan": {"success": False},
            },
            "test_results": {"success": False},
            "validation_score": 0.0,
            "formatting_diff": 100,
        }
        score = self.scorer.score(candidate, {"metrics": {"complexity": 10}})
        assert score == 0.0

    def test_score_clamped(self):
        candidate = {
            "validation_details": {
                "syntax": {"success": True},
                "rescan": {"success": True},
            },
            "test_results": {"success": True},
            "validation_score": 1.0,
            "formatting_diff": 0,
        }
        score = self.scorer.score(candidate, {"metrics": {"complexity": 1}})
        # Should be 1.0, not >1.0
        assert score <= 1.0
        assert score >= 0.0

    def test_get_breakdown_returns_all_factors(self):
        candidate = {
            "validation_details": {
                "syntax": {"success": True},
                "rescan": {"success": True},
            },
            "test_results": {"success": True},
            "validation_score": 0.8,
            "formatting_diff": 0,
        }
        breakdown = self.scorer.get_breakdown(candidate, {"metrics": {"complexity": 1}})
        expected_keys = {"syntax_validity", "security_validation", "tests_passed",
                         "complexity", "formatting_preserved", "confidence", "total"}
        assert expected_keys.issubset(breakdown.keys())
        assert breakdown["total"] > 0

    def test_score_edge_cases(self):
        # Test with missing fields
        candidate = {}
        score = self.scorer.score(candidate, {})
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


# =========================================================
# QUALITY CONFIG TESTS
# =========================================================

class TestQualityConfig:
    def test_default_weights_loaded(self):
        from core.config.quality_config import QualityConfig
        cfg = QualityConfig()
        assert "syntax_validity" in cfg.weights
        assert "security_validation" in cfg.weights
        assert "tests_passed" in cfg.weights
        assert sum(abs(v) for v in cfg.weights.values()) > 0


# =========================================================
# INPUT VALIDATION TESTS
# =========================================================

class TestInputValidation:
    def test_validate_file_path_normal(self):
        from core.utils.validation import validate_file_path
        assert validate_file_path("src/main.py") == "src\\main.py"

    def test_validate_file_path_null_byte(self):
        from core.utils.validation import InputValidationError, validate_file_path
        with pytest.raises(InputValidationError):
            validate_file_path("src\0main.py")

    def test_validate_file_path_traversal(self):
        from core.utils.validation import InputValidationError, validate_file_path
        with pytest.raises(InputValidationError):
            validate_file_path("../etc/passwd")

    def test_validate_file_path_empty(self):
        from core.utils.validation import InputValidationError, validate_file_path
        with pytest.raises(InputValidationError):
            validate_file_path("")

    def test_validate_diff_data_none(self):
        from core.utils.validation import validate_diff_data
        assert validate_diff_data(None) is None

    def test_validate_diff_data_invalid_type(self):
        from core.utils.validation import InputValidationError, validate_diff_data
        with pytest.raises(InputValidationError):
            validate_diff_data(123)

    def test_validate_code_input_empty(self):
        from core.utils.validation import InputValidationError, validate_code_input
        with pytest.raises(InputValidationError):
            validate_code_input("")

    def test_safe_filename_sanitization(self):
        from core.utils.validation import safe_filename
        assert safe_filename("/etc/passwd") == "passwd"
        assert safe_filename("../../../etc/shadow") == "shadow"
        assert ".." not in safe_filename("../foo/bar")


# =========================================================
# EXCEPTION TESTS
# =========================================================

class TestCustomExceptions:
    def test_exception_hierarchy(self):
        from core.exceptions import (
            AIRiskGuardError,
            CacheError,
            InputValidationError,
            PatchError,
            ResourceCleanupError,
            RiskAnalysisError,
            SandboxError,
            ScanError,
            ValidationError,
        )
        assert issubclass(ScanError, AIRiskGuardError)
        assert issubclass(PatchError, AIRiskGuardError)
        assert issubclass(ValidationError, AIRiskGuardError)
        assert issubclass(SandboxError, AIRiskGuardError)
        assert issubclass(RiskAnalysisError, AIRiskGuardError)
        assert issubclass(CacheError, AIRiskGuardError)
        assert issubclass(InputValidationError, AIRiskGuardError)
        assert issubclass(ResourceCleanupError, AIRiskGuardError)

    def test_exceptions_carry_message(self):
        from core.exceptions import InputValidationError, ScanError
        exc1 = ScanError("test scan error")
        assert str(exc1) == "test scan error"
        exc2 = InputValidationError("invalid input")
        assert str(exc2) == "invalid input"


# =========================================================
# TEMPDIR TESTS
# =========================================================

class TestTempDir:
    def test_tempdir_creates_and_cleans_up(self):
        from core.utils.tempdir import TempDir
        path = None
        with TempDir(prefix="test_") as tmpdir:
            path = tmpdir
            assert os.path.isdir(tmpdir)
        # Should be cleaned up after exit
        assert not os.path.exists(path)

    def test_tempdir_cleans_up_on_exception(self):
        from core.utils.tempdir import TempDir
        path = None
        try:
            with TempDir(prefix="test_") as tmpdir:
                path = tmpdir
                assert os.path.isdir(tmpdir)
                raise ValueError("test error")
        except ValueError:
            pass
        assert not os.path.exists(path)


# =========================================================
# CONFIDENCE TESTS (UPDATED WITH NEW PARAMS)
# =========================================================

class TestConfidenceWithQualityAndTests:
    def test_confidence_boost_from_tests(self):
        from core.confidence.confidence import calculate_confidence
        # Baseline for COMMAND_INJECTION
        base = calculate_confidence(
            vulnerability={"type": "COMMAND_INJECTION", "severity": "HIGH"},
            patch='import subprocess\nsubprocess.run(["ls"], shell=False)',
            validation={"success": True},
            test_results=None,
            quality_score=None,
        )
        boosted = calculate_confidence(
            vulnerability={"type": "COMMAND_INJECTION", "severity": "HIGH"},
            patch='import subprocess\nsubprocess.run(["ls"], shell=False)',
            validation={"success": True},
            test_results={"success": True},
            quality_score=0.8,
        )
        assert boosted > base, "Confidence should increase with tests + quality"

    def test_confidence_no_tests_no_quality(self):
        from core.confidence.confidence import calculate_confidence
        score = calculate_confidence(
            vulnerability={"type": "UNKNOWN_TYPE", "severity": "LOW"},
            patch="x = 1",
            validation={"success": False},
        )
        assert 0.2 <= score <= 0.95

    def test_confidence_clamped_bounds(self):
        from core.confidence.confidence import calculate_confidence
        score = calculate_confidence(
            vulnerability={"type": "COMMAND_INJECTION", "severity": "HIGH"},
            patch="x = 1",
            validation={"success": True},
            test_results={"success": True},
            quality_score=1.0,
        )
        assert score <= 0.95
        score2 = calculate_confidence(
            vulnerability={"type": "COMMAND_INJECTION", "severity": "LOW"},
            patch="x = 1",
            validation={"success": False},
            test_results={"success": False},
            quality_score=0.0,
        )
        assert score2 >= 0.2


# =========================================================
# RISK ENGINE UPDATED TESTS
# =========================================================

class TestRiskEngineQualityFactor:
    def test_quality_score_reduces_risk(self):
        from core.risk.risk_engine import calculate_risk
        vuln = {"type": "COMMAND_INJECTION", "severity": "HIGH", "file": "test.py"}
        pr = {}
        high_quality = calculate_risk(vuln, pr, confidence=0.9, quality_score=0.9)
        low_quality = calculate_risk(vuln, pr, confidence=0.9, quality_score=0.1)
        assert high_quality <= low_quality, "Higher quality should yield lower or equal risk"

    def test_risk_calculation_handles_missing_quality(self):
        from core.risk.risk_engine import calculate_risk
        vuln = {"type": "COMMAND_INJECTION", "severity": "HIGH", "file": "test.py"}
        score = calculate_risk(vuln, {}, confidence=0.8, quality_score=None)
        assert 0 < score <= 10


# =========================================================
# VALIDATOR AGENT TEST (MOCKED SANDBOX)
# =========================================================

class TestValidatorAgent:
    def test_validation_with_mocked_sandbox(self):
        from core.agents.validator_agent import ValidatorAgent
        agent = ValidatorAgent()
        agent.sandbox.run = Mock(return_value={"success": True, "output": "ok"})
        agent.sandbox.run_tests = Mock(return_value={"success": True, "output": "tests ok"})

        context = {
            "patch_candidates": [
                {
                    "id": "cand_1",
                    "source": "ast",
                    "code": 'import subprocess\nsubprocess.run(["ls"], shell=False)',
                }
            ],
            "test_file_path": None,
        }
        result = agent.execute(context)
        assert result is not None
        candidate = result["patch_candidates"][0]
        assert "validation_score" in candidate
        assert candidate["validation_score"] >= 0

    def test_validation_with_missing_code(self):
        from core.agents.validator_agent import ValidatorAgent
        agent = ValidatorAgent()
        context = {
            "patch_candidates": [
                {"id": "cand_1", "source": "ast", "code": None}
            ]
        }
        result = agent.execute(context)
        assert result is not None
        # The candidate should have been skipped
        candidate = result["patch_candidates"][0]
        assert "validation_score" not in candidate  # Should have been skipped

    def test_ssrf_check_skipped_when_no_validator(self):
        from core.agents.validator_agent import _check_ssrf_patch
        code = "import requests\nrequests.get('https://example.com')\n"
        result = _check_ssrf_patch(code)
        assert result["skipped"] is True

    def test_ssrf_check_uses_canonical_validator(self):
        from core.agents.validator_agent import _check_ssrf_patch
        code = (
            "def validate_url_ssrf(url): return url  # no-op in user code\n"
            "requests.get(validate_url_ssrf('https://example.com'))\n"
        )
        result = _check_ssrf_patch(code)
        # The canonical validator from fixers.py is tested, not user's no-op
        assert result.get("success") is True
        assert result.get("total", 0) > 0
        assert result.get("failed", -1) == 0

    def test_ssrf_check_all_test_cases_cover_both_paths(self):
        from core.agents.validator_agent import _SSRF_TEST_URLS
        allowed = [u for u, b in _SSRF_TEST_URLS if not b]
        blocked = [u for u, b in _SSRF_TEST_URLS if b]
        assert len(allowed) >= 3, "Should have multiple allowed URLs"
        assert len(blocked) >= 10, "Should have multiple blocked URLs"

    def test_validation_pipeline_stores_ssrf_result_on_mocked_sandbox(self):
        from core.agents.validator_agent import ValidatorAgent
        agent = ValidatorAgent()
        agent.sandbox.run = Mock(return_value={"success": True, "output": "ok"})
        agent.sandbox.run_tests = Mock(return_value={"success": True, "output": "ok"})
        code = (
            "import requests\n"
            "import ipaddress\n"
            "def validate_url_ssrf(url): return url\n"
            "requests.get(validate_url_ssrf('https://example.com'))\n"
        )
        context = {
            "patch_candidates": [
                {"id": "ssrf_cand", "source": "ast", "code": code}
            ],
        }
        result = agent.execute(context)
        candidate = result["patch_candidates"][0]
        details = candidate.get("validation_details", {})
        assert "ssrf_validator" in details
        assert details["ssrf_validator"]["success"] is True

    def test_validation_preserves_skipped_tests(self):
        """A skipped test result from the sandbox should not be downgraded to FAIL."""
        from core.agents.validator_agent import ValidatorAgent

        skip_result = {
            "success": False,
            "skipped": True,
            "mode": "docker",
            "error": "test imports from tests.demo which does not match the patched module",
        }
        with patch("core.agents.validator_agent.Sandbox") as MockSandbox:
            instance = MockSandbox.return_value
            instance.run.return_value = {"success": True, "output": "ok"}
            instance.run_tests.return_value = skip_result

            agent = ValidatorAgent()
            context = {
                "patch_candidates": [
                    {
                        "id": "cand_1",
                        "source": "ast",
                        "code": 'import subprocess\nsubprocess.run(["ls"], shell=False)',
                    }
                ],
                "test_file_path": "demo_test.py",
                "repo_root": ".",
                "file_path": "demo1.py",
            }
            result = agent.execute(context)

        candidate = result["patch_candidates"][0]
        test_results = candidate["test_results"]
        assert test_results["skipped"] is True
        assert "local_fallback" not in test_results
        assert candidate["validation_score"] >= 0.75

    def test_validation_attributes_pinning_test_failures_as_expected(self):
        """Tests that pin the removed vulnerabilities must not count as regressions."""
        import tempfile as _tempfile

        from core.agents.validator_agent import ValidatorAgent

        original = (
            "import hashlib\n"
            "import subprocess\n"
            "API_TOKEN = 'tok_live_a1b2c3d4e5f6g7h8'\n"
            "def fetch_url(url):\n"
            "    return url\n"
            "def hash_content(c):\n"
            "    return hashlib.md5(c.encode()).hexdigest()\n"
            "def run_diagnostics(domain):\n"
            "    return subprocess.run(f'ping {domain}', shell=True).stdout\n"
        )
        patched = (
            "import hashlib\n"
            "import os\n"
            "import subprocess\n"
            "API_TOKEN = os.getenv('API_TOKEN')\n"
            "def fetch_url(url):\n"
            "    return url\n"
            "def hash_content(c):\n"
            "    return hashlib.sha256(c.encode()).hexdigest()\n"
            "def run_diagnostics(domain):\n"
            "    return subprocess.run(['ping', domain], shell=False).stdout\n"
        )
        test_src = (
            "from tests.demo import API_TOKEN, hash_content, run_diagnostics\n"
            "def test_secret_exists():\n"
            "    assert API_TOKEN == 'tok_live_a1b2c3d4e5f6g7h8'\n"
            "def test_hash_content():\n"
            "    assert hash_content('hello') == '5d41402abc4b2a76b9719d911017c592'\n"
            "def test_run_diagnostics():\n"
            "    assert 'PING' in run_diagnostics('example.com')\n"
            "def test_unchanged_logic():\n"
            "    assert True\n"
        )
        run_output = (
            "demo1_test.py::test_secret_exists FAILED\n"
            "demo1_test.py::test_hash_content FAILED\n"
            "demo1_test.py::test_run_diagnostics FAILED\n"
            "demo1_test.py::test_unchanged_logic PASSED\n"
            "1 passed, 3 failed in 0.42s\n"
        )

        test_file = _tempfile.NamedTemporaryFile(
            suffix="_demo_test.py", delete=False, mode="w", encoding="utf-8"
        )
        test_file.write(test_src)
        test_file.close()

        with patch("core.agents.validator_agent.Sandbox") as MockSandbox:
            instance = MockSandbox.return_value
            instance.run.return_value = {"success": True, "output": "ok"}
            instance.run_tests.return_value = {
                "success": False,
                "mode": "docker",
                "output": run_output,
            }

            agent = ValidatorAgent()
            context = {
                "patch_candidates": [
                    {"id": "cand_1", "source": "ast", "code": patched}
                ],
                "test_file_path": test_file.name,
                "repo_root": ".",
                "file_path": "demo1.py",
                "original_code": original,
            }
            result = agent.execute(context)

        os.unlink(test_file.name)

        candidate = result["patch_candidates"][0]
        test_results = candidate["test_results"]
        assert set(test_results["expected_failures"]) == {
            "test_secret_exists",
            "test_hash_content",
            "test_run_diagnostics",
        }
        assert test_results["regression_failures"] == []
        assert test_results["success"] is True
        assert test_results["raw_success"] is False
        assert candidate["validation_score"] >= 0.9

    def test_validation_keeps_regressions_when_unrelated_test_fails(self):
        """A failing test on an unchanged symbol must remain a regression."""
        import tempfile as _tempfile

        from core.agents.validator_agent import ValidatorAgent

        original = (
            "import subprocess\n"
            "def run_diagnostics(domain):\n"
            "    return subprocess.run(f'ping {domain}', shell=True).stdout\n"
        )
        patched = (
            "import subprocess\n"
            "def run_diagnostics(domain):\n"
            "    return subprocess.run(['ping', domain], shell=False).stdout\n"
        )
        test_src = (
            "from tests.demo import run_diagnostics\n"
            "def test_run_diagnostics():\n"
            "    assert 'PING' in run_diagnostics('example.com')\n"
            "def test_unrelated_breaks():\n"
            "    import demo1\n"
            "    assert demo1.run_diagnostics is None\n"
        )
        run_output = (
            "demo1_test.py::test_run_diagnostics FAILED\n"
            "demo1_test.py::test_unrelated_breaks FAILED\n"
            "0 passed, 2 failed in 0.30s\n"
        )

        test_file = _tempfile.NamedTemporaryFile(
            suffix="_demo_test.py", delete=False, mode="w", encoding="utf-8"
        )
        test_file.write(test_src)
        test_file.close()

        with patch("core.agents.validator_agent.Sandbox") as MockSandbox:
            instance = MockSandbox.return_value
            instance.run.return_value = {"success": True, "output": "ok"}
            instance.run_tests.return_value = {
                "success": False,
                "mode": "docker",
                "output": run_output,
            }

            agent = ValidatorAgent()
            context = {
                "patch_candidates": [
                    {"id": "cand_1", "source": "ast", "code": patched}
                ],
                "test_file_path": test_file.name,
                "repo_root": ".",
                "file_path": "demo1.py",
                "original_code": original,
            }
            result = agent.execute(context)

        os.unlink(test_file.name)

        candidate = result["patch_candidates"][0]
        test_results = candidate["test_results"]
        assert test_results["expected_failures"] == ["test_run_diagnostics"]
        assert test_results["regression_failures"] == ["test_unrelated_breaks"]
        assert test_results["success"] is False


    def test_scan_settings_threaded_to_sandbox(self):
        """Per-user scan settings from pr_context reach Sandbox.run/run_tests."""
        import tempfile as _tempfile
        from pathlib import Path as _Path

        from core.agents.validator_agent import ValidatorAgent
        test_file = _Path(_tempfile.gettempdir()) / "airisk_threaded_test.py"
        test_file.write_text("def test_ok():\n    assert True\n")
        try:
            with patch("core.agents.validator_agent.Sandbox") as MockSandbox:
                instance = MockSandbox.return_value
                instance.run.return_value = {"success": True, "output": "ok"}
                instance.run_tests.return_value = {"success": True, "output": "ok", "mode": "docker"}

                agent = ValidatorAgent()
                context = {
                    "patch_candidates": [
                        {
                            "id": "cand_1",
                            "source": "ast",
                            "code": 'import subprocess\nsubprocess.run(["ls"], shell=False)',
                        }
                    ],
                    "test_file_path": str(test_file),
                    "repo_root": ".",
                    "file_path": "demo1.py",
                    "pr_context": {
                        "scan_settings": {
                            "scan_mode": "sandbox_with_local_fallback",
                            "sandbox_network": "bridge",
                        }
                    },
                }
                agent.execute(context)

            run_kwargs = instance.run.call_args.kwargs
            assert run_kwargs.get("scan_mode") == "sandbox_with_local_fallback"
            assert run_kwargs.get("network") == "bridge"
            tests_kwargs = instance.run_tests.call_args.kwargs
            assert tests_kwargs.get("scan_mode") == "sandbox_with_local_fallback"
            assert tests_kwargs.get("network") == "bridge"
        finally:
            try:
                test_file.unlink()
            except OSError:
                pass

    def test_comparison_mode_runs_local_alongside_docker(self):
        """sandbox_and_local_comparison attaches local_fallback even when Docker passes."""
        import tempfile as _tempfile
        from pathlib import Path as _Path

        from core.agents.validator_agent import ValidatorAgent
        test_file = _Path(_tempfile.gettempdir()) / "airisk_compare_test.py"
        test_file.write_text("def test_ok():\n    assert True\n")
        try:
            with patch("core.agents.validator_agent.Sandbox") as MockSandbox:
                instance = MockSandbox.return_value
                instance.run.return_value = {"success": True, "output": "ok"}
                instance.run_tests.return_value = {"success": True, "output": "ok", "mode": "docker"}
                instance._is_docker_available.return_value = True
                instance._run_local_tests.return_value = {"success": True}

                agent = ValidatorAgent()
                context = {
                    "patch_candidates": [
                        {
                            "id": "cand_1",
                            "source": "ast",
                            "code": 'import subprocess\nsubprocess.run(["ls"], shell=False)',
                        }
                    ],
                    "test_file_path": str(test_file),
                    "repo_root": ".",
                    "file_path": "demo1.py",
                    "pr_context": {
                        "scan_settings": {
                            "scan_mode": "sandbox_and_local_comparison",
                            "sandbox_network": "none",
                        }
                    },
                }
                result = agent.execute(context)

            test_results = result["patch_candidates"][0]["test_results"]
            assert test_results["local_fallback"]["success"] is True
            instance._run_local_tests.assert_called_once()
        finally:
            try:
                test_file.unlink()
            except OSError:
                pass


    def test_comparison_mode_reclassifies_expected_failures_locally(self):
        """Local comparison results must get the same expected-failure attribution as Docker."""
        import tempfile as _tempfile
        from pathlib import Path as _Path

        from core.agents.validator_agent import ValidatorAgent

        original = (
            "import hashlib\n"
            "import subprocess\n"
            "API_TOKEN = 'tok_live_a1b2c3d4e5f6g7h8'\n"
            "def hash_content(c):\n"
            "    return hashlib.md5(c.encode()).hexdigest()\n"
        )
        patched = (
            "import hashlib\n"
            "import os\n"
            "API_TOKEN = os.getenv('API_TOKEN')\n"
            "def hash_content(c):\n"
            "    return hashlib.sha256(c.encode()).hexdigest()\n"
        )
        test_file = _Path(_tempfile.gettempdir()) / "airisk_compare_reclassify_test.py"
        test_file.write_text(
            "from tests.demo import API_TOKEN, hash_content\n"
            "def test_secret_exists():\n"
            "    assert API_TOKEN == 'tok_live_a1b2c3d4e5f6g7h8'\n"
            "def test_hash_content():\n"
            "    assert hash_content('hello') == '5d41402abc4b2a76b9719d911017c592'\n"
            "def test_unchanged():\n"
            "    assert True\n"
        )
        local_output = (
            "demo1_test.py::test_secret_exists FAILED\n"
            "demo1_test.py::test_hash_content FAILED\n"
            "demo1_test.py::test_unchanged PASSED\n"
        )
        try:
            with patch("core.agents.validator_agent.Sandbox") as MockSandbox:
                instance = MockSandbox.return_value
                instance.run.return_value = {"success": True, "output": "ok"}
                instance.run_tests.return_value = {
                    "success": False,
                    "mode": "docker",
                    "output": local_output,
                }
                instance._is_docker_available.return_value = True
                instance._run_local_tests.return_value = {
                    "success": False,
                    "mode": "local",
                    "output": local_output,
                }

                agent = ValidatorAgent()
                context = {
                    "patch_candidates": [
                        {"id": "cand_1", "source": "ast", "code": patched}
                    ],
                    "test_file_path": str(test_file),
                    "repo_root": ".",
                    "file_path": "demo1.py",
                    "original_code": original,
                    "pr_context": {
                        "scan_settings": {
                            "scan_mode": "sandbox_and_local_comparison",
                            "sandbox_network": "none",
                        }
                    },
                }
                result = agent.execute(context)

            test_results = result["patch_candidates"][0]["test_results"]
            lf = test_results["local_fallback"]
            assert lf["success"] is True
            assert lf["raw_success"] is False
            assert set(lf["expected_failures"]) == {"test_secret_exists", "test_hash_content"}
            assert lf["regression_failures"] == []
            assert lf["passing_tests"] == ["test_unchanged"]
        finally:
            try:
                test_file.unlink()
            except OSError:
                pass

    def test_comparison_mode_keeps_true_local_regressions_failed(self):
        """A genuine local regression must keep local_fallback success=False."""
        import tempfile as _tempfile
        from pathlib import Path as _Path

        from core.agents.validator_agent import ValidatorAgent

        original = "API_TOKEN = 'tok_live_a1b2c3d4e5f6g7h8'\n"
        patched = "import os\nAPI_TOKEN = os.getenv('API_TOKEN')\n"
        test_file = _Path(_tempfile.gettempdir()) / "airisk_compare_regression_test.py"
        test_file.write_text(
            "from tests.demo import API_TOKEN\n"
            "def test_secret_exists():\n"
            "    assert API_TOKEN == 'tok_live_a1b2c3d4e5f6g7h8'\n"
            "def test_unrelated_broken():\n"
            "    import os\n"
            "    assert os is None\n"
        )
        local_output = (
            "demo1_test.py::test_secret_exists FAILED\n"
            "demo1_test.py::test_unrelated_broken FAILED\n"
        )
        try:
            with patch("core.agents.validator_agent.Sandbox") as MockSandbox:
                instance = MockSandbox.return_value
                instance.run.return_value = {"success": True, "output": "ok"}
                instance.run_tests.return_value = {
                    "success": False,
                    "mode": "docker",
                    "output": local_output,
                }
                instance._is_docker_available.return_value = True
                instance._run_local_tests.return_value = {
                    "success": False,
                    "mode": "local",
                    "output": local_output,
                }

                agent = ValidatorAgent()
                context = {
                    "patch_candidates": [
                        {"id": "cand_1", "source": "ast", "code": patched}
                    ],
                    "test_file_path": str(test_file),
                    "repo_root": ".",
                    "file_path": "demo1.py",
                    "original_code": original,
                    "pr_context": {
                        "scan_settings": {
                            "scan_mode": "sandbox_and_local_comparison",
                            "sandbox_network": "none",
                        }
                    },
                }
                result = agent.execute(context)

            test_results = result["patch_candidates"][0]["test_results"]
            lf = test_results["local_fallback"]
            assert lf["success"] is False
            assert lf["regression_failures"] == ["test_unrelated_broken"]
            assert lf["expected_failures"] == ["test_secret_exists"]
        finally:
            try:
                test_file.unlink()
            except OSError:
                pass

    def test_comparison_mode_attaches_local_fallback_when_docker_unavailable(self):
        """sandbox_and_local_comparison still captures local results when Docker did not run."""
        import tempfile as _tempfile
        from pathlib import Path as _Path

        from core.agents.validator_agent import ValidatorAgent
        test_file = _Path(_tempfile.gettempdir()) / "airisk_compare_localonly_test.py"
        test_file.write_text("def test_ok():\n    assert True\n")
        try:
            with patch("core.agents.validator_agent.Sandbox") as MockSandbox:
                instance = MockSandbox.return_value
                instance.run.return_value = {"success": True, "output": "ok"}
                instance.run_tests.return_value = {
                    "success": True,
                    "output": "ok",
                    "mode": "local",
                    "docker_unavailable": True,
                }
                instance._is_docker_available.return_value = False
                instance._run_local_tests.return_value = {"success": True}

                agent = ValidatorAgent()
                context = {
                    "patch_candidates": [
                        {
                            "id": "cand_1",
                            "source": "ast",
                            "code": 'import subprocess\nsubprocess.run(["ls"], shell=False)',
                        }
                    ],
                    "test_file_path": str(test_file),
                    "repo_root": ".",
                    "file_path": "demo1.py",
                    "pr_context": {
                        "scan_settings": {
                            "scan_mode": "sandbox_and_local_comparison",
                            "sandbox_network": "none",
                        }
                    },
                }
                result = agent.execute(context)

            test_results = result["patch_candidates"][0]["test_results"]
            assert test_results["local_fallback"]["success"] is True
            instance._run_local_tests.assert_called_once()
        finally:
            try:
                test_file.unlink()
            except OSError:
                pass


# =========================================================
# RISK AGENT TEST (MOCKED)
# =========================================================

class TestRiskAgent:
    def test_risk_agent_with_mocked_deps(self):
        from core.agents.risk_agent import RiskAgent
        agent = RiskAgent()
        context = {
            "vulnerabilities": [{"type": "COMMAND_INJECTION", "severity": "HIGH", "file": "test.py"}],
            "patch_candidates": [
                {
                    "id": "cand_1",
                    "source": "ast",
                    "code": 'import subprocess\nsubprocess.run(["ls"], shell=False)',
                    "validation_score": 0.85,
                    "validation_details": {
                        "syntax": {"success": True},
                        "sandbox": {"success": True},
                        "rescan": {"success": True},
                        "policy": {"success": True},
                    },
                    "test_results": {"success": True},
                    "quality_score": 0.8,
                    "quality_breakdown": {},
                }
            ],
            "file_path": __file__,
            "repo_root": os.path.dirname(os.path.dirname(__file__)),
            "pr_context": {},
        }
        result = agent.execute(context)
        assert "results" in result
        assert len(result["results"]) > 0
        assert "quality_score" in result["results"][0]
        assert "quality_breakdown" in result["results"][0]
        assert "test_results" in result["results"][0].get("validation", {})

    def test_risk_agent_no_candidates(self):
        from core.agents.risk_agent import RiskAgent
        agent = RiskAgent()
        context = {
            "vulnerabilities": [],
            "patch_candidates": [],
            "file_path": __file__,
        }
        result = agent.execute(context)
        assert result is context

    def test_risk_agent_suppressed_patch_has_empty_diff(self):
        """A suppressed winner (ranking too low) must never leak a diff."""
        from core.agents.risk_agent import RiskAgent
        agent = RiskAgent()
        context = {
            "vulnerabilities": [{"type": "COMMAND_INJECTION", "severity": "HIGH", "file": "test.py"}],
            "original_code": 'import os\nos.system(cmd)\n',
            "patch_candidates": [
                {
                    "id": "cand_low",
                    "source": "ast",
                    "code": 'import subprocess\nsubprocess.run(["ls"], shell=False)',
                    "validation_score": 0.1,
                    "validation_details": {
                        "syntax": {"success": False},
                        "rescan": {"success": False},
                        "sandbox": {"success": False},
                        "policy": {"success": False},
                    },
                    "test_results": {"success": False},
                    "quality_score": 0.0,
                    "quality_breakdown": {},
                }
            ],
            "file_path": __file__,
            "repo_root": os.path.dirname(os.path.dirname(__file__)),
            "pr_context": {},
        }
        result = agent.execute(context)
        assert "results" in result
        assert result["results"][0]["patch_suppressed"] is True
        assert result["results"][0]["diff"] == ""
        assert "diff" in result["results"][0]

    def test_ranking_not_clamped_to_zero_for_high_risk_file(self):
        """A decent-quality patch on a high-risk file must not rank as 0.00.

        Regression: the old flat penalty (avg_risk / 10, up to 1.0) clamped every
        candidate to 0.00 when the file had high average risk, wiping out the
        quality signal and forcing artificial ties.
        """
        from core.agents.risk_agent import RiskAgent
        agent = RiskAgent()
        low_complexity = write_temp_file("def a():\n    return 1\n")
        context = {
            "vulnerabilities": [
                {"type": "COMMAND_INJECTION", "severity": "CRITICAL", "file": "test.py"},
                {"type": "SQL_INJECTION", "severity": "HIGH", "file": "test.py"},
                {"type": "PATH_TRAVERSAL", "severity": "HIGH", "file": "test.py"},
            ],
            "patch_candidates": [
                {
                    "id": "cand_good",
                    "source": "llm",
                    "code": 'import subprocess\nsubprocess.run(["ls"], shell=False)',
                    "validation_score": 0.85,
                    "validation_details": {
                        "syntax": {"success": True},
                        "sandbox": {"success": True},
                        "rescan": {"success": False},
                        "policy": {"success": False},
                    },
                    "test_results": {"success": False},
                    "quality_score": 0.7,
                    "quality_breakdown": {},
                }
            ],
            "file_path": low_complexity,
            "repo_root": os.path.dirname(os.path.dirname(__file__)),
            "pr_context": {},
        }
        result = agent.execute(context)
        winner = result["results"][0]
        # High-risk file but quality patch: ranking must exceed the clamp floor
        assert winner["quality_score"] > 0.3
        # With avg_risk ~ high, old formula would clamp ranking to 0.00 -> suppressed.
        # New formula keeps the patch viable.
        assert result["results"][0]["patch_suppressed"] is False
        import os as _os
        _os.remove(low_complexity)

    def test_tiebreak_prefers_higher_validation_over_llm_preference(self):
        """When candidates tie on ranking, quality/validation must win over the
        LLM preference.

        Regression: baseline_ast scored 0.6 validation vs LLM variants at 0.45,
        yet the old tie-break picked llm_variant_1 because everything clamped to
        ranking 0.00 and the sort key defaulted to preferring LLM.
        """
        from core.agents.risk_agent import RiskAgent
        agent = RiskAgent()

        def _candidate(cid, source, validation_score):
            return {
                "id": cid,
                "source": source,
                "code": 'import subprocess\nsubprocess.run(["ls"], shell=False)',
                "validation_score": validation_score,
                "validation_details": {
                    "syntax": {"success": True},
                    "sandbox": {"success": True},
                    "rescan": {"success": False},
                    "policy": {"success": False},
                },
                "test_results": {"success": False},
                "quality_score": validation_score,
                "quality_breakdown": {},
            }

        context = {
            "vulnerabilities": [{"type": "COMMAND_INJECTION", "severity": "HIGH", "file": "test.py"}],
            "patch_candidates": [
                _candidate("llm_variant_1", "llm", 0.45),
                _candidate("baseline_ast", "deterministic_ast", 0.6),
            ],
            "file_path": __file__,
            "repo_root": os.path.dirname(os.path.dirname(__file__)),
            "pr_context": {},
        }
        result = agent.execute(context)
        # The higher-validated deterministic candidate must win, not the LLM variant.
        assert result["results"][0]["candidate_id"] == "baseline_ast"
        assert result["results"][0]["candidate_source"] == "deterministic_ast"
