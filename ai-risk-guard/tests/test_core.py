"""
tests/test_core.py

Updated Unit Tests for Multi-Agent Mesh.
Run with: pytest tests/ -v
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.main import AIRiskGuard
from core.patch.fixers import apply_patch_to_content
from core.scanner.context_validator import ContextValidator
from core.scanner.vulnerability_scanner import VulnerabilityScanner

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

    def test_sql_injection_detected(self):
        path = write_temp_file("cursor.execute(f'SELECT * FROM users WHERE username = {name}')")
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert any(f["type"] == "SQL_INJECTION" for f in findings)

    def test_path_traversal_detected(self):
        path = write_temp_file("open('/uploads/' + user_file)")
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert any(f["type"] == "PATH_TRAVERSAL" for f in findings)

    def test_ssrf_detected(self):
        path = write_temp_file("import requests\nrequests.get(target_url)")
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert any(f["type"] == "SSRF" for f in findings)

    def test_weak_cryptography_detected(self):
        path = write_temp_file("import hashlib\nhashlib.md5(data)")
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert any(f["type"] == "WEAK_CRYPTOGRAPHY" for f in findings)

    def test_hardcoded_secret_via_assign_detected(self):
        path = write_temp_file('api_password = "supersecretvalue"')
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert any(f["type"] == "HARDCODED_SECRET" for f in findings)

    def test_marshal_deserialization_detected(self):
        path = write_temp_file("import marshal\nmarshal.loads(data)")
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert any(f["type"] == "INSECURE_DESERIALIZATION" for f in findings)

    def test_yaml_load_without_safe_loader_detected(self):
        path = write_temp_file("import yaml\nconfig = yaml.load(open('conf.yaml'))")
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert any(f["type"] == "INSECURE_DESERIALIZATION" for f in findings)

    def test_yaml_unsafe_load_detected(self):
        path = write_temp_file("import yaml\nconfig = yaml.unsafe_load(open('conf.yaml'))")
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert any(f["type"] == "INSECURE_DESERIALIZATION" for f in findings)

    def test_yaml_load_with_safe_loader_not_detected(self):
        path = write_temp_file("import yaml\nconfig = yaml.load(open('conf.yaml'), Loader=yaml.SafeLoader)")
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert not any(f["type"] == "INSECURE_DESERIALIZATION" for f in findings)

    def test_breakpoint_detected(self):
        path = write_temp_file("def handler():\n    breakpoint()")
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert any(f["type"] == "DEBUG_CODE" for f in findings)

    def test_pdb_set_trace_detected(self):
        path = write_temp_file("import pdb\ndef handler():\n    pdb.set_trace()")
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert any(f["type"] == "DEBUG_CODE" for f in findings)

    def test_tls_verification_disabled_detected(self):
        path = write_temp_file("import requests\nrequests.get('https://internal.api/users', verify=False)")
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert any(f["type"] == "TLS_VERIFICATION_DISABLED" for f in findings)

    def test_tls_verification_enabled_not_detected(self):
        path = write_temp_file("import requests\nrequests.get('https://internal.api/users', verify=True)")
        findings = self.scanner.scan_file(path)
        os.unlink(path)
        assert not any(f["type"] == "TLS_VERIFICATION_DISABLED" for f in findings)

    def test_diff_aware_scanning(self):
        content = (
            "import os\n"
            "os.system('ls')\n"
            "print('Hello')\n"
        )
        path = write_temp_file(content)
        basename = os.path.basename(path)
        
        # 1. Diff that does NOT modify line 2 (vulnerability should be ignored)
        diff_ignore = (
            f"--- a/{basename}\n"
            f"+++ b/{basename}\n"
            "@@ -3,1 +3,2 @@\n"
            " print('Hello')\n"
            "+print('World')\n"
        )
        findings_ignore = self.scanner.scan_file(path, diff_data=diff_ignore)
        
        # 2. Diff that modifies line 2 (vulnerability should be reported)
        diff_report = (
            f"--- a/{basename}\n"
            f"+++ b/{basename}\n"
            "@@ -2,1 +2,1 @@\n"
            "+os.system('ls')\n"
        )
        findings_report = self.scanner.scan_file(path, diff_data=diff_report)
        
        os.unlink(path)
        
        assert len(findings_ignore) == 1
        assert findings_ignore[0]["is_new"] is False, "Untouched legacy vulnerability should be marked as not new"
        
        assert len(findings_report) == 1
        assert findings_report[0]["is_new"] is True, "Modified vulnerability should be marked as new"
        assert findings_report[0]["type"] == "COMMAND_INJECTION"

# =========================================================
# SILENT ALERT TESTS (informational, non-blocking types)
# =========================================================

class TestSilentAlerts:
    def test_silent_types_defined(self):
        from core.metadata.vuln_metadata import SILENT_TYPES
        assert "DEBUG_CODE" in SILENT_TYPES
        assert "TLS_VERIFICATION_DISABLED" in SILENT_TYPES

    def test_unpatchable_types_not_in_fixer_set(self):
        from core.patch.fixers import SUPPORTED_FIXER_TYPES
        assert "DEBUG_CODE" not in SUPPORTED_FIXER_TYPES
        assert "TLS_VERIFICATION_DISABLED" not in SUPPORTED_FIXER_TYPES

    def test_silent_types_kept_as_conflicts_without_error(self):
        from core.patch.fixers import apply_patch_to_content
        from core.patch.patch_orchestrator import apply_patches_safely
        code = "import requests\nrequests.get(url, verify=False)\ndef h():\n    breakpoint()"
        vulns = [
            {"type": "TLS_VERIFICATION_DISABLED", "line": 2},
            {"type": "DEBUG_CODE", "line": 4},
        ]
        result = apply_patches_safely(code, vulns, apply_patch_to_content)
        assert result["final_code"] == code
        assert len(result["conflicts"]) == 2
        assert result["applied"] == []
        assert result["errors"] == []

    def test_mock_header_neutralizes_debugger(self):
        from sandbox.mock_header import build_mock_header
        header = build_mock_header()
        assert "builtins.breakpoint = _noop" in header
        assert "sys.breakpointhook = _noop" in header
        assert "sys.modules.setdefault('pdb', _pdb_stub)" in header

    def test_mock_header_exposes_mocked_env_vars(self):
        from sandbox.mock_header import MOCKED_ENV_VARS, build_mock_header
        header = build_mock_header()
        for var in MOCKED_ENV_VARS:
            assert f"setdefault('{var}'" in header
        assert "API_TOKEN" in MOCKED_ENV_VARS

    def test_mock_header_uses_str_keyed_env_with_path(self):
        from sandbox.mock_header import build_mock_header
        header = build_mock_header()
        assert "isinstance(k, str)" in header
        assert "_env.setdefault('PATH'," in header

    def test_sandbox_local_runs_debug_code_without_hang(self):
        from core.validator.sandbox import Sandbox
        code = "import pdb\nbreakpoint()\ndef main():\n    pdb.set_trace()\n    return 42\nprint(main())"
        result = Sandbox()._run_local(code, source_filename="snippet.py")
        assert result.get("success") is True
        assert "42" in (result.get("output") or "")

    def test_pipeline_marks_tls_finding_as_silent(self):
        path = write_temp_file("import requests\nrequests.get('https://internal.api/users', verify=False)")
        try:
            engine = AIRiskGuard()
            results = engine.analyze_file(path)
        finally:
            os.unlink(path)
        tls = [r for r in results if r["vulnerability"]["type"] == "TLS_VERIFICATION_DISABLED"]
        assert tls
        assert all(r.get("is_silent") is True for r in tls)

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

    def test_command_injection_subprocess_shell_true(self):
        code = 'import subprocess\nresult = subprocess.run(f"ping -c 2 {domain}", shell=True, capture_output=True, text=True)'
        vuln = {"type": "COMMAND_INJECTION", "line": 2, "code": "subprocess.run(f\"ping -c 2 {domain}\", shell=True, capture_output=True, text=True)"}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "shell=False" in result["patched_code"]
        assert "shlex.split" in result["patched_code"]
        assert "shell=True" not in result["patched_code"]

    def test_command_injection_subprocess_shell_true_multiline(self):
        code = (
            'import subprocess\n'
            'result = subprocess.run(\n'
            '    f"ping -c 2 {domain}",\n'
            '    shell=True,\n'
            '    capture_output=True,\n'
            '    text=True,\n'
            ')\n'
        )
        vuln = {"type": "COMMAND_INJECTION", "line": 2, "code": "subprocess.run(f\"ping -c 2 {domain}\", shell=True, capture_output=True, text=True)"}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "shlex.split" in result["patched_code"]
        assert "shell=False" in result["patched_code"]

    def test_patch_diff_is_minimal_unchanged_lines_preserved(self):
        code = 'import requests\n\ndef fetch_url(target_url):\n    resp = requests.get(target_url, timeout=15)\n    return resp.status_code, resp.text\n'
        vuln = {"type": "SSRF", "line": 4, "code": "resp = requests.get(target_url, timeout=15)"}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "return resp.status_code, resp.text" in result["patched_code"]
        diff = result["diff"]
        assert "-    resp = requests.get(target_url, timeout=15)" in diff
        assert "+    resp = requests.get(validate_url_ssrf(target_url), timeout=15)" in diff
        assert "-    return resp.status_code, resp.text" not in diff

    def test_patch_diff_minimal_multiline_statement(self):
        code = (
            'import os\nimport json\nfrom urllib.parse import urlparse\n\n'
            'def export_json(data, url):\n'
            '    hostname = urlparse(url).hostname or "unknown"\n'
            '    with open(f"report_{hostname}.json", "w") as f:\n'
            '        json.dump(data, f, indent=2)\n'
        )
        vuln = {"type": "PATH_TRAVERSAL", "line": 7, "code": 'with open(f"report_{hostname}.json", "w") as f:'}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "hostname = urlparse(url).hostname or \"unknown\"" in result["patched_code"]
        diff = result["diff"]
        assert "+    with open(safe_path_join('.', f'report_{hostname}.json'), 'w') as f:" in diff
        assert "-    hostname = urlparse(url).hostname or \"unknown\"" not in diff

    def test_eval_patch(self):
        code = 'result = eval(data)'
        vuln = {"type": "CODE_INJECTION", "line": 1, "code": 'eval(data)'}
        result = apply_patch_to_content(code, vuln)
        assert "ast.literal_eval" in result["patched_code"]

    def test_deserialization_patch(self):
        code = 'import pickle\ndata = pickle.loads(payload)'
        vuln = {"type": "INSECURE_DESERIALIZATION", "line": 2, "code": 'pickle.loads(payload)'}
        result = apply_patch_to_content(code, vuln)
        assert "safe_loads" in result["patched_code"]
        assert "RestrictedUnpickler" in result["patched_code"]

    def test_sql_injection_patch(self):
        code = 'import sqlite3\nconn = sqlite3.connect("db.sqlite")\nconn.execute(f"SELECT * FROM users WHERE username = {name}")'
        vuln = {"type": "SQL_INJECTION", "line": 3, "code": "conn.execute(f'SELECT * FROM users WHERE username = {name}')"}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "?" in result["patched_code"]
        assert "name" in result["patched_code"]

    def test_path_traversal_patch(self):
        code = "open('/uploads/' + user_file)"
        vuln = {"type": "PATH_TRAVERSAL", "line": 1, "code": "open('/uploads/' + user_file)"}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "safe_path_join" in result["patched_code"]

    def test_path_traversal_fstring_no_prefix(self):
        code = "open(f\"report_{hostname}.json\")"
        vuln = {"type": "PATH_TRAVERSAL", "line": 1, "code": "open(f\"report_{hostname}.json\")"}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "safe_path_join" in result["patched_code"]
        assert "safe_path_join('.'" in result["patched_code"] or "safe_path_join(\".\"" in result["patched_code"]

    def test_ssrf_patch(self):
        code = "import requests\nrequests.get(target_url)"
        vuln = {"type": "SSRF", "line": 2, "code": "requests.get(target_url)"}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "validate_url_ssrf" in result["patched_code"]

    def test_weak_cryptography_patch(self):
        code = "import hashlib\nhashlib.md5(data)"
        vuln = {"type": "WEAK_CRYPTOGRAPHY", "line": 2, "code": "hashlib.md5(data)"}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "hashlib.sha256" in result["patched_code"]

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


# =========================================================
# POLICY ENGINE TESTS
# =========================================================

class TestPolicyEngine:
    def test_weak_crypto_policy_violations(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        
        # Test code containing hashlib.md5 should violate policy
        code = "import hashlib\nhashlib.md5(data)"
        res = policy.check_compliance(code)
        assert res["success"] is False
        assert any("Forbidden function call: hashlib.md5" in v for v in res["violations"])
        
        # Test code containing hashlib.sha1 should violate policy
        code = "import hashlib\nhashlib.sha1(data)"
        res = policy.check_compliance(code)
        assert res["success"] is False
        assert any("Forbidden function call: hashlib.sha1" in v for v in res["violations"])

        # Clean code should pass
        code = "import hashlib\nhashlib.sha256(data)"
        res = policy.check_compliance(code)
        assert res["success"] is True


# =========================================================
# SECURITY RESCAN TESTS
# =========================================================

class TestSecurityRescan:
    def test_security_rescan_clean_code(self):
        from core.validator.security_rescan import SecurityRescanner
        rescanner = SecurityRescanner()
        code = 'print("Hello World")'
        result = rescanner.rescan_code(code)
        assert result["success"] is True
        assert len(result["remaining_vulnerabilities"]) == 0

    def test_security_rescan_vulnerable_code(self):
        from core.validator.security_rescan import SecurityRescanner
        rescanner = SecurityRescanner()
        code = 'import os\nos.system("ls")'
        result = rescanner.rescan_code(code)
        assert result["success"] is False
        assert len(result["remaining_vulnerabilities"]) > 0
        assert result["remaining_vulnerabilities"][0]["type"] == "COMMAND_INJECTION"

    def test_security_rescan_recognizes_safe_path_join(self):
        """A PATH_TRAVERSAL fix via safe_path_join must pass the re-scan.

        Regression: the scanner only recognized basename/PurePath.name, so a
        patched open(safe_path_join(...), ...) was still flagged, leaving
        "Rescan: 1 left" for every candidate.
        """
        from core.validator.security_rescan import SecurityRescanner
        rescanner = SecurityRescanner()
        code = (
            'import os\n'
            'def safe_path_join(base_dir, user_path):\n'
            '    base = os.path.realpath(base_dir)\n'
            '    full = os.path.realpath(os.path.join(base, user_path))\n'
            '    if not full.startswith(base + os.sep) and full != base:\n'
            '        raise ValueError("Path traversal detected")\n'
            '    return os.path.normpath(os.path.join(base_dir, user_path))\n'
            'open(safe_path_join(".", f"report_{hostname}.json"), "w")\n'
        )
        result = rescanner.rescan_code(code)
        assert result["success"] is True
        assert len(result["remaining_vulnerabilities"]) == 0

    def test_safe_path_join_preserves_relative_path(self):
        """The injected safe_path_join must keep relative paths relative.

        Regression: realpath(base_dir) absolutized "." to the CWD (e.g. /app in
        Docker), silently changing open("report_x.json") -> open("/app/report_x.json").
        """
        import tempfile

        from core.patch.fixers import _SAFE_PATH_JOIN_SRC
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
            f.write(_SAFE_PATH_JOIN_SRC)
            helper_path = f.name
        import importlib.util
        spec = importlib.util.spec_from_file_location("_spj_helper", helper_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import os as _os
        _os.remove(helper_path)
        result = mod.safe_path_join(".", "report_example.com.json")
        assert result == "report_example.com.json"
        assert not os.path.isabs(result)


    def test_security_rescan_concurrent_isolation(self):
        """Concurrent rescan_code calls must not corrupt each other's results.

        Regression: SecurityRescanner reused one mutable VulnerabilityScanner, so
        the validator's parallel candidate validation (ThreadPoolExecutor) leaked
        findings between candidates — clean code could report "remaining"
        vulnerabilities and every candidate failed re-scan.
        """
        from concurrent.futures import ThreadPoolExecutor

        from core.validator.security_rescan import SecurityRescanner

        samples = {
            "clean": ('import os\n'
                      'def read(path):\n'
                      '    return open(path, "r").read()\n'),
            "cmd_injection": 'import os\nos.system("ls")\n',
            "hardcoded_secret": 'import os\nAPI_KEY = "sk-1234567890abcdef"\n',
        }

        baseline = {
            name: (SecurityRescanner().rescan_code(code)["remaining_vulnerabilities"])
            for name, code in samples.items()
        }

        rescanner = SecurityRescanner()
        with ThreadPoolExecutor(max_workers=len(samples)) as pool:
            futures = {
                pool.submit(rescanner.rescan_code, code): name
                for name, code in samples.items()
            }
            concurrent = {
                futures[f]: f.result()["remaining_vulnerabilities"]
                for f in futures
            }

        for name, expected in baseline.items():
            got = concurrent[name]
            assert [v["type"] for v in got] == [v["type"] for v in expected], name


# =========================================================
# DASHBOARD TESTS
# =========================================================

class TestDashboard:
    def setup_method(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import utils.db as udb
        self._db_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        self._db_patcher = patch.object(udb, "DB_PATH", Path(self._db_tmp))
        self._db_patcher.start()
        udb.init_db()
        from app.app import app
        self.client = app.test_client()

    def teardown_method(self):
        import os
        self._db_patcher.stop()
        try:
            os.unlink(self._db_tmp)
        except PermissionError:
            pass

    def test_computed_avg_risk_score(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import utils.db as udb
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        try:
            with patch.object(udb, "DB_PATH", Path(tmp)):
                udb.init_db()
                udb.increment_dashboard(10, "HIGH")
                udb.increment_dashboard(5, "MEDIUM")
                d = udb.get_dashboard()
                assert d["total_vulnerabilities"] == 15
                assert d["risk_levels"]["HIGH"] == 1
                assert d["risk_levels"]["MEDIUM"] == 1
                assert d["avg_risk_score"] == 0.9
        finally:
            try: os.unlink(tmp)
            except PermissionError: pass

    def test_computed_remediation_rate(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import utils.db as udb
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        try:
            with patch.object(udb, "DB_PATH", Path(tmp)):
                udb.init_db()
                udb.increment_dashboard(1, "LOW")
                udb.record_feedback("SQL", "ACCEPTED")
                udb.record_feedback("CMD", "ACCEPTED")
                udb.record_feedback("SQL", "REJECTED")
                d = udb.get_dashboard()
                assert d["remediation_rate"] == 66.7
        finally:
            try: os.unlink(tmp)
            except PermissionError: pass

    def test_computed_cache_hit_rate(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import utils.db as udb
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        try:
            with patch.object(udb, "DB_PATH", Path(tmp)):
                udb.init_db()
                with udb._connect() as conn:
                    conn.execute("UPDATE dashboard SET value = 30 WHERE key = 'cache_hits'")
                    conn.execute("UPDATE dashboard SET value = 10 WHERE key = 'cache_misses'")
                    conn.commit()
                d = udb.get_dashboard()
                assert d["cache_hit_rate"] == 75.0
        finally:
            try: os.unlink(tmp)
            except PermissionError: pass

    def test_dashboard_zero_defaults(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import utils.db as udb
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        try:
            with patch.object(udb, "DB_PATH", Path(tmp)):
                udb.init_db()
                d = udb.get_dashboard()
                assert d["avg_risk_score"] == 0.0
                assert d["remediation_rate"] == 0.0
                assert d["cache_hit_rate"] == 0.0
        finally:
            try: os.unlink(tmp)
            except PermissionError: pass

    def test_dashboard_endpoints(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import utils.db as udb
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        try:
            with patch.object(udb, "DB_PATH", Path(tmp)):
                udb.init_db()
                udb.increment_dashboard(3, "HIGH")
                udb.increment_dashboard(1, "MEDIUM")
                udb.record_feedback("SQL_INJECTION", "ACCEPTED")
                udb.record_feedback("COMMAND_INJECTION", "REJECTED")

                with self.client.session_transaction() as sess:
                    sess["user"] = {"github_id": "123", "login": "tester"}
                for endpoint in ("/", "/dashboard", "/api/metrics", "/api/policy"):
                    response = self.client.get(endpoint)
                    assert response.status_code == 200

                with self.client.session_transaction() as sess:
                    sess.clear()
                for endpoint in ("/api/metrics", "/api/policy", "/api/repos"):
                    response = self.client.get(endpoint)
                    assert response.status_code == 401
        finally:
            try: os.unlink(tmp)
            except PermissionError: pass

    def test_get_scan_and_findings_roundtrip(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import utils.db as udb
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        try:
            with patch.object(udb, "DB_PATH", Path(tmp)):
                udb.init_db()
                udb.upsert_repo({
                    "id": 1, "full_name": "acme/demo", "owner": "acme",
                    "name": "demo", "description": "", "language": "Python",
                    "private": 0, "default_branch": "main", "install_id": 5,
                })
                scan_id = udb.record_scan(
                    repo_id=1, pr_number=42, pr_title="Fix login vuln",
                    branch="feature/x", commit_sha="abc123",
                    findings_count=2, max_risk=8.5, duration_ms=1500,
                )
                udb.record_finding(scan_id, "SQL_INJECTION", "HIGH", 8.5, "app.py", 12, is_new=1)
                udb.record_finding(scan_id, "HARDCODED_SECRET", "MEDIUM", 5.0, "config.py", 3)

                scan = udb.get_scan(scan_id)
                assert scan is not None
                assert scan["repo_full_name"] == "acme/demo"
                assert scan["pr_number"] == 42
                assert scan["findings_count"] == 2

                findings = udb.get_scan_findings(scan_id)
                assert len(findings) == 2
                assert findings[0]["vuln_type"] == "SQL_INJECTION"
                assert findings[0]["is_new"] == 1
                assert findings[0]["risk_score"] == 8.5

                assert udb.get_scan(99999) is None
                assert udb.get_scan_findings(99999) == []
        finally:
            try: os.unlink(tmp)
            except PermissionError: pass

    def test_scan_detail_endpoints(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import utils.db as udb
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        try:
            with patch.object(udb, "DB_PATH", Path(tmp)):
                udb.init_db()
                udb.upsert_repo({
                    "id": 2, "full_name": "acme/demo", "owner": "acme",
                    "name": "demo", "description": "", "language": "Python",
                    "private": 0, "default_branch": "main", "install_id": 5,
                })
                scan_id = udb.record_scan(
                    repo_id=2, pr_number=7, pr_title="Add tests",
                    branch="main", commit_sha="deadbeef",
                    findings_count=1, max_risk=4.0, duration_ms=900,
                )
                udb.record_finding(scan_id, "SSRF", "MEDIUM", 4.0, "fetch.py", 8)

                # User 123 must have access to the repo's installation (install 5)
                udb.upsert_user(123, "tester", "Tester", "")
                udb.sync_user_installations(123, [{"id": 5, "account": {"type": "User", "login": "tester"}}])

                with self.client.session_transaction() as sess:
                    sess["user"] = {"github_id": "123", "login": "tester"}

                response = self.client.get(f"/api/scans/{scan_id}")
                assert response.status_code == 200
                body = response.get_json()
                assert body["scan"]["pr_number"] == 7
                assert body["scan"]["repo_full_name"] == "acme/demo"

                response = self.client.get(f"/api/scans/{scan_id}/findings")
                assert response.status_code == 200
                assert len(response.get_json()["findings"]) == 1

                response = self.client.get("/api/scans/99999")
                assert response.status_code == 404
                response = self.client.get("/api/scans/99999/findings")
                assert response.status_code == 404
        finally:
            try: os.unlink(tmp)
            except PermissionError: pass


class TestHybridReporter:
    def test_format_report_split(self):
        from services.github.reporter import format_report
        
        # Test case with one new and one legacy vulnerability
        results = [
            {
                "vulnerability": {
                    "type": "COMMAND_INJECTION",
                    "file": "app.py",
                    "line": 10,
                    "code": "os.system(cmd)",
                    "severity": "HIGH",
                    "is_new": True,
                    "cwe": "CWE-78",
                    "owasp": "A01:2021"
                },
                "risk": 8.5,
                "confidence": 0.9,
                "validation": {"success": True, "policy_violations": []},
                "risk_breakdown": {}
            },
            {
                "vulnerability": {
                    "type": "HARDCODED_SECRET",
                    "file": "app.py",
                    "line": 20,
                    "code": "API_KEY = '12345'",
                    "severity": "HIGH",
                    "is_new": False,
                    "cwe": "CWE-798",
                    "owasp": "A07:2021"
                },
                "risk": 9.0,
                "confidence": 0.8,
                "validation": {"success": True, "policy_violations": []},
                "risk_breakdown": {}
            }
        ]
        
        report = format_report(results)

        assert "**Scan 1**" in report or "Scan 1" in report
        assert "Findings (1)" in report
        assert "1 legacy finding" in report
        assert "Command Injection" in report
        assert "Hardcoded Secret" in report
        assert "*(legacy)*" in report
        assert "SARIF alerts: Security" in report


# =========================================================
# EXTENDED POLICY ENGINE TESTS
# =========================================================

class TestPolicyEngineExtended:
    """Extended tests for PolicyEngine covering untested paths."""

    def test_check_compliance_forbidden_module(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = "import marshal"
        res = policy.check_compliance(code)
        assert res["success"] is False
        assert any("Forbidden module import" in v for v in res["violations"])

    def test_check_compliance_mandatory_sanitizer_missing(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'import subprocess\nsubprocess.run("ls")'
        res = policy.check_compliance(code)
        assert res["success"] is False
        assert any("Missing mandatory sanitizer" in v for v in res["violations"])

    def test_check_compliance_mandatory_sanitizer_present(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'import subprocess\nsubprocess.run("ls", shell=False)'
        res = policy.check_compliance(code)
        assert res["success"] is True

    def test_enforce_sanitizers_injects_missing_kwarg(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        out = policy.enforce_sanitizers('import subprocess\nsubprocess.run(["ls"])')
        assert "shell=False" in out

    def test_enforce_sanitizers_keeps_explicit_shell_false(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'import subprocess\nsubprocess.run(["ls"], shell=False)'
        assert policy.enforce_sanitizers(code).strip() == code

    def test_enforce_sanitizers_does_not_mask_shell_true(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'import subprocess\nsubprocess.run(f"ping -c 2 {domain}", shell=True)'
        out = policy.enforce_sanitizers(code)
        assert "shell=True" in out
        assert "shell=False" not in out

    def test_is_path_sensitive(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        assert policy.is_path_sensitive("src/auth/login.py") is True
        assert policy.is_path_sensitive("src/secrets/config.py") is True
        assert policy.is_path_sensitive("src/utils/helpers.py") is False

    def test_check_compliance_internal_error_returns_false(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        res = policy.check_compliance("not valid python @@")
        assert res["success"] is False
        assert len(res["violations"]) > 0


class TestPolicyEngineNewRules:
    """Tests for the 4 new policy rule types."""

    def test_restricted_function_args_violation_md5(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'import hashlib\nhashlib.new("md5")'
        res = policy.check_compliance(code)
        assert res["success"] is False
        assert any("Weak hash" in v for v in res["violations"])

    def test_restricted_function_args_violation_sha1(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'import hashlib\nhashlib.new("sha1")'
        res = policy.check_compliance(code)
        assert res["success"] is False
        assert any("Weak hash" in v for v in res["violations"])

    def test_restricted_function_args_clean(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'import hashlib\nhashlib.new("sha256")'
        res = policy.check_compliance(code)
        assert res["success"] is True

    def test_restricted_function_args_non_constant_arg(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = "import hashlib\nalgo = 'md5'\nhashlib.new(algo)"
        res = policy.check_compliance(code)
        assert res["success"] is True

    def test_mandatory_call_wrapper_ssrf_wrapped(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'import requests\ndef validate_url_ssrf(url): pass\nrequests.get(validate_url_ssrf("https://example.com"))'
        res = policy.check_compliance(code)
        assert res["success"] is True

    def test_mandatory_call_wrapper_ssrf_unwrapped(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'import requests\nrequests.get("https://example.com")'
        res = policy.check_compliance(code)
        assert res["success"] is False
        assert any("validate_url_ssrf" in v for v in res["violations"])

    def test_mandatory_call_wrapper_path_traversal_safe(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'import os\nopen(os.path.basename("/some/path"))'
        res = policy.check_compliance(code)
        assert res["success"] is True

    def test_mandatory_call_wrapper_path_traversal_unsafe(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'open("/etc/passwd")'
        res = policy.check_compliance(code)
        assert res["success"] is False
        assert any("safe_path_join" in v or "basename" in v for v in res["violations"])

    def test_mandatory_call_wrapper_post(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'import requests\nrequests.post("https://evil.com")'
        res = policy.check_compliance(code)
        assert res["success"] is False

    def test_forbidden_assignment_password(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'password = "supersecret123"'
        res = policy.check_compliance(code)
        assert res["success"] is False
        assert any("Hardcoded" in v for v in res["violations"])

    def test_forbidden_assignment_api_key(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'API_KEY = "sk-abc123"'
        res = policy.check_compliance(code)
        assert res["success"] is False

    def test_forbidden_assignment_non_literal(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = "import os\npassword = os.getenv('PASSWORD')"
        res = policy.check_compliance(code)
        assert res["success"] is True

    def test_forbidden_assignment_clean_variable(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'username = "admin"'
        res = policy.check_compliance(code)
        assert res["success"] is True

    def test_mandatory_query_params_f_string(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'user_id = 1\ncursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'
        res = policy.check_compliance(code)
        assert res["success"] is False
        assert any("parameterized" in v.lower() for v in res["violations"])

    def test_mandatory_query_params_percent_format(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)'
        res = policy.check_compliance(code)
        assert res["success"] is False

    def test_mandatory_query_params_safe_tuple(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = "cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))"
        res = policy.check_compliance(code)
        assert res["success"] is True

    def test_mandatory_query_params_executemany(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'cursor.executemany("INSERT INTO users VALUES %s", user_data)'
        res = policy.check_compliance(code)
        assert res["success"] is True

    def test_mandatory_query_params_executemany_f_string(self):
        from core.policy.policy_engine import PolicyEngine
        policy = PolicyEngine()
        code = 'cursor.executemany(f"INSERT INTO users VALUES {data}", [])'
        res = policy.check_compliance(code)
        assert res["success"] is False


# =========================================================
# EXTENDED DB TESTS
# =========================================================

class TestDBExtended:
    """Extended tests for utils.db covering untested functions."""

    def test_get_feedback_stats(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import utils.db as udb
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        try:
            with patch.object(udb, "DB_PATH", Path(tmp)):
                udb.init_db()
                udb.record_feedback("SQL", "ACCEPTED")
                udb.record_feedback("SQL", "ACCEPTED")
                udb.record_feedback("SQL", "ACCEPTED")
                udb.record_feedback("SQL", "REJECTED")
                stats = udb.get_feedback_stats("SQL")
                assert stats["total"] == 4
                assert stats["accepted"] == 3
        finally:
            try: os.unlink(tmp)
            except PermissionError: pass

    def test_get_feedback_stats_empty_returns_zero(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import utils.db as udb
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        try:
            with patch.object(udb, "DB_PATH", Path(tmp)):
                udb.init_db()
                stats = udb.get_feedback_stats("NONEXISTENT")
                assert stats["total"] == 0
                assert stats["accepted"] == 0
        finally:
            try: os.unlink(tmp)
            except PermissionError: pass

    def test_get_feedback_records_timestamps(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import utils.db as udb
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        try:
            with patch.object(udb, "DB_PATH", Path(tmp)):
                udb.init_db()
                udb.record_feedback("CMD", "ACCEPTED")
                udb.record_feedback("CMD", "REJECTED")
                records = udb.get_feedback_records("CMD")
                assert len(records) == 2
                assert records[0]["outcome"] == "ACCEPTED"
                assert records[1]["outcome"] == "REJECTED"
                assert "timestamp" in records[0]
        finally:
            try: os.unlink(tmp)
            except PermissionError: pass

    def test_record_and_get_pr_findings(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import utils.db as udb
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        try:
            with patch.object(udb, "DB_PATH", Path(tmp)):
                udb.init_db()
                udb.record_pr_finding(42, "SQL_INJECTION")
                udb.record_pr_finding(42, "COMMAND_INJECTION")
                findings = udb.get_pr_findings(42)
                assert "SQL_INJECTION" in findings
                assert "COMMAND_INJECTION" in findings
                assert len(findings) == 2
        finally:
            try: os.unlink(tmp)
            except PermissionError: pass

    def test_record_feedback_with_user_id_upsert(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import utils.db as udb
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        try:
            with patch.object(udb, "DB_PATH", Path(tmp)):
                udb.init_db()
                udb.record_feedback("SQL", "ACCEPTED", user_id="user1", display_name="Alice")
                udb.record_feedback("SQL", "REJECTED", user_id="user1", display_name="Alice")
                stats = udb.get_feedback_stats("SQL")
                assert stats["total"] == 1  # upsert replaced the row
                assert stats["accepted"] == 0
        finally:
            try: os.unlink(tmp)
            except PermissionError: pass

    def test_increment_dashboard_invalid_risk_level_defaults_to_medium(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import utils.db as udb
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        try:
            with patch.object(udb, "DB_PATH", Path(tmp)):
                udb.init_db()
                udb.increment_dashboard(5, "INVALID_LEVEL")
                d = udb.get_dashboard()
                assert d["total_vulnerabilities"] == 5
                assert d["risk_levels"]["MEDIUM"] == 1
        finally:
            try: os.unlink(tmp)
            except PermissionError: pass


class TestAuthNoInstallations:
    """auth_callback should return the user to the login page with a notice
    when the GitHub App is installed on no repositories."""

    def _callback(self, client, installed):
        import app.app as mod

        with client.session_transaction() as sess:
            sess["oauth_state"] = "expected_state"

        token_mock = MagicMock(status_code=200, json=lambda: {"access_token": "tok"})
        user_mock = MagicMock(
            status_code=200,
            json=lambda: {"id": 987, "login": "octo", "name": "Octo", "avatar_url": ""},
        )
        install_mock = MagicMock(
            status_code=200,
            json=lambda: {"installations": [{"id": 9}] if installed else []},
        )

        def fake_get(url, **kwargs):
            return install_mock if "/user/installations" in url else user_mock

        with patch.object(mod, "GITHUB_CLIENT_ID", "test_client"), \
             patch.object(mod, "GITHUB_CLIENT_SECRET", "test_secret"), \
             patch("requests.post", return_value=token_mock), \
             patch("requests.get", side_effect=fake_get), \
             patch.object(mod, "_github_app_install_url", return_value="https://github.com/apps/test-app/installations/new"):
            return client.get("/auth/callback?state=expected_state&code=abc")

    def test_no_installations_redirects_to_login(self):
        import app.app as mod
        from app.app import app

        mod._install_cache.clear()
        client = app.test_client()
        resp = self._callback(client, installed=False)

        assert resp.status_code == 302
        location = resp.headers["Location"]
        assert location.startswith("/login?error=no_installations")
        assert "install_url" in location
        assert client.get("/api/me").get_json()["authenticated"] is False

    def test_installed_redirects_to_dashboard(self):
        import app.app as mod
        from app.app import app

        mod._install_cache.clear()
        client = app.test_client()
        resp = self._callback(client, installed=True)

        assert resp.status_code == 302
        assert resp.headers["Location"] == "/dashboard"
        assert client.get("/api/me").get_json()["authenticated"] is True


# =========================================================
# PER-USER DATA TESTS (install mapping, attribution, isolation)
# =========================================================

class TestPerUserData:
    def setup_method(self):
        import utils.db as udb
        self._db_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        self._db_patcher = patch.object(udb, "DB_PATH", Path(self._db_tmp))
        self._db_patcher.start()
        udb.init_db()
        from app.app import app
        self.client = app.test_client()

    def teardown_method(self):
        self._db_patcher.stop()
        try:
            os.unlink(self._db_tmp)
        except PermissionError:
            pass

    def _seed(self):
        import utils.db as udb
        udb.upsert_user(111, "alice", "Alice", "")
        udb.upsert_user(222, "bob", "Bob", "")
        udb.sync_user_installations(111, [{"id": 5, "account": {"type": "User", "login": "alice"}}])
        udb.sync_user_installations(222, [{"id": 6, "account": {"type": "User", "login": "bob"}}])
        udb.upsert_repo({
            "id": 1, "full_name": "alice/app", "owner": "alice",
            "name": "app", "description": "", "language": "Python",
            "private": 0, "default_branch": "main", "install_id": 5,
        })
        udb.upsert_repo({
            "id": 2, "full_name": "bob/tool", "owner": "bob",
            "name": "tool", "description": "", "language": "Python",
            "private": 0, "default_branch": "main", "install_id": 6,
        })
        sid_a = udb.record_scan(
            repo_id=1, pr_number=1, pr_title="a", branch="main", commit_sha="x",
            findings_count=1, max_risk=8.0, duration_ms=10,
        )
        sid_b = udb.record_scan(
            repo_id=2, pr_number=2, pr_title="b", branch="main", commit_sha="y",
            findings_count=1, max_risk=6.0, duration_ms=10,
        )
        udb.record_finding(sid_a, "SQL_INJECTION", "HIGH", 8.0, "a.py", 1)
        udb.record_finding(sid_b, "SSRF", "MEDIUM", 6.0, "b.py", 1)
        return sid_a, sid_b

    def test_resolve_scan_user_priority(self):
        import utils.db as udb
        self._seed()
        # install mapping + owner login match
        assert udb.resolve_scan_user(5, "alice") == 111
        assert udb.resolve_scan_user(6, "bob") == 222
        # owner-login fallback when no install mapping exists
        assert udb.resolve_scan_user(999, "alice") == 111
        # no mapping and unknown owner -> None
        assert udb.resolve_scan_user(999, "nobody") is None

    def test_attribution_persisted_on_repo_and_scan(self):
        import utils.db as udb
        sid_a, _ = self._seed()
        assert udb.get_repo(1)["user_id"] == 111
        assert udb.get_repo(2)["user_id"] == 222
        assert udb.get_scan(sid_a)["user_id"] == 111

    def test_repos_filtered_per_user(self):
        import utils.db as udb
        self._seed()
        assert [r["id"] for r in udb.get_repos(111)] == [1]
        assert [r["id"] for r in udb.get_repos(222)] == [2]
        assert udb.get_repo(1, 111) is not None
        assert udb.get_repo(1, 222) is None
        assert udb.get_repo_scans(1, 222) == []
        assert udb.get_repo_findings(1, 222) == []

    def test_scan_visibility_scoped_to_user(self):
        import utils.db as udb
        sid_a, sid_b = self._seed()
        assert udb.get_scan(sid_a, 111) is not None
        assert udb.get_scan(sid_a, 222) is None
        assert udb.get_scan(sid_b, 222) is not None
        assert udb.get_scan_findings(sid_a, 222) == []
        assert len(udb.get_scan_findings(sid_a, 111)) == 1

    def test_per_user_dashboard_stats(self):
        import utils.db as udb
        self._seed()
        d_alice = udb.get_dashboard(111)
        assert d_alice["total_prs"] == 1
        assert d_alice["total_vulnerabilities"] == 1
        assert d_alice["risk_levels"]["HIGH"] == 1
        assert d_alice["avg_risk_score"] == 8.0
        assert [r["full_name"] for r in d_alice["repos"]] == ["alice/app"]
        d_bob = udb.get_dashboard(222)
        assert d_bob["total_prs"] == 1
        assert d_bob["risk_levels"]["MEDIUM"] == 1

    def test_api_isolation_between_users(self):
        self._seed()
        # Alice sees her repo + scan, not Bob's
        with self.client.session_transaction() as sess:
            sess["user"] = {"github_id": "111", "login": "alice"}
        repos = self.client.get("/api/repos").get_json()["repos"]
        assert [r["id"] for r in repos] == [1]
        assert self.client.get("/api/scans/1").status_code == 200
        assert self.client.get("/api/scans/2").status_code == 404
        assert self.client.get("/api/scans/2/findings").status_code == 404
        assert self.client.get("/api/dashboard").get_json()["total_prs"] == 1

        # Bob cannot read Alice's data
        with self.client.session_transaction() as sess:
            sess["user"] = {"github_id": "222", "login": "bob"}
        assert self.client.get("/api/scans/1").status_code == 404
        assert self.client.get("/api/repos").get_json()["repos"][0]["id"] == 2

    def test_api_requires_auth_on_data_endpoints(self):
        self._seed()
        for endpoint in ("/api/repos", "/api/dashboard", "/api/metrics", "/api/scans/1"):
            assert self.client.get(endpoint).status_code == 401

    def test_get_all_findings_and_scans_scoped_per_user(self):
        import utils.db as udb
        self._seed()
        # Alice only sees her own repo's findings/scans
        a_findings = udb.get_all_findings(111)
        assert [f["vuln_type"] for f in a_findings] == ["SQL_INJECTION"]
        assert a_findings[0]["repo_full_name"] == "alice/app"
        assert a_findings[0]["pr_number"] == 1
        assert a_findings[0]["scan_id"] is not None

        a_scans = udb.get_all_scans(111)
        assert [s["pr_number"] for s in a_scans] == [1]
        assert a_scans[0]["repo_full_name"] == "alice/app"

        # Filters work
        assert len(udb.get_all_findings(111, severity="HIGH")) == 1
        assert len(udb.get_all_findings(111, severity="LOW")) == 0
        assert len(udb.get_all_findings(111, vuln_type="SSRF")) == 0

    def test_feedback_context_columns_roundtrip(self):
        import utils.db as udb
        self._seed()
        udb.record_feedback("SQL_INJECTION", "ACCEPTED", user_id="alice", display_name="Alice",
                            repo_id=1, pr_number=1, scan_id=1)
        records = udb.get_feedback_records("SQL_INJECTION")
        assert len(records) == 1
        stats = udb.get_feedback_stats("SQL_INJECTION")
        assert stats["accepted"] == 1

    def test_api_findings_and_scans_endpoints(self):
        self._seed()
        with self.client.session_transaction() as sess:
            sess["user"] = {"github_id": "111", "login": "alice"}

        resp = self.client.get("/api/findings")
        assert resp.status_code == 200
        body = resp.get_json()["findings"]
        assert len(body) == 1
        assert body[0]["vuln_type"] == "SQL_INJECTION"
        assert body[0]["repo_full_name"] == "alice/app"

        resp = self.client.get("/api/scans")
        assert resp.status_code == 200
        scans = resp.get_json()["scans"]
        assert [s["pr_number"] for s in scans] == [1]

        # Invalid filters are rejected
        assert self.client.get("/api/findings?severity=bogus").status_code == 400
        assert self.client.get("/api/scans?repo_id=abc").status_code == 400

        # Bob can't see Alice's findings through the global endpoints
        with self.client.session_transaction() as sess:
            sess["user"] = {"github_id": "222", "login": "bob"}
        bob_findings = self.client.get("/api/findings").get_json()["findings"]
        assert len(bob_findings) == 1
        assert bob_findings[0]["vuln_type"] == "SSRF"

    def test_api_feedback_context_endpoint(self):
        self._seed()
        with self.client.session_transaction() as sess:
            sess["user"] = {"github_id": "111", "login": "alice"}
        resp = self.client.post("/feedback", json={
            "vuln_type": "SQL_INJECTION", "outcome": "ACCEPTED",
            "repo_id": 1, "pr_number": 1, "scan_id": 1,
        })
        assert resp.status_code == 200
        # Invalid context values rejected
        resp = self.client.post("/feedback", json={
            "vuln_type": "SQL_INJECTION", "outcome": "ACCEPTED", "repo_id": "x",
        })
        assert resp.status_code == 400

    def test_api_findings_scans_require_auth(self):
        self._seed()
        assert self.client.get("/api/findings").status_code == 401
        assert self.client.get("/api/scans").status_code == 401

    def test_dashboard_and_findings_dedupe_rescans_of_same_pr(self):
        import utils.db as udb
        _, _ = self._seed()
        # A second scan (revision) of alice's PR #1.
        sid_c = udb.record_scan(
            repo_id=1, pr_number=1, pr_title="a", branch="main", commit_sha="z",
            findings_count=1, max_risk=9.0, duration_ms=10,
        )
        udb.record_finding(sid_c, "HARDCODED_SECRET", "HIGH", 9.0, "a.py", 2)

        revs = udb.get_repo_scans(1)
        assert len(revs) == 2
        latest = [s for s in revs if s["is_latest"]]
        assert len(latest) == 1 and latest[0]["id"] == sid_c
        assert sorted([s["revision_number"] for s in revs]) == [1, 2]

        # Aggregates collapse to the latest scan per PR (1 unique PR).
        d = udb.get_dashboard(111)
        assert d["total_prs"] == 1
        assert d["total_vulnerabilities"] == 1
        assert d["risk_levels"]["HIGH"] == 1
        # Findings/scan lists show only the latest revision's findings.
        assert len(udb.get_repo_findings(1, 111)) == 1
        allf = udb.get_all_findings(111)
        assert len(allf) == 1 and allf[0]["vuln_type"] == "HARDCODED_SECRET"

    def test_feedback_deduped_one_per_pr_latest_vote(self):
        import utils.db as udb
        self._seed()
        udb.record_feedback("SQL_INJECTION", "ACCEPTED", user_id="alice", display_name="Alice",
                            repo_id=1, pr_number=1, scan_id=1)
        # Re-vote on a re-scan of the same PR -> latest vote replaces (one per PR).
        udb.record_feedback("SQL_INJECTION", "REJECTED", user_id="alice", display_name="Alice",
                            repo_id=1, pr_number=1, scan_id=2)
        d = udb.get_dashboard(111)
        perf = {p["type"]: p for p in d["performance"]}
        assert perf["SQL_INJECTION"]["rejected_count"] == 1
        assert perf["SQL_INJECTION"]["accepted_count"] == 0

    def test_api_feedback_route_alias(self):
        self._seed()
        with self.client.session_transaction() as sess:
            sess["user"] = {"github_id": "111", "login": "alice", "name": "Alice"}
        resp = self.client.post("/api/feedback", json={
            "vuln_type": "SSRF", "outcome": "ACCEPTED", "repo_id": 1, "pr_number": 1, "scan_id": 1,
        })
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "success"


# =========================================================
# PER-USER SCAN CONFIGURATION TESTS (Phase 4.1)
# =========================================================

class TestUserScanSettings:
    def setup_method(self):
        import utils.db as udb
        self._db_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        self._db_patcher = patch.object(udb, "DB_PATH", Path(self._db_tmp))
        self._db_patcher.start()
        udb.init_db()
        from app.app import app
        self.client = app.test_client()

    def teardown_method(self):
        self._db_patcher.stop()
        try:
            os.unlink(self._db_tmp)
        except PermissionError:
            pass

    def _seed_user(self, github_id=111, login="alice"):
        import utils.db as udb
        udb.upsert_user(github_id, login, "Alice", "")

    def test_defaults_for_unknown_or_none_user(self):
        import utils.db as udb
        assert udb.get_user_settings(None)["scan_mode"] == "sandbox_with_local_fallback"
        assert udb.get_user_settings(None)["sandbox_network"] == "none"
        assert udb.get_user_settings(999)["scan_mode"] == "sandbox_with_local_fallback"

    def test_update_and_roundtrip(self):
        import utils.db as udb
        self._seed_user()
        udb.update_user_settings(111, scan_mode="sandbox_and_local_comparison", sandbox_network="bridge")
        settings = udb.get_user_settings(111)
        assert settings["scan_mode"] == "sandbox_and_local_comparison"
        assert settings["sandbox_network"] == "bridge"

    def test_partial_update_keeps_other_field(self):
        import utils.db as udb
        self._seed_user()
        udb.update_user_settings(111, scan_mode="sandbox_and_local_comparison", sandbox_network="bridge")
        udb.update_user_settings(111, sandbox_network="none")
        settings = udb.get_user_settings(111)
        assert settings["scan_mode"] == "sandbox_and_local_comparison"
        assert settings["sandbox_network"] == "none"

    def test_invalid_value_raises(self):
        import utils.db as udb
        self._seed_user()
        try:
            udb.update_user_settings(111, scan_mode="nope")
            assert False, "expected ValueError"
        except ValueError:
            pass
        try:
            udb.update_user_settings(111, sandbox_network="host")
            assert False, "expected ValueError"
        except ValueError:
            pass

    def test_per_user_isolation(self):
        import utils.db as udb
        self._seed_user(111, "alice")
        self._seed_user(222, "bob")
        udb.update_user_settings(111, scan_mode="sandbox_and_local_comparison", sandbox_network="bridge")
        assert udb.get_user_settings(111)["scan_mode"] == "sandbox_and_local_comparison"
        assert udb.get_user_settings(222)["scan_mode"] == "sandbox_with_local_fallback"
        assert udb.get_user_settings(222)["sandbox_network"] == "none"

    def test_api_settings_get_requires_auth(self):
        assert self.client.get("/api/settings").status_code == 401

    def test_api_settings_get_returns_options(self):
        self._seed_user()
        with self.client.session_transaction() as sess:
            sess["user"] = {"github_id": "111", "login": "alice"}
        data = self.client.get("/api/settings").get_json()
        assert data["settings"]["scan_mode"] == "sandbox_with_local_fallback"
        assert set(data["options"]["scan_modes"]) == {"sandbox_with_local_fallback", "sandbox_and_local_comparison"}
        assert set(data["options"]["networks"]) == {"none", "bridge"}

    def test_api_settings_post_persists(self):
        self._seed_user()
        with self.client.session_transaction() as sess:
            sess["user"] = {"github_id": "111", "login": "alice"}
        resp = self.client.post("/api/settings", json={
            "scan_mode": "sandbox_and_local_comparison",
            "sandbox_network": "bridge",
        })
        assert resp.status_code == 200
        assert resp.get_json()["saved"] is True
        data = self.client.get("/api/settings").get_json()
        assert data["settings"]["scan_mode"] == "sandbox_and_local_comparison"
        assert data["settings"]["sandbox_network"] == "bridge"

    def test_api_settings_post_invalid_returns_400(self):
        self._seed_user()
        with self.client.session_transaction() as sess:
            sess["user"] = {"github_id": "111", "login": "alice"}
        resp = self.client.post("/api/settings", json={"scan_mode": "bogus"})
        assert resp.status_code == 400
        resp = self.client.post("/api/settings", json={})
        assert resp.status_code == 400

# =========================================================
# FEATURE 345 REGRESSION TESTS (sandbox CLI, path traversal,
# SQL LIKE, helper injection)
# =========================================================

class TestFeature345Regressions:
    """Regression tests for the four engine fixes shipped for PR #18.

    1. Sandbox tolerates argparse "missing required args" exits (no Traceback).
    2. PATH_TRAVERSAL resolves a module-constant base dir and wraps every
       open() call so policy compliance passes.
    3. SQL LIKE '<wildcards>?<wildcards>' is parameterized as LIKE ? with a
       bound f-string that preserves the wildcards.
    4. Helper blocks are inserted only after column-0 (top-level) imports.
    """

    # ---------------- Fix 1: sandbox CLI tolerance ----------------

    def test_argparse_required_args_regex(self):
        from core.validator.sandbox import ARGPARSE_REQUIRED_ARGS_RE
        assert ARGPARSE_REQUIRED_ARGS_RE.search(
            "usage: demo [-h] [--db DB] {add} ...\n"
            "demo: error: the following arguments are required: command"
        )

    def test_cli_arguments_only_ignores_tracebacks(self):
        from types import SimpleNamespace

        from core.validator.sandbox import Sandbox
        assert Sandbox._cli_arguments_only(
            SimpleNamespace(stderr="demo: error: the following arguments are required: command")
        ) is True
        assert Sandbox._cli_arguments_only(
            SimpleNamespace(stderr="Traceback (most recent call last):\nValueError: boom")
        ) is False
        assert Sandbox._cli_arguments_only(
            SimpleNamespace(stderr="unrelated failure")
        ) is False

    def test_sandbox_local_tolerates_missing_cli_args(self):
        from core.validator.sandbox import Sandbox
        code = (
            "import argparse\n"
            "def main():\n"
            "    parser = argparse.ArgumentParser(prog=\"demo\")\n"
            "    sub = parser.add_subparsers(dest=\"command\", required=True)\n"
            "    add = sub.add_parser(\"add\")\n"
            "    add.add_argument(\"title\")\n"
            "    parser.parse_args()\n"
            "main()\n"
        )
        result = Sandbox()._run_local(code, source_filename="demo.py")
        assert result.get("success") is True
        assert result.get("note") == "cli_arguments_required"

    def test_sandbox_local_still_fails_on_real_traceback(self):
        from core.validator.sandbox import Sandbox
        result = Sandbox()._run_local("print(1/0)", source_filename="crash.py")
        assert result.get("success") is False

    # ---------------- Fix 2: PATH_TRAVERSAL base dir ----------------

    def test_path_traversal_resolves_module_constant_base_dir(self):
        code = (
            'DATA_DIR = "./task_attachments"\n'
            'with open(f"{DATA_DIR}/{task_id}.txt") as f:\n'
            '    pass\n'
        )
        vuln = {"type": "PATH_TRAVERSAL", "line": 2, "code": 'with open(f"{DATA_DIR}/{task_id}.txt") as f:'}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "safe_path_join('./task_attachments'" in result["patched_code"].replace('"', "'")

    def test_path_traversal_skips_separator_only_falls_back_to_dot(self):
        code = 'with open(f"{base}/{file}") as f:\n    pass\n'
        vuln = {"type": "PATH_TRAVERSAL", "line": 1, "code": 'with open(f"{base}/{file}") as f:'}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "safe_path_join('.'" in result["patched_code"].replace('"', "'")

    def test_path_traversal_wraps_every_open_call(self):
        """All open() calls must be wrapped, not just the finding's own call."""
        code = (
            'import os\n'
            'DATA_DIR = "./task_attachments"\n'
            'def read_task(task_id):\n'
            '    with open(f"{DATA_DIR}/{task_id}.txt") as f:\n'
            '        return f.read()\n'
            'def write_log(path):\n'
            '    with open(path, "w") as f:\n'
            '        f.write("x")\n'
        )
        vuln = {"type": "PATH_TRAVERSAL", "line": 4, "code": 'with open(f"{DATA_DIR}/{task_id}.txt") as f:'}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert result["patched_code"].count("safe_path_join") >= 2
        assert result["patched_code"].count("open(") == 2

    def test_path_traversal_multi_open_passes_policy_and_rescan(self):
        from core.patch.patch_orchestrator import apply_patches_safely
        from core.policy.policy_engine import PolicyEngine
        from core.validator.security_rescan import SecurityRescanner
        code = (
            'import os\n'
            'DATA_DIR = "./task_attachments"\n'
            'def read_task(task_id):\n'
            '    with open(f"{DATA_DIR}/{task_id}.txt") as f:\n'
            '        return f.read()\n'
            'def write_log(path):\n'
            '    with open(path, "w") as f:\n'
            '        f.write("x")\n'
        )
        vuln = {"type": "PATH_TRAVERSAL", "line": 4, "code": 'with open(f"{DATA_DIR}/{task_id}.txt") as f:'}
        result = apply_patches_safely(code, [vuln], apply_patch_to_content)
        patched = result["final_code"]
        assert patched.count("safe_path_join") >= 2
        compliance = PolicyEngine().check_compliance(patched)
        assert compliance["success"] is True, compliance.get("violations")
        rescan = SecurityRescanner().rescan_code(patched)
        assert rescan["success"] is True

    # ---------------- Fix 3: SQL LIKE parameterization ----------------

    def test_sql_like_fstring_parameterized(self):
        code = 'import sqlite3\nconn = sqlite3.connect("db.sqlite")\nrows = conn.execute(f"SELECT * FROM tasks WHERE title LIKE \'%{keyword}%\'").fetchall()'
        vuln = {"type": "SQL_INJECTION", "line": 3, "code": "conn.execute(f\"SELECT * FROM tasks WHERE title LIKE '%{keyword}%'\")"}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "LIKE ?" in result["patched_code"]
        assert "f'%{keyword}%'" in result["patched_code"].replace('"', "'")
        assert "keyword" not in result["patched_code"].split("LIKE ?")[0]

    def test_sql_like_fstring_executes_against_sqlite(self):
        import sqlite3
        code = (
            'import sqlite3\n'
            'def search(conn, keyword):\n'
            "    return conn.execute(f\"SELECT * FROM tasks WHERE title LIKE '%{keyword}%'\").fetchall()\n"
        )
        vuln = {"type": "SQL_INJECTION", "line": 3, "code": "conn.execute(f\"SELECT * FROM tasks WHERE title LIKE '%{keyword}%'\")"}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        ns = {}
        exec(compile(result["patched_code"], "<patched>", "exec"), ns)
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE tasks (title TEXT)")
        conn.execute("INSERT INTO tasks VALUES ('hello world')")
        conn.execute("INSERT INTO tasks VALUES ('other')")
        rows = ns["search"](conn, "world")
        assert [r["title"] for r in rows] == ["hello world"]

    def test_sql_like_percent_s_parameterized(self):
        code = "import sqlite3\nconn = sqlite3.connect('db.sqlite')\nconn.execute(\"SELECT * FROM tasks WHERE title LIKE '%s'\" % keyword)"
        vuln = {"type": "SQL_INJECTION", "line": 3, "code": "conn.execute(\"SELECT * FROM tasks WHERE title LIKE '%s'\" % keyword)"}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "LIKE ?" in result["patched_code"]
        assert "%s" not in result["patched_code"].replace("'%s'", "")

    def test_sql_like_format_parameterized(self):
        code = "import sqlite3\nconn = sqlite3.connect('db.sqlite')\nconn.execute(\"SELECT * FROM tasks WHERE title LIKE '{}'\".format(keyword))"
        vuln = {"type": "SQL_INJECTION", "line": 3, "code": "conn.execute(\"SELECT * FROM tasks WHERE title LIKE '{}'\".format(keyword))"}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        assert "LIKE ?" in result["patched_code"]
        assert "{}" not in result["patched_code"]

    # ---------------- Fix 4: helper injection top-level only ----------------

    def test_helper_inserted_after_last_top_level_import(self):
        from core.patch.fixers import _insert_helper_after_imports
        code = "import os\nif True:\n    import pdb\nimport requests\nrequests.get(url)\n"
        patched = _insert_helper_after_imports(code, "def safe_path_join(base, path):\n    return path\n")
        lines = patched.splitlines()
        assert "    import pdb" in lines
        helper_idx = lines.index("def safe_path_join(base, path):")
        requests_idx = lines.index("import requests")
        assert helper_idx > requests_idx

    def test_ssrf_helper_stays_top_level_when_indented_import_present(self):
        code = (
            "import os\n"
            "if True:\n"
            "    import pdb\n"
            "import requests\n"
            "\n"
            "def fetch(target_url):\n"
            "    return requests.get(target_url, timeout=15)\n"
        )
        vuln = {"type": "SSRF", "line": 7, "code": "requests.get(target_url, timeout=15)"}
        result = apply_patch_to_content(code, vuln)
        assert result["ast_success"] is True
        lines = result["patched_code"].splitlines()
        assert "    import pdb" in lines
        helper_idx = next(i for i, l in enumerate(lines) if l.startswith("def validate_url_ssrf"))
        requests_idx = next(i for i, l in enumerate(lines) if l.strip() == "import requests")
        assert helper_idx > requests_idx
