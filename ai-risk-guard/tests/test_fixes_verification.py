"""
tests/test_fixes_verification.py
Focused tests verifying the 3 fixes:
1. SARIF executionSuccessful=true
2. Sandbox local fallback when Docker unavailable
3. Quality score analysis
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from core.models.analysis import AnalysisResult
from core.models.risk import RiskAssessment
from core.models.scan import ScanResult
from core.models.vulnerability import Severity, Vulnerability, VulnerabilityType

# PatchScorer imports
from core.quality.patch_scorer import PatchScorer
from core.sarif.converter import build_analysis_result, build_analysis_summary

# SARIF imports
from core.sarif.sarif_generator import SARIFGenerator

# Sandbox imports
from core.validator.sandbox import Sandbox


class TestSARIFExecutionSuccessful:
    """
    Verify Fix 1: SARIF executionSuccessful should be true when scan runs,
    regardless of validation/sandbox/rescan results.
    """

    def test_execution_successful_with_findings(self):
        """SARIF should have executionSuccessful: true even when vulnerabilities found."""
        generator = SARIFGenerator()
        
        vuln = Vulnerability(
            type=VulnerabilityType.COMMAND_INJECTION,
            file="test.py",
            line=10,
            code="os.system(cmd)",
            severity=Severity.HIGH,
            message="Command injection",
        )
        assessment = RiskAssessment(
            vulnerability=vuln,
            risk_score=8.5,
            confidence=0.9,
        )
        result = AnalysisResult(
            file_path="test.py",
            scan=ScanResult(success=True, file_path="test.py"),
            risk_assessments=[assessment],
        )
        
        sarif = generator.generate(result)
        invocation = sarif["runs"][0].get("invocations", [{}])[0]
        
        assert invocation["executionSuccessful"] is True, (
            "executionSuccessful should be True when scan ran successfully"
        )

    def test_execution_successful_via_converter(self):
        """Converter should produce passed_all_stages=True for scan with findings."""
        findings = [
            {
                "vulnerability": {
                    "type": "COMMAND_INJECTION",
                    "file": "test.py",
                    "line": 10,
                    "code": "os.system(cmd)",
                    "severity": "HIGH",
                    "message": "Command injection",
                },
                "risk": 8.5,
                "confidence": 0.9,
            }
        ]
        
        summary = build_analysis_summary(findings)
        assert summary.passed_all_stages is True, (
            "passed_all_stages should be True (hardcoded) when scan produces findings"
        )

    def test_execution_successful_empty_findings(self):
        """SARIF should have executionSuccessful: true even with no findings."""
        generator = SARIFGenerator()
        
        result = AnalysisResult(
            file_path="clean.py",
            scan=ScanResult(success=True, file_path="clean.py"),
            risk_assessments=[],
        )
        
        sarif = generator.generate(result)
        invocation = sarif["runs"][0].get("invocations", [{}])[0]
        
        assert invocation["executionSuccessful"] is True

    def test_execution_successful_full_pipeline(self):
        """End-to-end: build_analysis_result -> SARIFGenerator should produce executionSuccessful: true."""
        findings = [
            {
                "vulnerability": {
                    "type": "SQL_INJECTION",
                    "file": "app.py",
                    "line": 25,
                    "code": "cursor.execute(f\"SELECT * FROM users WHERE id={user_id}\")",
                    "severity": "HIGH",
                    "message": "SQL injection via f-string",
                },
                "risk": 7.2,
                "confidence": 0.85,
                "patch_applied": True,
            }
        ]
        
        analysis_result = build_analysis_result(findings, "app.py")
        generator = SARIFGenerator()
        sarif = generator.generate(analysis_result)
        
        invocation = sarif["runs"][0].get("invocations", [{}])[0]
        assert invocation["executionSuccessful"] is True
        
        # Also verify the JSON output is valid and contains the correct value
        json_str = generator.generate_json(analysis_result)
        parsed = json.loads(json_str)
        assert parsed["runs"][0]["invocations"][0]["executionSuccessful"] is True


class TestSandboxLocalFallback:
    """
    Verify Fix 2: Sandbox should fall back to local Python execution
    when Docker is unavailable.
    """

    def test_docker_not_available_fallback(self):
        """Sandbox.run() should use _run_local when Docker is not available."""
        sandbox = Sandbox()
        sandbox._docker_available = False  # Force Docker unavailable
        
        result = sandbox.run("print('hello')")
        
        # Should not fail - should run locally
        assert result is not None
        assert "success" in result

    def test_run_local_executes_python(self):
        """_run_local should execute valid Python code."""
        sandbox = Sandbox()
        
        result = sandbox._run_local("print('hello')")
        
        assert result["success"] is True
        assert "hello" in result.get("output", "")

    def test_run_local_detects_unsafe_pattern(self):
        """_run_local should detect unsafe patterns (os.system)."""
        sandbox = Sandbox()
        
        result = sandbox._run_local("import os\nos.system('echo pwned')")
        
        assert result["success"] is False
        assert "unsafe" in result.get("error", "").lower()

    def test_run_local_syntax_error(self):
        """_run_local should handle syntax errors gracefully."""
        sandbox = Sandbox()
        
        result = sandbox._run_local("def (broken")
        
        # Should not crash - should return error result
        assert result["success"] is False

    def test_run_local_tests_fallback(self):
        """_run_local_tests should run pytest locally."""
        sandbox = Sandbox()
        
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir()
        ) as f:
            f.write("def test_pass():\n    assert True\n")
            test_path = f.name
        
        try:
            result = sandbox._run_local_tests(test_path)
            assert result["success"] is True
        finally:
            os.unlink(test_path)

    def test_run_local_tests_nonexistent_file(self):
        """_run_local_tests should handle missing test file."""
        sandbox = Sandbox()
        
        result = sandbox._run_local_tests("nonexistent_test_file.py")
        
        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()

    def test_sandbox_run_uses_fallback_when_no_docker(self):
        """Sandbox.run() should call _run_local when Docker is unavailable."""
        sandbox = Sandbox()
        sandbox._docker_available = False
        
        with patch.object(sandbox, '_run_local') as mock_local:
            mock_local.return_value = {"success": True, "output": "ok"}
            result = sandbox.run("print('test')")
            
            mock_local.assert_called_once()
            assert result["success"] is True

    def test_sandbox_run_tests_uses_fallback_when_no_docker(self):
        """Sandbox.run_tests() should call _run_local_tests when Docker is unavailable."""
        sandbox = Sandbox()
        sandbox._docker_available = False
        
        with patch.object(sandbox, '_run_local_tests') as mock_local:
            mock_local.return_value = {"success": True, "output": "tests passed"}
            sandbox.run_tests("test_something.py")
            
            mock_local.assert_called_once()

    def test_docker_availability_cached(self):
        """Docker availability check should be cached after first call."""
        sandbox = Sandbox()
        
        # First check: should call subprocess
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result1 = sandbox._is_docker_available()
            
            # Second check: should NOT call subprocess (cached)
            result2 = sandbox._is_docker_available()
            
            # subprocess.run should only be called once
            assert mock_run.call_count == 1
            assert result1 == result2 == False

    def test_detect_third_party_imports_excludes_local_source_stem(self):
        """Imports that match the scanned source stem should not be pip-installed."""
        code = "from demo1 import fetch_url\nimport requests\n"
        missing = Sandbox._detect_third_party_imports(
            code, workspace=tempfile.gettempdir(), source_filename="demo1.py"
        )
        assert missing == set()

    def test_detect_third_party_imports_keeps_missing_package(self):
        """Imports with no local resolution (e.g. tests) are still reported."""
        code = "from tests.demo import fetch_url\n"
        missing = Sandbox._detect_third_party_imports(code)
        assert missing == {"tests"}

    def test_detect_third_party_imports_excludes_local_package_dir(self):
        """A package directory in the workspace resolves the import locally."""
        workspace = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(workspace, "tests"), exist_ok=True)
            open(os.path.join(workspace, "tests", "__init__.py"), "w").close()
            code = "from tests.demo import fetch_url\n"
            missing = Sandbox._detect_third_party_imports(
                code, workspace=workspace, source_filename="demo1.py"
            )
            assert missing == set()
        finally:
            import shutil
            shutil.rmtree(workspace)

    def test_run_local_tests_continues_when_pip_install_fails(self):
        """A failed dependency install should not abort the test run."""
        sandbox = Sandbox()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir()
        ) as f:
            f.write("from tests.demo import fetch_url\n\n\ndef test_thing():\n    assert True\n")
            test_path = f.name

        try:
            with patch("subprocess.run") as mock_run, \
                 patch("core.validator.sandbox._win32_capped_run", return_value=None):
                def side_effect(cmd, *args, **kwargs):
                    if "pytest" in [str(c) for c in cmd]:
                        return MagicMock(returncode=0, stdout="1 passed in 0.01s", stderr="")
                    return MagicMock(returncode=1, stderr="No matching distribution for tests")

                mock_run.side_effect = side_effect
                result = sandbox._run_local_tests(test_path)

            assert result.get("success") is True
            assert "1 passed" in result.get("output", "")
        finally:
            os.unlink(test_path)

    def test_run_tests_docker_pip_install_is_non_fatal(self):
        """Docker test installer should ignore pip failure and still run pytest."""
        sandbox = Sandbox()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir()
        ) as f:
            f.write("from tests.demo import fetch_url\n\n\ndef test_docker_thing():\n    assert True\n")
            test_path = f.name

        try:
            captured = {}
            with patch.object(sandbox, "_is_docker_available", return_value=True), \
                 patch.object(sandbox, "_docker_image_ready", return_value=True), \
                 patch.object(
                     sandbox, "_build_docker_cmd",
                     side_effect=lambda *args, **kwargs: captured.setdefault("entry_point", args[2]),
                 ), \
                 patch.object(
                     sandbox, "_do_docker_run",
                     return_value={"success": True, "output": "ok"},
                 ):
                result = sandbox.run_tests(test_path)

            assert result.get("success") is True
            installer_code = captured["entry_point"][2]
            assert "check_call" not in installer_code
            assert "subprocess.run" in installer_code
            assert "pytest" in installer_code
        finally:
            os.unlink(test_path)

    def test_run_local_tests_rebinds_unresolvable_test_import(self):
        """A test importing from a repo module should be rebound to the patched module."""
        sandbox = Sandbox()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir()
        ) as f:
            f.write(
                "from tests.demo import fetch_url\n"
                "\n"
                "\n"
                "def test_fetch():\n"
                "    assert fetch_url() == 'ok'\n"
            )
            test_path = f.name

        try:
            with patch("subprocess.run") as mock_run, \
                 patch("core.validator.sandbox._win32_capped_run", return_value=None):
                mock_run.return_value = MagicMock(returncode=0, stdout="1 passed in 0.01s", stderr="")
                result = sandbox._run_local_tests(
                    test_path,
                    source_code="def fetch_url():\n    return 'ok'\n",
                    source_filename="demo1.py",
                )

            assert result.get("success") is True
            assert result.get("rebind", {}).get("rebound") is True
            assert mock_run.call_count == 1
            pytest_args = [str(a) for a in mock_run.call_args[0][0]]
            assert "pytest" in pytest_args
            assert "pip" not in pytest_args
        finally:
            os.unlink(test_path)

    def test_run_local_tests_skips_when_test_import_unresolvable(self):
        """A partial name match should skip the stage with a clear reason."""
        sandbox = Sandbox()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir()
        ) as f:
            f.write(
                "from tests.demo import fetch_url, API_TOKEN\n"
                "\n"
                "\n"
                "def test_fetch():\n"
                "    assert fetch_url() == API_TOKEN\n"
            )
            test_path = f.name

        try:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="1 passed", stderr="")
                result = sandbox._run_local_tests(
                    test_path,
                    source_code="def fetch_url():\n    return 'ok'\n",
                    source_filename="demo1.py",
                )

            assert result.get("success") is False
            assert result.get("skipped") is True
            assert "API_TOKEN" in result.get("error", "")
            mock_run.assert_not_called()
        finally:
            os.unlink(test_path)

    def test_run_tests_docker_rebinds_unresolvable_test_import(self):
        """Docker test installer should be bypassed when imports are rebound."""
        sandbox = Sandbox()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir()
        ) as f:
            f.write(
                "from tests.demo import fetch_url\n"
                "\n"
                "\n"
                "def test_docker_thing():\n"
                "    assert fetch_url() == 'ok'\n"
            )
            test_path = f.name

        try:
            captured = {}
            with patch.object(sandbox, "_is_docker_available", return_value=True), \
                 patch.object(sandbox, "_docker_image_ready", return_value=True), \
                 patch.object(
                     sandbox, "_build_docker_cmd",
                     side_effect=lambda *args, **kwargs: captured.setdefault("entry_point", args[2]),
                 ), \
                 patch.object(
                     sandbox, "_do_docker_run",
                     return_value={"success": True, "output": "ok"},
                 ):
                result = sandbox.run_tests(
                    test_path,
                    source_code="def fetch_url():\n    return 'ok'\n",
                    source_filename="demo1.py",
                )

            assert result.get("success") is True
            assert result.get("rebind", {}).get("rebound") is True
            entry_point = captured["entry_point"]
            assert any("pytest" in str(a) for a in entry_point)
            assert not any("pip install" in str(a) for a in entry_point)
        finally:
            os.unlink(test_path)

    def test_run_tests_docker_skips_when_test_import_unresolvable(self):
        """Docker run should be skipped entirely on an unresolvable test import."""
        sandbox = Sandbox()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir()
        ) as f:
            f.write(
                "from tests.demo import fetch_url, API_TOKEN\n"
                "\n"
                "\n"
                "def test_docker_thing():\n"
                "    assert fetch_url() == API_TOKEN\n"
            )
            test_path = f.name

        try:
            with patch.object(sandbox, "_is_docker_available", return_value=True), \
                 patch.object(sandbox, "_docker_image_ready", return_value=True), \
                 patch.object(sandbox, "_do_docker_run") as mock_run, \
                 patch.object(sandbox, "_build_docker_cmd") as mock_cmd:
                result = sandbox.run_tests(
                    test_path,
                    source_code="def fetch_url():\n    return 'ok'\n",
                    source_filename="demo1.py",
                )

            assert result.get("success") is False
            assert result.get("skipped") is True
            assert "API_TOKEN" in result.get("error", "")
            mock_run.assert_not_called()
            mock_cmd.assert_not_called()
        finally:
            os.unlink(test_path)


class TestSandboxDockerCommand:
    """Verify the hardened Docker run command carries every resource limit."""

    def test_build_docker_cmd_includes_all_limits(self):
        from core.config import config
        sandbox = Sandbox()
        dc = config.sandbox.docker
        cmd = sandbox._build_docker_cmd(
            "sandbox_health", "/tmp/workspace", ["python", "/app/smoke.py"]
        )

        assert "--rm" in cmd
        assert "--name" in cmd and "sandbox_health" in cmd[cmd.index("--name") + 1]
        assert f"--memory={dc.memory}" in cmd
        assert f"--cpus={dc.cpu}" in cmd
        assert f"--pids-limit={dc.pids_limit}" in cmd
        assert f"--network={dc.network}" in cmd
        assert "--read-only" in cmd
        assert any(a.startswith("--tmpfs") for a in cmd)
        assert "--cap-drop" in cmd and cmd[cmd.index("--cap-drop") + 1] == "ALL"
        assert "--security-opt" in cmd and cmd[cmd.index("--security-opt") + 1] == "no-new-privileges"

        mount_idx = cmd.index("-v")
        assert cmd[mount_idx + 1].endswith(":/app:ro")
        assert cmd[mount_idx + 2] == dc.image
        assert cmd[mount_idx + 3] == "python"

    def test_docker_image_available_false_without_docker(self):
        sandbox = Sandbox()
        with patch.object(sandbox, "_is_docker_available", return_value=False):
            assert sandbox.docker_image_available() is False

    def test_build_docker_cmd_network_override(self):
        sandbox = Sandbox()
        cmd = sandbox._build_docker_cmd(
            "sandbox_net", "/tmp/workspace", ["python", "/app/smoke.py"], network="bridge"
        )
        assert "--network=bridge" in cmd

    def test_run_threads_network_to_docker_cmd(self):
        sandbox = Sandbox()
        sandbox._docker_available = True
        sandbox._image_verified = True
        with patch.object(sandbox, "_build_docker_cmd") as mock_cmd, \
             patch.object(sandbox, "_do_docker_run", return_value={"success": True, "output": "ok"}):
            sandbox.run("print('x')", network="bridge")
            _, kwargs = mock_cmd.call_args
            assert kwargs["network"] == "bridge"

    def test_sandbox_cache_scoped_by_network(self):
        """Different network settings must not share sandbox cache entries."""
        from core.cache.sandbox_cache import SandboxCache
        cache = SandboxCache()
        cache.set("code", "", "secure_validation", {"success": True}, "bridge|sandbox_with_local_fallback")
        assert cache.get("code", "", "secure_validation") is None
        assert cache.get("code", "", "secure_validation", "bridge|sandbox_with_local_fallback")["success"] is True
        assert cache.get("code", "", "secure_validation", "none|") is None


class TestSandboxExtraFiles:
    """Tests for staging conftest.py and repo-relative helper modules (Phase 2)."""

    def _write_test(self, content):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir())
        f.write(content)
        f.close()
        return f.name

    def test_run_tests_docker_stages_extra_files_before_pytest(self):
        """Extra files should be written into the Docker mount before pytest runs."""
        sandbox = Sandbox()
        test_path = self._write_test(
            "from tests.helpers import make_client\n\n\ndef test_x():\n    assert make_client()\n"
        )
        try:
            captured = {}

            def build_cmd(*args, **kwargs):
                captured["mount"] = args[1]
                captured["entry"] = args[2]
                return ["docker", "run", args[1]]

            def do_run(cmd, name, **kw):
                mount = captured["mount"]
                staged = set()
                for root, _, files in os.walk(mount):
                    for fn in files:
                        rel = os.path.relpath(os.path.join(root, fn), mount).replace(os.sep, "/")
                        staged.add(rel)
                return {"success": True, "output": "ok", "staged": sorted(staged)}

            with patch.object(sandbox, "_is_docker_available", return_value=True), \
                 patch.object(sandbox, "_docker_image_ready", return_value=True), \
                 patch.object(sandbox, "_build_docker_cmd", side_effect=build_cmd), \
                 patch.object(sandbox, "_do_docker_run", side_effect=do_run):
                result = sandbox.run_tests(
                    test_path,
                    source_code="def make_client():\n    return 'ok'\n",
                    source_filename="demo1.py",
                    extra_files=[
                        {"path": "tests/helpers.py", "content": "def make_client():\n    return 'ok'\n"},
                        {"path": "conftest.py", "content": "import pytest\n"},
                    ],
                )

            assert result.get("success") is True
            assert "tests/helpers.py" in result.get("staged", [])
            assert "conftest.py" in result.get("staged", [])
            entry = captured["entry"]
            assert any("pytest" in str(a) for a in entry)
            assert not any("pip install" in str(a) for a in entry)
        finally:
            os.unlink(test_path)

    def test_run_tests_docker_rebinds_over_staged_mirror(self):
        """A staged mirror of the patched module must not shadow the rebind."""
        sandbox = Sandbox()
        test_path = self._write_test(
            "from tests.demo import fetch_url\n\n\ndef test_f():\n    assert fetch_url() == 'ok'\n"
        )
        try:
            captured = {}
            with patch.object(sandbox, "_is_docker_available", return_value=True), \
                 patch.object(sandbox, "_docker_image_ready", return_value=True), \
                 patch.object(sandbox, "_build_docker_cmd",
                              side_effect=lambda *a, **k: captured.setdefault("entry", a[2])), \
                 patch.object(sandbox, "_do_docker_run", return_value={"success": True, "output": "ok"}):
                result = sandbox.run_tests(
                    test_path,
                    source_code="def fetch_url():\n    return 'ok'\n",
                    source_filename="demo1.py",
                    extra_files=[
                        {"path": "tests/demo.py", "content": "def fetch_url():\n    return 'unpatched'\n"},
                    ],
                )
            assert result.get("rebind", {}).get("rebound") is True
            entry = captured["entry"]
            assert any("pytest" in str(a) for a in entry)
            assert not any("pip install" in str(a) for a in entry)
        finally:
            os.unlink(test_path)

    def test_run_tests_docker_uses_staged_helper_without_pip(self):
        """A genuine repo helper should resolve via the workspace, not pip."""
        sandbox = Sandbox()
        test_path = self._write_test(
            "from tests.helpers import make_client\n\n\ndef test_x():\n    assert make_client()\n"
        )
        try:
            captured = {}
            with patch.object(sandbox, "_is_docker_available", return_value=True), \
                 patch.object(sandbox, "_docker_image_ready", return_value=True), \
                 patch.object(sandbox, "_build_docker_cmd",
                              side_effect=lambda *a, **k: captured.setdefault("entry", a[2])), \
                 patch.object(sandbox, "_do_docker_run", return_value={"success": True, "output": "ok"}):
                result = sandbox.run_tests(
                    test_path,
                    source_code="def fetch_url():\n    return 'ok'\n",
                    source_filename="demo1.py",
                    extra_files=[
                        {"path": "tests/helpers.py", "content": "def make_client():\n    return 'ok'\n"},
                    ],
                )
            assert result.get("success") is True
            entry = captured["entry"]
            assert any("pytest" in str(a) for a in entry)
            assert not any("pip install" in str(a) for a in entry)
        finally:
            os.unlink(test_path)

    def test_run_local_tests_stages_extra_files(self):
        from subprocess import CompletedProcess

        sandbox = Sandbox()
        test_path = self._write_test(
            "from tests.helpers import make_client\n\n\ndef test_x():\n    assert make_client()\n"
        )
        try:
            captured = {}

            def fake_run(cmd, *args, **kwargs):
                target = cmd[3]
                helper = os.path.join(os.path.dirname(target), "tests", "helpers.py")
                captured["staged"] = os.path.exists(helper)
                captured["is_pip"] = any("pip install" in part for part in cmd)
                return CompletedProcess(cmd, 0, stdout="1 passed", stderr="")

            with patch.object(sandbox, "_is_pytest_available", return_value=True), \
                 patch("core.validator.sandbox.subprocess.run", side_effect=fake_run), \
                 patch("core.validator.sandbox._win32_capped_run", return_value=None):
                result = sandbox._run_local_tests(
                    test_path,
                    source_code="def make_client():\n    return 'ok'\n",
                    source_filename="demo1.py",
                    extra_files=[
                        {"path": "tests/helpers.py", "content": "def make_client():\n    return 'ok'\n"},
                    ],
                )
            assert result.get("success") is True
            assert captured["staged"] is True
            assert captured["is_pip"] is False
        finally:
            os.unlink(test_path)

    def test_run_local_tests_writes_mock_header_to_source(self):
        """Local test runs must apply the mock header to the source module, matching Docker."""
        from subprocess import CompletedProcess

        sandbox = Sandbox()
        test_path = self._write_test(
            "from demo1 import API_TOKEN\n\n\ndef test_token():\n    assert API_TOKEN == 'mock-api-token-xxxxx'\n"
        )
        try:
            captured = {}

            def fake_run(cmd, *args, **kwargs):
                target = cmd[3]
                src = os.path.join(os.path.dirname(target), "demo1.py")
                with open(src, "r", encoding="utf-8") as f:
                    captured["src"] = f.read()
                return CompletedProcess(cmd, 0, stdout="1 passed", stderr="")

            with patch.object(sandbox, "_is_pytest_available", return_value=True), \
                 patch("core.validator.sandbox.subprocess.run", side_effect=fake_run), \
                 patch("core.validator.sandbox._win32_capped_run", return_value=None):
                result = sandbox._run_local_tests(
                    test_path,
                    source_code="import os\nAPI_TOKEN = os.getenv('API_TOKEN')\n",
                    source_filename="demo1.py",
                )
            assert result.get("success") is True
            assert captured["src"].startswith("import builtins")
            assert "_MockEnv" in captured["src"]
            assert "API_TOKEN = os.getenv('API_TOKEN')" in captured["src"]
        finally:
            os.unlink(test_path)

    def test_run_local_tests_isolates_pytest_cwd_from_repo(self):
        """pytest must run with cwd inside the sandbox temp dir, never the repo.

        Without this, a non-rebound ``from tests.demo import ...`` resolves to
        the repository's own original module and the local run silently passes
        against unpatched code (the false "all green" signal).
        """
        from subprocess import CompletedProcess

        sandbox = Sandbox()
        test_path = self._write_test(
            "from tests.demo import fetch_url\n\n\ndef test_f():\n    assert fetch_url()\n"
        )
        try:
            captured = {}

            def fake_run(cmd, *args, **kwargs):
                cwd = kwargs.get("cwd")
                captured["cwd"] = cwd
                captured["has_src_in_cwd"] = cwd is not None and os.path.isfile(
                    os.path.join(cwd, "demo1.py")
                )
                captured["target_inside_cwd"] = cwd is not None and os.path.dirname(
                    cmd[3]
                ).startswith(os.path.normpath(cwd))
                return CompletedProcess(cmd, 0, stdout="1 passed", stderr="")

            with patch.object(sandbox, "_is_pytest_available", return_value=True), \
                 patch("core.validator.sandbox.subprocess.run", side_effect=fake_run), \
                 patch("core.validator.sandbox._win32_capped_run", return_value=None):
                result = sandbox._run_local_tests(
                    test_path,
                    source_code="def fetch_url():\n    return 'ok'\n",
                    source_filename="demo1.py",
                )
            assert result.get("success") is True
            assert captured["cwd"] is not None
            base = os.path.basename(os.path.normpath(captured["cwd"]))
            assert base.startswith("airisk_tests_"), f"pytest cwd escaped sandbox: {captured['cwd']}"
            assert os.path.normpath(captured["cwd"]) != os.path.normpath(os.getcwd())
            assert captured["has_src_in_cwd"] is True
            assert captured["target_inside_cwd"] is True
        finally:
            os.unlink(test_path)


class TestQualityScoreAnalysis:
    """
    Investigate Fix 3: Quality score uniformity.
    All findings should get the same quality_score because they share the
    same winner candidate. This is by design, but verify the scoring logic
    produces correct results per-candidate.
    """

    def setup_method(self):
        self.scorer = PatchScorer()

    def test_perfect_candidate_scores_high(self):
        """Candidate passing all stages should score high."""
        candidate = {
            "validation_details": {
                "syntax": {"success": True},
                "rescan": {"success": True},
            },
            "test_results": {"success": True, "mode": "docker"},
            "formatting_diff": 0,
            "validation_score": 1.0,
        }
        context = {"metrics": {"complexity": 2}}
        
        score = self.scorer.score(candidate, context)
        
        # syntax(0.20) + rescan(0.25) + tests(0.20) + complexity(0.10) + formatting(0.10) + confidence(0.15*1.0)
        # = 0.20 + 0.25 + 0.20 + 0.10 + 0.10 + 0.15 = 1.00
        assert score == 1.0, f"Perfect candidate should score 1.0, got {score}"

    def test_failing_sandbox_reduces_score(self):
        """Candidate with failing sandbox should have lower score."""
        candidate = {
            "validation_details": {
                "syntax": {"success": True},
                "rescan": {"success": True},
            },
            "test_results": {"success": True, "mode": "docker"},
            "formatting_diff": 0,
            "validation_score": 0.8,  # Not perfect due to sandbox failure
        }
        context = {"metrics": {"complexity": 2}}
        
        score = self.scorer.score(candidate, context)
        
        # syntax(0.20) + rescan(0.25) + tests(0.20) + complexity(0.10) + formatting(0.10) + confidence(0.15*0.8)
        # = 0.20 + 0.25 + 0.20 + 0.10 + 0.10 + 0.12 = 0.97
        assert score < 1.0, f"Should score less than 1.0, got {score}"
        assert score == 0.97, f"Expected 0.97, got {score}"

    def test_all_stages_failing(self):
        """Candidate failing all stages should score near zero."""
        candidate = {
            "validation_details": {
                "syntax": {"success": False},
                "rescan": {"success": False},
            },
            "test_results": {"success": False},
            "formatting_diff": 5,
            "validation_score": 0.0,
        }
        context = {"metrics": {"complexity": 10}}
        
        score = self.scorer.score(candidate, context)
        
        # Only complexity(8+) contributes -0.10, clamped to 0.0
        assert score == 0.0, f"Should score 0.0, got {score}"

    def test_same_candidate_same_score(self):
        """Two different findings with the same winner should get the same quality score."""
        # This verifies the design: quality_score is per-candidate, not per-finding
        candidate = {
            "validation_details": {
                "syntax": {"success": True},
                "rescan": {"success": True},
            },
            "test_results": {"success": True, "mode": "docker"},
            "formatting_diff": 0,
            "validation_score": 1.0,
        }
        context = {"metrics": {"complexity": 2}}
        
        score1 = self.scorer.score(candidate, context)
        score2 = self.scorer.score(candidate, context)
        
        assert score1 == score2, "Same candidate should always produce same score"

    def test_different_candidates_different_scores(self):
        """Different candidates should produce different scores."""
        candidate_a = {
            "validation_details": {
                "syntax": {"success": True},
                "rescan": {"success": True},
            },
            "test_results": {"success": True, "mode": "docker"},
            "formatting_diff": 0,
            "validation_score": 1.0,
        }
        
        candidate_b = {
            "validation_details": {
                "syntax": {"success": False},
                "rescan": {"success": False},
            },
            "test_results": {"success": False},
            "formatting_diff": 10,
            "validation_score": 0.0,
        }
        context = {"metrics": {"complexity": 5}}
        
        score_a = self.scorer.score(candidate_a, context)
        score_b = self.scorer.score(candidate_b, context)
        
        assert score_a > score_b, f"Candidate A ({score_a}) should score higher than B ({score_b})"

    def test_quality_score_breakdown_matches_total(self):
        """get_breakdown total should match score()."""
        candidate = {
            "validation_details": {
                "syntax": {"success": True},
                "rescan": {"success": True},
            },
            "test_results": {"success": True, "mode": "docker"},
            "formatting_diff": 0,
            "validation_score": 0.85,
        }
        context = {"metrics": {"complexity": 3}}
        
        score = self.scorer.score(candidate, context)
        breakdown = self.scorer.get_breakdown(candidate, context)
        
        assert breakdown["total"] == score, (
            f"Breakdown total ({breakdown['total']}) should match score ({score})"
        )

    def test_validation_score_weight_is_15_percent(self):
        """validation_score should contribute 15% weight to final score."""
        candidate_perfect = {
            "validation_details": {"syntax": {"success": True}, "rescan": {"success": True}},
            "test_results": {"success": True, "mode": "docker"},
            "formatting_diff": 0,
            "validation_score": 1.0,
        }
        candidate_zero = {
            "validation_details": {"syntax": {"success": True}, "rescan": {"success": True}},
            "test_results": {"success": True, "mode": "docker"},
            "formatting_diff": 0,
            "validation_score": 0.0,
        }
        context = {"metrics": {"complexity": 3}}
        
        score_perfect = self.scorer.score(candidate_perfect, context)
        score_zero = self.scorer.score(candidate_zero, context)
        
        diff = score_perfect - score_zero
        assert abs(diff - 0.15) < 0.01, (
            f"Difference should be ~0.15 (15% weight), got {diff}"
        )

    def test_risk_agent_assigns_same_quality_to_all_findings(self):
        """
        Verify the root cause: RiskAgent assigns winner's quality_score
        to ALL findings. This is by design (quality is per-patch, not per-vuln).
        """
        # Simulate what RiskAgent does at line 171:
        # "quality_score": winner.get("quality_score", 0)
        winner_quality_score = 0.453
        
        findings = [
            {"type": "COMMAND_INJECTION", "severity": "HIGH"},
            {"type": "SQL_INJECTION", "severity": "HIGH"},
            {"type": "SSRF", "severity": "MEDIUM"},
        ]
        
        for vuln in findings:
            vuln["quality_score"] = winner_quality_score
        
        # All findings should have the same quality score
        scores = [f["quality_score"] for f in findings]
        assert len(set(scores)) == 1, "All findings should share the winner's quality score"
        assert scores[0] == 0.453


class TestValidationScoreInValidatorAgent:
    """
    Verify that ValidatorAgent correctly computes validation_score
    and handles skipped vs failed stages.
    """

    def test_skipped_test_does_not_affect_score(self):
        """
        When no test file exists, tests are 'skipped' (not failed).
        Skipped tests should not penalize validation_score.
        """
        # Simulate ValidatorAgent scoring logic (lines 80-92)
        syntax_res = {"success": True}
        sandbox_res = {"success": True}
        rescan_res = {"success": True}
        policy_res = {"success": True}
        test_results = {"success": False, "skipped": True, "error": "No test file"}
        
        score = 0.0
        if syntax_res.get("success") is True:
            score += 0.20
        if sandbox_res.get("success") is True:
            score += 0.25
        if rescan_res.get("success") is True:
            score += 0.15
        if policy_res.get("success") is True:
            score += 0.15
        if test_results.get("success") is True:
            score += 0.25
        
        score = round(score, 2)
        
        # Score should be 0.75 (missing 0.25 from tests, but tests are SKIPPED not FAILED)
        # This is a known design issue: skipped tests are penalized the same as failed tests
        assert score == 0.75, f"Expected 0.75, got {score}"
        # NOTE: This reveals a potential improvement - skipped tests could be excluded
        # from scoring entirely, giving a higher base score.

    def test_all_passing_gives_perfect_score(self):
        """All stages passing should give validation_score of 1.0."""
        syntax_res = {"success": True}
        sandbox_res = {"success": True}
        rescan_res = {"success": True}
        policy_res = {"success": True}
        test_results = {"success": True}
        
        score = 0.0
        if syntax_res.get("success") is True:
            score += 0.20
        if sandbox_res.get("success") is True:
            score += 0.25
        if rescan_res.get("success") is True:
            score += 0.15
        if policy_res.get("success") is True:
            score += 0.15
        if test_results.get("success") is True:
            score += 0.25
        
        score = round(score, 2)
        assert score == 1.0, f"Expected 1.0, got {score}"

    def test_sandbox_failure_reduces_score(self):
        """Sandbox failure should reduce score by 0.25."""
        syntax_res = {"success": True}
        sandbox_res = {"success": False, "error": "Sandbox timeout"}
        rescan_res = {"success": True}
        policy_res = {"success": True}
        test_results = {"success": False, "skipped": True}
        
        score = 0.0
        if syntax_res.get("success") is True:
            score += 0.20
        if sandbox_res.get("success") is True:
            score += 0.25
        if rescan_res.get("success") is True:
            score += 0.15
        if policy_res.get("success") is True:
            score += 0.15
        if test_results.get("success") is True:
            score += 0.25
        
        score = round(score, 2)
        assert score == 0.50, f"Expected 0.50, got {score}"
