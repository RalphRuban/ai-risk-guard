"""
tests/test_sarif.py
Tests for SARIF generation, converter, config, and partial fingerprints.
"""

import json

from core.models.analysis import AnalysisResult
from core.models.risk import RiskAssessment
from core.models.scan import ScanResult
from core.models.vulnerability import Severity, Vulnerability, VulnerabilityType
from core.sarif.converter import (
    build_analysis_result,
    build_analysis_summary,
    findings_to_risk_assessments,
)
from core.sarif.sarif_generator import SARIFGenerator


class TestSARIFGenerator:
    """Tests for SARIFGenerator class."""

    def setup_method(self):
        self.generator = SARIFGenerator()

    def test_generate_empty_analysis(self):
        result = AnalysisResult(
            file_path="test.py",
            scan=ScanResult(success=True, file_path="test.py"),
            risk_assessments=[],
        )
        sarif = self.generator.generate(result)

        assert sarif["version"] == "2.1.0"
        assert "runs" in sarif
        assert len(sarif["runs"]) == 1
        assert sarif["runs"][0]["results"] == []

    def test_generate_with_vulnerability(self):
        vuln = Vulnerability(
            type=VulnerabilityType.COMMAND_INJECTION,
            file="test.py",
            line=10,
            code="os.system(cmd)",
            severity=Severity.HIGH,
            message="Command injection vulnerability",
            cwe="CWE-78",
            owasp="A03:2021",
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

        sarif = self.generator.generate(result)
        results = sarif["runs"][0]["results"]

        assert len(results) == 1
        assert results[0]["ruleId"] == "COMMAND_INJECTION"
        assert results[0]["level"] == "error"
        assert results[0]["properties"]["risk_score"] == 8.5

    def test_generate_json_output(self):
        result = AnalysisResult(
            file_path="test.py",
            scan=ScanResult(success=True, file_path="test.py"),
            risk_assessments=[],
        )
        json_str = self.generator.generate_json(result)

        parsed = json.loads(json_str)
        assert parsed["version"] == "2.1.0"

    def test_severity_mapping(self):
        test_cases = [
            (Severity.HIGH, "error"),
            (Severity.MEDIUM, "warning"),
            (Severity.LOW, "note"),
        ]

        for severity, expected_level in test_cases:
            vuln = Vulnerability(
                type=VulnerabilityType.SQL_INJECTION,
                file="test.py",
                line=1,
                code="test",
                severity=severity,
                message="test",
            )
            assessment = RiskAssessment(
                vulnerability=vuln,
                risk_score=5.0,
                confidence=0.5,
            )
            result = AnalysisResult(
                file_path="test.py",
                scan=ScanResult(success=True, file_path="test.py"),
                risk_assessments=[assessment],
            )

            sarif = self.generator.generate(result)
            assert sarif["runs"][0]["results"][0]["level"] == expected_level

    def test_relativize_path_preserves_relative_path(self):
        result = SARIFGenerator._relativize_path("src/utils/helpers.py")
        assert result == "src/utils/helpers.py"

        result = SARIFGenerator._relativize_path("app.py")
        assert result == "app.py"

    def test_relativize_path_strips_absolute_path(self):
        import os

        result = SARIFGenerator._relativize_path("C:\\Users\\tmp\\test\\demo.py")
        assert result == "demo.py"

        posix_path = "/tmp/test/demo.py"
        expected = "demo.py" if os.path.isabs(posix_path) else posix_path
        assert SARIFGenerator._relativize_path(posix_path) == expected

    def test_relativize_path_preserves_empty_or_unknown(self):
        assert SARIFGenerator._relativize_path("") == ""
        assert SARIFGenerator._relativize_path("unknown") == "unknown"


class TestSARIFConverter:
    """Tests for SARIF converter utilities."""

    def test_findings_to_risk_assessments(self):
        findings = [
            {
                "vulnerability": {
                    "type": "COMMAND_INJECTION",
                    "file": "test.py",
                    "line": 10,
                    "code": "os.system(cmd)",
                    "severity": "HIGH",
                    "message": "Test vulnerability",
                },
                "risk": 8.0,
                "confidence": 0.9,
            }
        ]

        assessments = findings_to_risk_assessments(findings, "test.py")

        assert len(assessments) == 1
        assert assessments[0].risk_score == 8.0
        assert assessments[0].vulnerability.type == "COMMAND_INJECTION"

    def test_build_analysis_summary(self):
        findings = [
            {"risk": 9.0, "vulnerability": {"is_new": True}},
            {"risk": 5.0, "vulnerability": {"is_new": True}},
            {"risk": 2.0, "vulnerability": {"is_new": True}},
        ]

        summary = build_analysis_summary(findings)

        assert summary.total_vulnerabilities == 3
        assert summary.critical_count == 1
        assert summary.moderate_count == 1
        assert summary.low_count == 1
        assert summary.max_risk_score == 9.0

    def test_build_analysis_result(self):
        findings = [
            {
                "vulnerability": {
                    "type": "SQL_INJECTION",
                    "file": "app.py",
                    "line": 5,
                    "code": "execute(query)",
                    "severity": "MEDIUM",
                    "message": "SQL injection",
                },
                "risk": 6.0,
                "confidence": 0.8,
            }
        ]

        result = build_analysis_result(findings, "app.py")

        assert isinstance(result, AnalysisResult)
        assert result.file_path == "app.py"
        assert result.scan.success is True
        assert len(result.risk_assessments) == 1

    def test_empty_findings(self):
        result = build_analysis_result([], "test.py")

        assert result.risk_assessments == []
        assert result.summary.total_vulnerabilities == 0


class TestSARIFConfig:
    """Tests for SARIFConfig model."""

    def test_sarif_config_defaults(self):
        from core.config.app_config import SARIFConfig

        sarif_config = SARIFConfig()
        assert sarif_config.upload_to_code_scanning is True
        assert sarif_config.comment_on_pr is True
        assert sarif_config.update_existing_comment is True

    def test_sarif_config_custom(self):
        from core.config.app_config import SARIFConfig

        sarif_config = SARIFConfig(
            upload_to_code_scanning=False,
            comment_on_pr=False,
        )
        assert sarif_config.upload_to_code_scanning is False
        assert sarif_config.comment_on_pr is False

    def test_sarif_config_in_app_config(self):
        from core.config.app_config import AppConfig

        app_config = AppConfig()
        assert hasattr(app_config, "sarif")
        assert app_config.sarif.upload_to_code_scanning is True

    def test_sarif_config_from_config_registry(self):
        from core.config import config

        assert hasattr(config.app, "sarif")
        assert config.app.sarif.comment_on_pr is True


class TestSARIFPartialFingerprints:
    """Tests for partialFingerprints in SARIF output."""

    def setup_method(self):
        self.generator = SARIFGenerator()

    def test_partial_fingerprints_present(self):
        vuln = Vulnerability(
            type=VulnerabilityType.COMMAND_INJECTION,
            file="test.py",
            line=10,
            code="os.system(cmd)",
            severity=Severity.HIGH,
            message="Command injection vulnerability",
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

        sarif = self.generator.generate(result)
        sarif_result = sarif["runs"][0]["results"][0]

        assert "partialFingerprints" in sarif_result
        assert "primaryLocationLineHash" in sarif_result["partialFingerprints"]
        assert isinstance(sarif_result["partialFingerprints"]["primaryLocationLineHash"], str)
        assert sarif_result["partialFingerprints"]["primaryLocationLineHash"].endswith(":1")
        assert len(sarif_result["partialFingerprints"]["primaryLocationLineHash"]) == 66

    def test_partial_fingerprints_stable(self):
        vuln1 = Vulnerability(
            type=VulnerabilityType.SQL_INJECTION,
            file="app.py",
            line=5,
            code="execute(query)",
            severity=Severity.MEDIUM,
            message="SQL injection",
        )
        vuln2 = Vulnerability(
            type=VulnerabilityType.SQL_INJECTION,
            file="app.py",
            line=5,
            code="execute(query)",
            severity=Severity.MEDIUM,
            message="SQL injection",
        )

        hash1 = self.generator._generate_line_hash(vuln1)
        hash2 = self.generator._generate_line_hash(vuln2)

        assert hash1 == hash2

    def test_partial_fingerprints_different_file(self):
        vuln1 = Vulnerability(
            type=VulnerabilityType.SQL_INJECTION,
            file="app.py",
            line=5,
            code="execute(query)",
            severity=Severity.MEDIUM,
            message="SQL injection",
        )
        vuln2 = Vulnerability(
            type=VulnerabilityType.SQL_INJECTION,
            file="other.py",
            line=5,
            code="execute(query)",
            severity=Severity.MEDIUM,
            message="SQL injection",
        )

        hash1 = self.generator._generate_line_hash(vuln1)
        hash2 = self.generator._generate_line_hash(vuln2)

        assert hash1 != hash2

    def test_existing_fingerprint_untouched(self):
        vuln = Vulnerability(
            type=VulnerabilityType.COMMAND_INJECTION,
            file="test.py",
            line=10,
            code="os.system(cmd)",
            severity=Severity.HIGH,
            message="Test",
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

        sarif = self.generator.generate(result)
        sarif_result = sarif["runs"][0]["results"][0]

        assert "fingerprints" in sarif_result
        assert "ai-risk-guard/vulnerability" in sarif_result["fingerprints"]


class TestReporterSARIF:
    """Tests for reporter SARIF integration."""

    def test_generate_sarif_empty(self):
        from services.github.reporter import generate_sarif

        sarif_json = generate_sarif([], "test.py")
        sarif = json.loads(sarif_json)

        assert sarif["runs"][0]["results"] == []

    def test_generate_sarif_with_findings(self):
        from services.github.reporter import generate_sarif

        findings = [
            {
                "vulnerability": {
                    "type": "COMMAND_INJECTION",
                    "file": "test.py",
                    "line": 10,
                    "code": "os.system(cmd)",
                    "severity": "HIGH",
                    "message": "Test",
                },
                "risk": 8.0,
                "confidence": 0.9,
            }
        ]

        sarif_json = generate_sarif(findings, "test.py")
        sarif = json.loads(sarif_json)

        assert len(sarif["runs"][0]["results"]) == 1


class TestSARIFEnrichment:
    """Tests for the enriched SARIF fields (logicalLocations, codeFlows, run props)."""

    def setup_method(self):
        self.generator = SARIFGenerator()

    def _build_result(self, vuln_kwargs=None):
        vuln_data = {
            "type": VulnerabilityType.COMMAND_INJECTION,
            "file": "test.py",
            "line": 10,
            "code": "os.system(cmd)",
            "severity": Severity.HIGH,
            "message": "Command injection",
            "cwe": "CWE-78",
            "owasp": "A03:2021",
            "function": "run_cmd",
            "context_lines": ["def run_cmd(cmd):", "    os.system(cmd)", "    return"],
        }
        vuln_data.update(vuln_kwargs or {})
        vuln = Vulnerability(**vuln_data)
        assessment = RiskAssessment(
            vulnerability=vuln,
            risk_score=8.5,
            confidence=0.9,
            priority="P1",
            rule_id="CMD001",
            detection_confidence=0.95,
            secret_entropy=3.7,
            remediation="Use subprocess.run with shell=False.",
        )
        result = AnalysisResult(
            file_path="test.py",
            scan=ScanResult(success=True, file_path="test.py"),
            risk_assessments=[assessment],
        )
        return self.generator.generate(result)

    def test_logical_locations_present(self):
        sarif = self._build_result()
        location = sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
        assert location["logicalLocations"] == [{"name": "run_cmd", "kind": "function"}]

    def test_logical_locations_absent_without_function(self):
        sarif = self._build_result({"function": None})
        location = sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
        assert "logicalLocations" not in location

    def test_codeflows_absent(self):
        sarif = self._build_result()
        result = sarif["runs"][0]["results"][0]
        assert "codeFlows" not in result

    def test_result_properties_enriched(self):
        sarif = self._build_result()
        props = sarif["runs"][0]["results"][0]["properties"]
        assert props["rule_id"] == "CMD001"
        assert props["priority"] == "P1"
        assert props["detection_confidence"] == 0.95
        assert props["secret_entropy"] == 3.7
        assert props["recommended_fix"] == "Use subprocess.run with shell=False."

    def test_run_properties_security_score_and_compliance(self):
        sarif = self._build_result()
        props = sarif["runs"][0]["properties"]
        assert "security_score" in props
        assert 0.0 <= props["security_score"] <= 100.0
        assert props["compliance"]["cwe"] == {"CWE-78": 1}
        assert props["rules_version"]

    def test_rule_properties_include_rule_id_and_version(self):
        sarif = self._build_result()
        rule = sarif["runs"][0]["tool"]["driver"]["rules"][0]
        assert rule["properties"]["rule_id"] == "CMD001"
        assert rule["properties"]["rules_version"]

    def test_tool_version_bumped(self):
        sarif = self._build_result()
        assert sarif["runs"][0]["tool"]["driver"]["version"] == "2.1.0"

    def test_information_uri_default(self, monkeypatch):
        monkeypatch.delenv("SARIF_INFORMATION_URI", raising=False)
        sarif = self._build_result()
        uri = sarif["runs"][0]["tool"]["driver"]["informationUri"]
        assert uri == "https://github.com/ralphje/ai-risk-guard"

    def test_information_uri_env_override(self, monkeypatch):
        monkeypatch.setenv("SARIF_INFORMATION_URI", "https://example.com/security")
        sarif = self._build_result()
        uri = sarif["runs"][0]["tool"]["driver"]["informationUri"]
        assert uri == "https://example.com/security"

