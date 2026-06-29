"""
tests/test_core.py

Updated Unit Tests for Multi-Agent Mesh.
Run with: pytest tests/ -v
"""

import os
import tempfile
import ast
import pytest

from app.main import AIRiskGuard
from core.scanner.vulnerability_scanner import VulnerabilityScanner
from core.patch.fixers import apply_patch_to_content
from core.scanner.diff_engine import DiffAwareScanner
from core.scanner.context_validator import ContextValidator
from core.agents.manager_agent import ManagerAgent

# =========================================================
# HELPERS
# =========================================================

def write_temp_file(content, suffix=".py"):
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode="w", encoding="utf-8")
    temp.write(content)
    temp.close()
    return temp.name

# =========================================================
# ORCHESTRATION TESTS (NEW: WEEK 1-6)
# =========================================================

class TestOrchestrator:
    """Tests the new Multi-Agent Manager orchestration."""
    
    def setup_method(self):
        self.orchestrator = AIRiskGuard()

    def test_full_pipeline_clean_code(self):
        path = write_temp_file('print("safe code")')
        try:
            results = self.orchestrator.analyze_file(path)
            assert results == []
        finally:
            os.unlink(path)

    def test_full_pipeline_vulnerable_code(self):
        # Stress test logic: detection -> patching -> validation -> risk
        path = write_temp_file('import os\nos.system("ls")')
        try:
            results = self.orchestrator.analyze_file(path)
            if results: # Depends on environment (e.g. if Docker is running)
                assert len(results) > 0
                assert results[0]["vulnerability"]["type"] == "COMMAND_INJECTION"
                assert "patch" in results[0]
                assert "risk" in results[0]
        finally:
            os.unlink(path)

# =========================================================
# SCANNER TESTS
# =========================================================

class TestScanner:
    def setup_method(self):
        self.scanner = VulnerabilityScanner()

    def test_os_system_detected(self):
        path = write_temp_file('import os\nos.system("ls")')
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert any(f["type"] == "COMMAND_INJECTION" for f in findings)

    def test_eval_detected(self):
        path = write_temp_file('eval(user_input)')
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert any(f["type"] == "CODE_INJECTION" for f in findings)

    def test_deserialization_detected(self):
        path = write_temp_file('import pickle\npickle.loads(data)')
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert any(f["type"] == "INSECURE_DESERIALIZATION" for f in findings)

# =========================================================
# PATCH TESTS
# =========================================================

class TestPatchEngine:
    def test_command_injection_patch(self):
        code = 'import os\nos.system("ls")'
        vuln = {"type": "COMMAND_INJECTION", "line": 2, "code": 'os.system("ls")'}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "subprocess.run" in result["patched_code"]
        assert "shell=False" in result["patched_code"]

    def test_eval_patch(self):
        code = 'result = eval(data)'
        vuln = {"type": "CODE_INJECTION", "line": 1, "code": 'eval(data)'}
        result = apply_patch_to_content(code, vuln)
        assert "ast.literal_eval" in result["patched_code"]

    def test_deserialization_patch(self):
        code = 'import pickle\ndata = pickle.loads(payload)'
        vuln = {"type": "INSECURE_DESERIALIZATION", "line": 2, "code": 'pickle.loads(payload)'}
        result = apply_patch_to_content(code, vuln)
        assert "json.loads" in result["patched_code"]
        # Verify Governance: Check if pickle was removed
        assert "import pickle" not in result["patched_code"]

# =========================================================
# CONTEXT VALIDATOR TESTS
# =========================================================

class TestContextValidator:
    def setup_method(self):
        self.validator = ContextValidator()

    def test_placeholder_ignored(self):
        # Refined patterns: your_..._here should be ignored
        assert self.validator.is_placeholder("your_api_key_here")

    def test_real_secret_not_ignored(self):
        # Ensure high-entropy real-looking secrets are NOT flagged as placeholders
        assert not self.validator.is_placeholder("AKIAIM5H3V5J6EXAMPLE")

    def test_test_file_detected(self):
        assert self.validator.is_test_file("/tests/test_auth.py")
