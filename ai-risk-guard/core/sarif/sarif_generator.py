"""
core/sarif/sarif_generator.py
Converts AI Risk Guard analysis results to SARIF 2.1.0 format for GitHub Code Scanning.
"""

import hashlib
import json
import os
from datetime import timedelta
from typing import Any

from core.metadata.versions import RULES_VERSION, TOOL_VERSION
from core.metadata.vuln_metadata import RULE_IDS, SECURITY_SEVERITY
from core.models.analysis import AnalysisResult
from core.models.risk import RiskAssessment
from core.models.vulnerability import Severity, Vulnerability, VulnerabilityType
from core.reporting.summary import compliance_counts, compute_security_score

# SARIF severity mapping
SEVERITY_MAP = {
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
}

# Compliance framework tags for each vulnerability type
COMPLIANCE_TAGS_MAP = {
    VulnerabilityType.COMMAND_INJECTION: ["CWE-78", "OWASP:A03:2021", "SOC2:CC6.8", "ISO27001:A.14.2.5", "PCI-DSS:Req 6.5.1"],
    VulnerabilityType.CODE_INJECTION: ["CWE-94", "OWASP:A03:2021", "SOC2:CC6.8", "ISO27001:A.14.2.5", "PCI-DSS:Req 6.5.1"],
    VulnerabilityType.HARDCODED_SECRET: ["CWE-798", "OWASP:A07:2021", "SOC2:CC6.1", "ISO27001:A.9.4.3", "PCI-DSS:Req 8.2.1"],
    VulnerabilityType.INSECURE_DESERIALIZATION: ["CWE-502", "OWASP:A08:2021", "SOC2:CC7.1", "ISO27001:A.12.6.1", "PCI-DSS:Req 6.5.8"],
    VulnerabilityType.SQL_INJECTION: ["CWE-89", "OWASP:A03:2021", "SOC2:CC6.8", "ISO27001:A.14.2.5", "PCI-DSS:Req 6.5.1"],
    VulnerabilityType.PATH_TRAVERSAL: ["CWE-22", "OWASP:A01:2021", "SOC2:CC6.1", "ISO27001:A.9.4.1", "PCI-DSS:Req 6.5.8"],
    VulnerabilityType.SSRF: ["CWE-918", "OWASP:A10:2021", "SOC2:CC6.6", "ISO27001:A.13.1.1", "PCI-DSS:Req 1.3.5"],
    VulnerabilityType.WEAK_CRYPTOGRAPHY: ["CWE-327", "OWASP:A02:2021", "SOC2:CC6.7", "ISO27001:A.10.1.1", "PCI-DSS:Req 4.1"],
}

# CWE IDs for each vulnerability type
CWE_MAP = {
    VulnerabilityType.COMMAND_INJECTION: "CWE-78",
    VulnerabilityType.CODE_INJECTION: "CWE-94",
    VulnerabilityType.HARDCODED_SECRET: "CWE-798",
    VulnerabilityType.INSECURE_DESERIALIZATION: "CWE-502",
    VulnerabilityType.SQL_INJECTION: "CWE-89",
    VulnerabilityType.PATH_TRAVERSAL: "CWE-22",
    VulnerabilityType.SSRF: "CWE-918",
    VulnerabilityType.WEAK_CRYPTOGRAPHY: "CWE-327",
}

# OWASP mappings
OWASP_MAP = {
    VulnerabilityType.COMMAND_INJECTION: "A03:2021",
    VulnerabilityType.CODE_INJECTION: "A03:2021",
    VulnerabilityType.HARDCODED_SECRET: "A07:2021",
    VulnerabilityType.INSECURE_DESERIALIZATION: "A08:2021",
    VulnerabilityType.SQL_INJECTION: "A03:2021",
    VulnerabilityType.PATH_TRAVERSAL: "A01:2021",
    VulnerabilityType.SSRF: "A10:2021",
    VulnerabilityType.WEAK_CRYPTOGRAPHY: "A02:2021",
}

# Security severity scores for GitHub Code Scanning (CVSS-like 0.0-10.0).
# Sourced from core.metadata.vuln_metadata so the SARIF display and the
# PR comment dashboard classify severity identically.
SECURITY_SEVERITY_MAP = {
    vt: f"{SECURITY_SEVERITY[vt.value]:.1f}"
    for vt in VulnerabilityType
    if vt.value in SECURITY_SEVERITY
}

# Default SARIF notification level for each vulnerability type
DEFAULT_LEVEL_MAP = {
    VulnerabilityType.COMMAND_INJECTION: "error",
    VulnerabilityType.CODE_INJECTION: "error",
    VulnerabilityType.HARDCODED_SECRET: "error",
    VulnerabilityType.INSECURE_DESERIALIZATION: "error",
    VulnerabilityType.SQL_INJECTION: "error",
    VulnerabilityType.PATH_TRAVERSAL: "warning",
    VulnerabilityType.SSRF: "warning",
    VulnerabilityType.WEAK_CRYPTOGRAPHY: "warning",
    VulnerabilityType.TLS_VERIFICATION_DISABLED: "warning",
    VulnerabilityType.DEBUG_CODE: "note",
}

# Help text descriptions for each vulnerability type
HELP_TEXT_MAP = {
    VulnerabilityType.COMMAND_INJECTION: (
        "User-controlled input is passed to a shell command execution function. "
        "An attacker can inject arbitrary commands by crafting malicious input. "
        "Use subprocess.run with shell=False or shlex.quote() to sanitize input."
    ),
    VulnerabilityType.CODE_INJECTION: (
        "User-controlled input is evaluated as code (eval, exec, compile). "
        "An attacker can execute arbitrary Python code. "
        "Avoid dynamic code evaluation; use safer alternatives like ast.literal_eval."
    ),
    VulnerabilityType.HARDCODED_SECRET: (
        "A cryptographic key, API token, or password is hardcoded in source code. "
        "Anyone with access to the repository can extract the secret. "
        "Move secrets to environment variables or a secrets manager."
    ),
    VulnerabilityType.INSECURE_DESERIALIZATION: (
        "Untrusted data is deserialized with pickle or similar libraries. "
        "An attacker can execute arbitrary code during deserialization. "
        "Use a safe serialization format like JSON instead."
    ),
    VulnerabilityType.SQL_INJECTION: (
        "User input is concatenated directly into a SQL query string. "
        "An attacker can manipulate the query to read/modify data. "
        "Use parameterized queries (cursor.execute with ? placeholders)."
    ),
    VulnerabilityType.PATH_TRAVERSAL: (
        "User input is used to construct a file path without sanitization. "
        "An attacker can read/write files outside the intended directory. "
        "Use os.path.basename to sanitize input and restrict to allowed paths."
    ),
    VulnerabilityType.SSRF: (
        "User-controlled input is used as a URL for server-side requests. "
        "An attacker can make the server access internal resources. "
        "Validate the URL against an allowlist of permitted hosts/schemes."
    ),
    VulnerabilityType.WEAK_CRYPTOGRAPHY: (
        "A weak or deprecated cryptographic algorithm is used (e.g., MD5, SHA1). "
        "These algorithms are vulnerable to collision and preimage attacks. "
        "Use a strong algorithm like SHA-256, SHA-3, or bcrypt."
    ),
    VulnerabilityType.TLS_VERIFICATION_DISABLED: (
        "TLS certificate verification is disabled on an HTTP request (verify=False). "
        "An attacker can intercept or modify traffic via a man-in-the-middle attack. "
        "Remove verify=False, or supply an explicit CA bundle via verify=path."
    ),
    VulnerabilityType.DEBUG_CODE: (
        "A debugger or breakpoint is left in the code (breakpoint, pdb.set_trace). "
        "This can halt production processes or expose interactive shells. "
        "Remove debugger calls and use logging for runtime diagnostics."
    ),
}

HELP_MARKDOWN_MAP = {
    VulnerabilityType.COMMAND_INJECTION: (
        "**Remediation**\n\n"
        "Replace `os.system()` / `subprocess.run(shell=True)` with "
        "`subprocess.run(shlex.split(user_input), shell=False)`. "
        "This prevents shell injection by passing arguments as a list."
    ),
    VulnerabilityType.CODE_INJECTION: (
        "**Remediation**\n\n"
        "Replace `eval()` / `exec()` with `ast.literal_eval()` if you need to evaluate "
        "literal expressions. For dynamic execution, use a sandboxed environment."
    ),
    VulnerabilityType.HARDCODED_SECRET: (
        "**Remediation**\n\n"
        "Replace the hardcoded secret with `os.getenv('VARIABLE_NAME')`. "
        "Add the secret to GitHub Secrets or a vault service."
    ),
    VulnerabilityType.INSECURE_DESERIALIZATION: (
        "**Remediation**\n\n"
        "Replace `pickle.loads(data)` with `json.loads(data)`. "
        "If you must use pickle, verify the data source with HMAC signing."
    ),
    VulnerabilityType.SQL_INJECTION: (
        "**Remediation**\n\n"
        "Replace f-string interpolation with parameterized queries: "
        "`cursor.execute('SELECT * FROM users WHERE name = ?', (username,))`"
    ),
    VulnerabilityType.PATH_TRAVERSAL: (
        "**Remediation**\n\n"
        "Sanitize the filename with `os.path.basename(filename)` and "
        "validate against an allowlist of permitted directories."
    ),
    VulnerabilityType.SSRF: (
        "**Remediation**\n\n"
        "Validate the URL against an allowlist of permitted hosts: "
        "parse with `urlparse()`, reject internal IPs/localhost, "
        "and restrict to allowed schemes (http/https only)."
    ),
    VulnerabilityType.WEAK_CRYPTOGRAPHY: (
        "**Remediation**\n\n"
        "Replace `hashlib.md5()` with `hashlib.sha256()` or `hashlib.sha3_256()`. "
        "For password hashing, use `bcrypt` or `argon2-cffi`."
    ),
    VulnerabilityType.TLS_VERIFICATION_DISABLED: (
        "**Remediation**\n\n"
        "Remove `verify=False` from the request call. For self-signed certs, "
        "pass the exact CA bundle instead: `requests.get(url, verify='/path/to/ca.pem')`."
    ),
    VulnerabilityType.DEBUG_CODE: (
        "**Remediation**\n\n"
        "Remove `breakpoint()` and `pdb.set_trace()` calls before merging. "
        "Prefer structured logging for runtime diagnostics."
    ),
}


class SARIFGenerator:
    """
    Generates SARIF 2.1.0 compliant output from AI Risk Guard analysis results.
    """

    def __init__(self, tool_name: str = "ai-risk-guard", tool_version: str = TOOL_VERSION):
        self.tool_name = tool_name
        self.tool_version = tool_version

    def generate(self, analysis_result: AnalysisResult, commit_sha: str | None = None) -> dict[str, Any]:
        """
        Convert an AnalysisResult to SARIF 2.1.0 format.
        
        Args:
            analysis_result: The complete analysis result from the pipeline
            commit_sha: Optional commit SHA for unique runAutomationDetails.id
            
        Returns:
            SARIF 2.1.0 compliant dictionary
        """
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [self._build_run(analysis_result, commit_sha)]
        }
        return sarif

    def generate_json(self, analysis_result: AnalysisResult, commit_sha: str | None = None) -> str:
        """
        Generate SARIF output as a JSON string.
        
        Args:
            analysis_result: The complete analysis result from the pipeline
            commit_sha: Optional commit SHA for unique runAutomationDetails.id
            
        Returns:
            Pretty-printed SARIF JSON string
        """
        return json.dumps(self.generate(analysis_result, commit_sha), indent=2)

    def _build_run(self, analysis_result: AnalysisResult, commit_sha: str | None = None) -> dict[str, Any]:
        """Build a SARIF run object."""
        run_id = "ai-risk-guard"
        if commit_sha:
            run_id = f"ai-risk-guard/{commit_sha[:8]}"
        run = {
            "tool": self._build_tool(),
            "name": {"text": "AI Risk Guard Scan"},
            "runAutomationDetails": {
                "id": run_id
            },
            "artifacts": self._build_artifacts(analysis_result),
            "results": self._build_results(analysis_result),
            "properties": self._build_run_properties(analysis_result),
        }
        
        # Add invocations if we have timing info
        invocation = self._build_invocation(analysis_result)
        if invocation:
            run["invocations"] = [invocation]
            
        return run

    def _build_run_properties(self, analysis_result: AnalysisResult) -> dict[str, Any]:
        """Run-level metadata: security score and compliance aggregates."""
        findings = [
            {
                "vulnerability": {
                    "cwe": a.vulnerability.cwe,
                    "owasp": a.vulnerability.owasp,
                },
                "risk": a.risk_score,
                "risk_breakdown": a.risk_breakdown,
                "validation": {"policy_violations": a.policy_violations},
            }
            for a in analysis_result.risk_assessments
        ]
        return {
            "security_score": compute_security_score(findings),
            "compliance": compliance_counts(findings),
            "rules_version": RULES_VERSION,
        }

    def _build_tool(self) -> dict[str, Any]:
        """Build the tool information."""
        return {
            "driver": {
                "name": self.tool_name,
                "version": self.tool_version,
                "semanticVersion": self.tool_version,
                "informationUri": "https://github.com/ralphje/ai-risk-guard",
                "rules": self._build_rules()
            }
        }

    def _build_rules(self) -> list[dict[str, Any]]:
        """Build rule definitions for each vulnerability type."""
        rules = []
        for vuln_type in VulnerabilityType:
            cwe = CWE_MAP.get(vuln_type)
            cwe_id = cwe.split("-")[1] if cwe else "0"
            rule: dict[str, Any] = {
                "id": vuln_type.value,
                "name": vuln_type.value.replace("_", " ").title(),
                "shortDescription": {
                    "text": f"Security vulnerability: {vuln_type.value}"
                },
                "fullDescription": {
                    "text": f"Detected {vuln_type.value} vulnerability by AI Risk Guard"
                },
                "defaultConfiguration": {
                    "level": DEFAULT_LEVEL_MAP.get(vuln_type, "warning"),
                },
                "help": {
                    "text": HELP_TEXT_MAP.get(vuln_type, "Security vulnerability detected by AI Risk Guard."),
                    "markdown": HELP_MARKDOWN_MAP.get(vuln_type, "**Security vulnerability** detected by AI Risk Guard."),
                },
                "helpUri": f"https://cwe.mitre.org/data/definitions/{cwe_id}.html",
                "properties": {
                    "tags": ["security", "ai-risk-guard"],
                    "precision": "high",
                    "security-severity": SECURITY_SEVERITY_MAP.get(vuln_type, "7.0"),
                    "owasp": OWASP_MAP.get(vuln_type, "A00:2021"),
                    "rule_id": RULE_IDS.get(vuln_type.value, vuln_type.value),
                    "rules_version": RULES_VERSION,
                }
            }

            if cwe:
                rule["properties"]["cwe"] = cwe

            rules.append(rule)
        return rules

    def _build_artifacts(self, analysis_result: AnalysisResult) -> list[dict[str, Any]]:
        """Build artifact list (files scanned)."""
        artifacts = []
        seen_files = set()
        
        # Add the main scanned file
        file_path = analysis_result.file_path
        rel_path = self._relativize_path(file_path)
        if rel_path not in seen_files:
            artifacts.append({
                "location": {
                    "uri": rel_path,
                },
                "mimeType": "text/plain"
            })
            seen_files.add(rel_path)
            
        # Add any additional files from vulnerabilities
        for assessment in analysis_result.risk_assessments:
            vuln_file = self._relativize_path(assessment.vulnerability.file)
            if vuln_file not in seen_files:
                artifacts.append({
                    "location": {
                        "uri": vuln_file,
                    },
                    "mimeType": "text/plain"
                })
                seen_files.add(vuln_file)
                
        return artifacts

    def _build_results(self, analysis_result: AnalysisResult) -> list[dict[str, Any]]:
        """Build SARIF results from risk assessments."""
        results = []
        
        for assessment in analysis_result.risk_assessments:
            result = self._build_result(assessment, analysis_result.file_path)
            results.append(result)
            
        return results

    def _build_result(self, assessment: RiskAssessment, main_file: str) -> dict[str, Any]:
        """Build a single SARIF result from a risk assessment."""
        vuln = assessment.vulnerability
        
        # Generate unique fingerprint for deduplication
        fingerprint = self._generate_fingerprint(vuln)
        
        # Compute ruleIndex from vulnerability type value string
        rule_index = 0
        if isinstance(vuln.type, str):
            for i, t in enumerate(VulnerabilityType):
                if t.value == vuln.type:
                    rule_index = i
                    break
        
        physical_location = {
            "artifactLocation": {
                "uri": self._relativize_path(vuln.file),
            },
            "region": {
                "startLine": vuln.line,
                "startColumn": 1,
                "endLine": vuln.line,
                "endColumn": max(2, 1 + len(vuln.code))
            }
        }

        if vuln.function:
            physical_location["logicalLocations"] = [
                {"name": vuln.function, "kind": "function"}
            ]

        # Build the result
        result: dict[str, Any] = {
            "ruleId": vuln.type,
            "ruleIndex": rule_index,
            "level": SEVERITY_MAP.get(vuln.severity, "warning"),
            "message": {
                "text": f"{vuln.type} vulnerability detected (risk: {assessment.risk_score}/10)",
                "markdown": self._build_markdown_message(assessment)
            },
            "locations": [{
                "physicalLocation": physical_location
            }],
            "fingerprints": {
                "ai-risk-guard/vulnerability": fingerprint
            },
            "partialFingerprints": {
                "primaryLocationLineHash": self._generate_line_hash(vuln)
            },
            "baselineState": "new" if vuln.is_new else "existing",
            "properties": {
                "risk_score": assessment.risk_score,
                "confidence": assessment.confidence,
                "severity": vuln.severity,
                "is_new": vuln.is_new,
                "cwe": vuln.cwe or CWE_MAP.get(vuln.type, "N/A"),
                "owasp": vuln.owasp or OWASP_MAP.get(vuln.type, "N/A"),
                "tags": ["security"] + COMPLIANCE_TAGS_MAP.get(vuln.type, []),
            }
        }

        # Add risk/fix/priority enrichment properties
        if assessment.rule_id:
            result["properties"]["rule_id"] = assessment.rule_id
        if assessment.priority:
            result["properties"]["priority"] = assessment.priority
        if assessment.detection_confidence is not None:
            result["properties"]["detection_confidence"] = assessment.detection_confidence
        if assessment.secret_entropy is not None:
            result["properties"]["secret_entropy"] = assessment.secret_entropy
        if assessment.remediation:
            result["properties"]["recommended_fix"] = assessment.remediation

        # Add fix guidance if available
        if assessment.risk_breakdown:
            result["properties"]["risk_breakdown"] = {
                k: {"value": v.value, "weight": v.weight}
                for k, v in assessment.risk_breakdown.items()
            }

        return result

    def _build_markdown_message(self, assessment: RiskAssessment) -> str:
        """Build a rich markdown message for the result."""
        vuln = assessment.vulnerability
        lines = [
            f"**{vuln.type}** vulnerability detected",
            "",
            f"**Risk Score**: {assessment.risk_score}/10",
            f"**Confidence**: {assessment.confidence * 100:.1f}%",
            f"**Severity**: {vuln.severity}",
            "",
            f"**CWE**: {vuln.cwe or CWE_MAP.get(vuln.type, 'N/A')}",
            f"**OWASP**: {vuln.owasp or OWASP_MAP.get(vuln.type, 'N/A')}",
        ]
        
        if assessment.policy_violations:
            lines.extend([
                "",
                "**Policy Violations**:",
                *[f"- {v}" for v in assessment.policy_violations]
            ])
            
        return "\n".join(lines)

    def _generate_fingerprint(self, vuln: Vulnerability) -> str:
        """Generate a unique fingerprint for deduplication."""
        raw = f"{vuln.type}:{vuln.file}:{vuln.line}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _generate_line_hash(self, vuln: Vulnerability) -> str:
        """Generate a stable line hash for GitHub Code Scanning deduplication.

        Uses rule + file + line (not code content) so the same vulnerability
        produces the same hash across scans, enabling GitHub to deduplicate.
        GitHub expects format: <sha256>:<index> where <index> disambiguates
        identical hashes on different lines of the same file.
        """
        raw = f"{vuln.type}:{vuln.file}:{vuln.line}"
        return f"{hashlib.sha256(raw.encode()).hexdigest()}:1"

    @staticmethod
    def _relativize_path(path: str) -> str:
        """Convert absolute file paths to repo-relative paths for SARIF.

        GitHub Code Scanning requires artifact URIs to be relative to the
        repository root. Absolute temp paths like
        'C:\\Users\\...\\tmpxxx\\demo.py' must be converted to 'demo.py'.
        Paths that are already relative (e.g. 'src/utils/helpers.py') are
        preserved to avoid collisions between files in different directories.
        """
        if not path or path == "unknown":
            return path
        # Preserve relative paths (e.g. 'src/utils/helpers.py')
        if os.path.isabs(path):
            return os.path.basename(path)
        return path

    def _build_invocation(self, analysis_result: AnalysisResult) -> dict[str, Any] | None:
        """Build invocation metadata if available."""
        if not analysis_result.analyzed_at:
            return None
        
        inv = {
            "executionSuccessful": analysis_result.summary.passed_all_stages,
            "startTimeUtc": analysis_result.analyzed_at.isoformat(),
            "tool": {
                "name": self.tool_name,
                "version": self.tool_version
            }
        }
        if analysis_result.scan_duration_seconds > 0:
            inv["endTimeUtc"] = (
                analysis_result.analyzed_at + timedelta(seconds=analysis_result.scan_duration_seconds)
            ).isoformat()
            inv["properties"] = {
                "scan_duration_seconds": analysis_result.scan_duration_seconds
            }
        return inv
