"""
tests/test_reporter.py
Tests for report formatting and scan number extraction.
"""


from services.github.reporter import (
    _risk_bar,
    extract_targeted_hunks,
    format_report,
)


def _rich_finding():
    return {
        "vulnerability": {
            "type": "COMMAND_INJECTION",
            "file": "src/server.py",
            "line": 10,
            "code": "os.system(cmd)",
            "severity": "HIGH",
            "cwe": "CWE-78",
            "owasp": "A03:2021",
            "is_new": True,
            "function": "run_cmd",
            "context_lines": ["def run_cmd(cmd):", "    os.system(cmd)", "    return"],
        },
        "risk": 8.5,
        "confidence": 0.9,
        "rule_id": "CMD001",
        "priority": "P1",
        "detection_confidence": 0.95,
        "remediation": "Use subprocess.run with shell=False.",
        "risk_rationale": "User input flows to shell execution.",
        "evidence": {"rule": "Rule: os.system() with shell", "code": "os.system(cmd)", "line": 10},
        "risk_breakdown": {
            "severity": {"value": 1.0, "weight": 0.22, "contribution": 0.22, "level": "Critical"},
            "validation": {"value": 1.0, "weight": 0.16, "contribution": 0.16, "level": "Unverified"},
        },
        "validation": {
            "success": True,
            "score": 0.9,
            "policy_violations": [],
            "details": {
                "syntax": {"success": True},
                "sandbox": {"success": True},
                "rescan": {"success": True},
                "policy": {"success": True},
            },
            "test_results": {"success": True, "mode": "docker", "output": "3 passed"},
        },
        "quality_score": 0.96,
        "quality_breakdown": {"total": 0.96},
        "patch": "subprocess.run(cmd, shell=False)",
        "diff": "--- a/src/server.py\n+++ b/src/server.py\n@@ -10 +10 @@\n-os.system(cmd)\n+subprocess.run(cmd, shell=False)",
        "candidate_id": "c1",
        "candidate_source": "deterministic_ast",
    }


class TestReportFormatting:
    """Tests for format_report."""

    def test_format_report_empty_findings(self):
        report = format_report([], scan_number=1)
        assert "No vulnerabilities detected" in report
        assert "<!-- ai-risk-guard -->" in report

    def test_format_report_includes_scan_id(self):
        report = format_report([], scan_number=42)
        assert "scan:42" in report

    def test_format_report_with_findings_has_table(self):
        findings = [
            {
                "vulnerability": {
                    "type": "COMMAND_INJECTION",
                    "file": "src/server.py",
                    "line": 10,
                    "severity": "HIGH",
                },
                "risk": 8.5,
            }
        ]

        report = format_report(findings, scan_number=1)

        assert "Command Injection" in report
        assert "8.5" in report
        assert "CRITICAL" in report

    def test_format_report_includes_summary(self):
        findings = [
            {
                "vulnerability": {
                    "type": "SQL_INJECTION",
                    "file": "db.py",
                    "line": 5,
                    "severity": "MEDIUM",
                },
                "risk": 6.0,
            }
        ]

        report = format_report(findings, scan_number=1)

        assert "📊" in report
        assert "SQL Injection" in report

    def test_format_report_orders_by_risk_when_priority_unknown(self):
        findings = [
            {
                "vulnerability": {
                    "type": "SQL_INJECTION",
                    "file": "src/db.py",
                    "line": 5,
                    "severity": "MEDIUM",
                },
                "risk": 6.0,
            },
            {
                "vulnerability": {
                    "type": "COMMAND_INJECTION",
                    "file": "src/server.py",
                    "line": 10,
                    "severity": "HIGH",
                },
                "risk": 8.5,
            },
        ]

        report = format_report(findings, scan_number=1)

        assert report.index("Command Injection") < report.index("SQL Injection")

    def test_format_report_uses_risk_label(self):
        findings = [
            {
                "vulnerability": {
                    "type": "SQL_INJECTION",
                    "file": "db.py",
                    "line": 5,
                    "severity": "MEDIUM",
                },
                "risk": 6.0,
            }
        ]

        report = format_report(findings, scan_number=1)

        assert "6.0" in report

    def test_format_report_legacy_findings(self):
        findings = [
            {
                "vulnerability": {
                    "type": "HARDCODED_SECRET",
                    "file": "config.py",
                    "line": 5,
                    "severity": "HIGH",
                    "is_new": False,
                },
                "risk": 9.0,
            }
        ]

        report = format_report(findings, scan_number=1)

        assert "legacy" in report.lower()

    def test_format_report_with_diffs(self):
        findings = [
            {
                "vulnerability": {
                    "type": "COMMAND_INJECTION",
                    "file": "src/server.py",
                    "line": 10,
                    "severity": "HIGH",
                },
                "risk": 8.5,
                "diff": "--- a/src/server.py\n+++ b/src/server.py\n@@ -10 +10 @@\n-os.system(cmd)\n+subprocess.run(cmd, shell=False)",
            }
        ]

        report = format_report(findings, scan_number=1)

        assert "Patch & Validation" in report or "🧠" in report

    def test_format_report_starts_with_html_comment(self):
        report = format_report([], scan_number=1)
        assert report.startswith("<!--")

    def test_format_report_contains_timestamp(self):
        report = format_report([], scan_number=1)
        assert "UTC" in report

    def test_format_report_rate_limited_banner_empty(self):
        report = format_report([], scan_number=1, rate_limited=True)
        assert "AI Rate Limit" in report
        assert "rate limit reached (429)" in report
        assert "No vulnerabilities detected" in report

    def test_format_report_rate_limited_banner_with_findings(self):
        findings = [
            {
                "vulnerability": {
                    "type": "SQL_INJECTION",
                    "file": "db.py",
                    "line": 5,
                    "severity": "MEDIUM",
                },
                "risk": 6.0,
            }
        ]
        report = format_report(findings, scan_number=1, rate_limited=True)
        assert "AI Rate Limit" in report
        assert "Retries exhausted" in report
        assert "SQL Injection" in report

    def test_format_report_not_rate_limited_no_banner(self):
        report = format_report([], scan_number=1, rate_limited=False)
        assert "AI Rate Limit" not in report
        assert "Retries exhausted" not in report

    def test_format_report_ends_with_bot_marker(self):
        findings = [
            {
                "vulnerability": {
                    "type": "SQL_INJECTION",
                    "file": "db.py",
                    "line": 5,
                    "severity": "MEDIUM",
                },
                "risk": 6.0,
            }
        ]

        report = format_report(findings, scan_number=1)

        assert report.rstrip().endswith("<!-- ai-risk-guard -->")


    def test_format_report_docker_unavailable_note(self):
        findings = [
            {
                "vulnerability": {
                    "type": "COMMAND_INJECTION",
                    "file": "src/server.py",
                    "line": 10,
                    "severity": "HIGH",
                },
                "risk": 8.5,
                "validation": {
                    "success": True,
                    "score": 0.8,
                    "details": {
                        "syntax": {"success": True},
                        "sandbox": {"success": True},
                        "rescan": {"success": True},
                        "policy": {"success": True},
                    },
                    "test_results": {
                        "success": True,
                        "mode": "local",
                        "docker_unavailable": True,
                    },
                },
            }
        ]
        report = format_report(findings, scan_number=1)
        assert "Docker unavailable" in report
        assert "tests ran locally" in report

    def test_format_report_local_fallback_docker_fail_local_pass(self):
        findings = [
            {
                "vulnerability": {
                    "type": "COMMAND_INJECTION",
                    "file": "src/server.py",
                    "line": 10,
                    "severity": "HIGH",
                },
                "risk": 8.5,
                "validation": {
                    "success": False,
                    "score": 0.5,
                    "details": {
                        "syntax": {"success": True},
                        "sandbox": {"success": True},
                        "rescan": {"success": True},
                        "policy": {"success": True},
                    },
                    "test_results": {
                        "success": False,
                        "mode": "docker",
                        "local_fallback": {"success": True},
                    },
                },
            }
        ]
        report = format_report(findings, scan_number=1)
        assert "Docker: ❌ failed" in report
        assert "Local fallback: ✅ passed" in report
        assert "Fix works outside sandbox" in report

    def test_format_report_local_fallback_both_fail(self):
        findings = [
            {
                "vulnerability": {
                    "type": "COMMAND_INJECTION",
                    "file": "src/server.py",
                    "line": 10,
                    "severity": "HIGH",
                },
                "risk": 8.5,
                "validation": {
                    "success": False,
                    "score": 0.5,
                    "details": {
                        "syntax": {"success": True},
                        "sandbox": {"success": True},
                        "rescan": {"success": True},
                        "policy": {"success": True},
                    },
                    "test_results": {
                        "success": False,
                        "mode": "docker",
                        "local_fallback": {"success": False},
                    },
                },
            }
        ]
        report = format_report(findings, scan_number=1)
        assert "Docker: ❌ failed" in report
        assert "Local fallback: ❌ failed" in report
        assert "Both environments failed" in report

    def test_finding_card_renders_expected_failures(self):
        findings = [
            {
                "vulnerability": {
                    "type": "COMMAND_INJECTION",
                    "file": "src/server.py",
                    "line": 10,
                    "severity": "HIGH",
                },
                "risk": 8.5,
                "validation": {
                    "success": True,
                    "score": 1.0,
                    "details": {
                        "syntax": {"success": True},
                        "sandbox": {"success": True},
                        "rescan": {"success": True},
                        "policy": {"success": True},
                    },
                    "test_results": {
                        "success": True,
                        "mode": "docker",
                        "output": (
                            "demo1_test.py::test_secret_exists FAILED\n"
                            "demo1_test.py::test_fetch_url FAILED\n"
                            "demo1_test.py::test_hash_content FAILED\n"
                            "demo1_test.py::test_save_results FAILED\n"
                            "demo1_test.py::test_run_diagnostics FAILED\n"
                            "demo1_test.py::test_extract_title PASSED\n"
                            "demo1_test.py::test_extract_title_no_match PASSED\n"
                            "demo1_test.py::test_extract_links PASSED\n"
                            "demo1_test.py::test_export_json PASSED\n"
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
                    },
                },
            }
        ]
        report = format_report(findings, scan_number=1)
        assert "4 passed, 5 expected, 0 skipped" in report
        assert "pin the removed vulnerabilities" in report
        assert "not regressions" in report
        assert "✅ No regressions" in report
        assert "Both environments failed" not in report
        assert "fix may be incomplete" not in report

    def test_finding_card_keeps_fail_messaging_when_regressions_remain(self):
        findings = [
            {
                "vulnerability": {
                    "type": "COMMAND_INJECTION",
                    "file": "src/server.py",
                    "line": 10,
                    "severity": "HIGH",
                },
                "risk": 8.5,
                "validation": {
                    "success": False,
                    "score": 0.5,
                    "details": {
                        "syntax": {"success": True},
                        "sandbox": {"success": True},
                        "rescan": {"success": True},
                        "policy": {"success": True},
                    },
                    "test_results": {
                        "success": False,
                        "mode": "docker",
                        "output": "demo1_test.py::test_unrelated FAILED\n4 passed, 1 failed in 0.9s\n",
                        "expected_failures": [],
                        "regression_failures": ["test_unrelated"],
                        "local_fallback": {"success": False},
                    },
                },
            }
        ]
        report = format_report(findings, scan_number=1)
        assert "Docker: ❌ failed" in report
        assert "Local fallback: ❌ failed" in report
        assert "Both environments failed" in report
        assert "fix may be incomplete" in report
        assert "✅ No regressions" not in report

    def test_format_report_local_fallback_both_pass(self):
        findings = [
            {
                "vulnerability": {
                    "type": "COMMAND_INJECTION",
                    "file": "src/server.py",
                    "line": 10,
                    "severity": "HIGH",
                },
                "risk": 8.5,
                "validation": {
                    "success": True,
                    "score": 0.9,
                    "details": {
                        "syntax": {"success": True},
                        "sandbox": {"success": True},
                        "rescan": {"success": True},
                        "policy": {"success": True},
                    },
                    "test_results": {
                        "success": True,
                        "mode": "docker",
                        "local_fallback": {"success": True},
                    },
                },
            }
        ]
        report = format_report(findings, scan_number=1)
        assert "Docker: ✅ passed" in report
        assert "Local fallback: ✅ passed" in report

    def test_format_report_dedicated_env_comparison_section(self):
        findings = [
            {
                "vulnerability": {"type": "COMMAND_INJECTION", "file": "src/server.py", "line": 10, "severity": "HIGH"},
                "rule_id": "CMD001",
                "risk": 8.5,
                "validation": {
                    "success": False,
                    "score": 0.5,
                    "details": {"sandbox": {"success": True}},
                    "test_results": {
                        "success": False,
                        "mode": "docker",
                        "local_fallback": {"success": True},
                    },
                },
                "diff": "--- a/src/server.py\n+++ b/src/server.py\n@@ -10 +10 @@\n-os.system(cmd)\n+subprocess.run(cmd, shell=False)",
            },
            {
                "vulnerability": {"type": "HARDCODED_SECRET", "file": "src/config.py", "line": 4, "severity": "HIGH"},
                "rule_id": "SECRET001",
                "risk": 7.0,
                "validation": {
                    "success": True,
                    "score": 0.8,
                    "test_results": {
                        "success": True,
                        "mode": "docker",
                        "local_fallback": {"success": True},
                    },
                },
                "diff": "--- a/src/config.py\n+++ b/src/config.py\n@@ -4 +4 @@\n-PASSWORD = \"sup3rs3cr3t\"\n+PASSWORD = os.environ[\"PASSWORD\"]",
            },
        ]
        report = format_report(findings, scan_number=1, scan_mode="sandbox_and_local_comparison")
        assert "🧪 Environment Comparison" in report
        assert "| Rule | Docker | Local | Patch |" in report
        assert "CMD001" in report
        assert "SECRET001" in report
        assert "✅ passed" in report

    def test_format_report_env_comparison_docker_unavailable(self):
        findings = [
            {
                "vulnerability": {"type": "COMMAND_INJECTION", "file": "src/server.py", "line": 10, "severity": "HIGH"},
                "rule_id": "CMD001",
                "risk": 8.5,
                "validation": {
                    "test_results": {
                        "success": True,
                        "mode": "local",
                        "docker_unavailable": True,
                    },
                },
                "diff": "--- a/src/server.py\n+++ b/src/server.py\n@@ -10 +10 @@\n-os.system()\n+subprocess.run(cmd, shell=False)",
            }
        ]
        report = format_report(findings, scan_number=1, scan_mode="sandbox_and_local_comparison")
        assert "🧪 Environment Comparison" in report
        assert "⚠️ unavailable" in report
        assert "Docker engine unavailable" in report

    def test_finding_card_suppressed_patch_still_renders(self):
        findings = [
            {
                "vulnerability": {"type": "COMMAND_INJECTION", "file": "src/server.py", "line": 10, "severity": "HIGH"},
                "rule_id": "CMD001",
                "risk": 8.5,
                "validation": {
                    "success": False,
                    "score": 0.3,
                    "details": {"sandbox": {"success": False}},
                    "test_results": {"success": False, "mode": "docker"},
                },
                "patch_suppressed": True,
                "suppression_score": 0.0,
                "patch": "",
                "diff": "",
            }
        ]
        report = format_report(findings, scan_number=1, scan_mode="sandbox_and_local_comparison")
        assert "Patch suppressed" in report
        assert "score too low" in report.lower()
        assert "🧪 Environment Comparison" in report
        assert "🧩 suppressed" in report

    def test_finding_card_renders_mocked_env_substitutions(self):
        findings = [
            {
                "vulnerability": {"type": "HARDCODED_SECRET", "file": "src/server.py", "line": 1, "severity": "HIGH"},
                "rule_id": "SEC001",
                "risk": 8.5,
                "validation": {
                    "success": False,
                    "score": 0.45,
                    "details": {"sandbox": {"success": True}},
                    "test_results": {
                        "success": False,
                        "mode": "docker",
                        "mocked_env_vars": ["API_TOKEN", "API_KEY"],
                    },
                },
                "patch_suppressed": False,
                "diff": "--- a/src/server.py\n+++ b/src/server.py\n-API_TOKEN = \"tok\"\n+API_TOKEN = os.getenv(\"API_TOKEN\")\n",
                "quality_score": 0.5,
            }
        ]
        report = format_report(findings, scan_number=1, scan_mode="sandbox_and_local_comparison")
        assert "Sandbox mocked env vars: API_TOKEN, API_KEY" in report
        assert "tests asserting the original values fail on substitution" in report

    def test_format_report_env_comparison_absent_default_mode(self):
        findings = [
            {
                "vulnerability": {"type": "COMMAND_INJECTION", "file": "src/server.py", "line": 10, "severity": "HIGH"},
                "rule_id": "CMD001",
                "risk": 8.5,
                "validation": {
                    "test_results": {
                        "success": False,
                        "mode": "docker",
                        "local_fallback": {"success": True},
                    },
                },
                "diff": "--- a/src/server.py\n+++ b/src/server.py\n@@ -10 +10 @@\n-os.system(cmd)\n+subprocess.run(cmd, shell=False)",
            }
        ]
        report = format_report(findings, scan_number=1)
        assert "🧪 Environment Comparison" not in report

    def test_format_report_env_comparison_uses_per_finding_rule_id(self):
        """Each env-comparison row must show its own rule_id, not a stale shared one."""
        findings = [
            {
                "vulnerability": {"type": "COMMAND_INJECTION", "file": "src/a.py", "line": 1, "severity": "HIGH"},
                "rule_id": "CMD001",
                "risk": 8.5,
                "validation": {
                    "test_results": {
                        "success": False,
                        "mode": "docker",
                        "local_fallback": {"success": False},
                    },
                },
                "diff": "--- a/src/a.py\n+++ b/src/a.py\n@@ -1 +1 @@\n-a\n+b",
            },
            {
                "vulnerability": {"type": "SSRF", "file": "src/b.py", "line": 1, "severity": "HIGH"},
                "rule_id": "SSRF001",
                "risk": 8.5,
                "validation": {
                    "test_results": {
                        "success": False,
                        "mode": "docker",
                        "local_fallback": {"success": False},
                    },
                },
                "diff": "--- a/src/b.py\n+++ b/src/b.py\n@@ -1 +1 @@\n-a\n+b",
            },
            {
                "vulnerability": {"type": "WEAK_CRYPTOGRAPHY", "file": "src/c.py", "line": 1, "severity": "MEDIUM"},
                "rule_id": "CRYPTO001",
                "risk": 5.0,
                "validation": {
                    "test_results": {
                        "success": False,
                        "mode": "docker",
                        "local_fallback": {"success": False},
                    },
                },
                "diff": "--- a/src/c.py\n+++ b/src/c.py\n@@ -1 +1 @@\n-a\n+b",
            },
        ]
        report = format_report(findings, scan_number=1, scan_mode="sandbox_and_local_comparison")
        for rule_id in ("CMD001", "SSRF001", "CRYPTO001"):
            assert f"`{rule_id}`" in report, f"expected rule {rule_id} to appear in env comparison"
        assert "CMD001 Hardcoded Secret" not in report
        assert "SSRF001 Hardcoded Secret" not in report

    def test_format_report_shared_patch_note_when_candidate_shared(self):
        """Findings sharing a candidate should render a 'shared across' note."""
        findings = [
            {
                "vulnerability": {"type": "COMMAND_INJECTION", "file": "src/a.py", "line": 1, "severity": "HIGH", "is_new": True},
                "rule_id": "CMD001",
                "risk": 8.5,
                "candidate_id": "llm_variant_1",
                "quality_score": 0.47,
                "validation": {
                    "success": False,
                    "score": 0.3,
                    "test_results": {"success": False, "mode": "docker"},
                },
                "diff": "--- a/src/a.py\n+++ b/src/a.py\n@@ -1 +1 @@\n-a\n+b",
            },
            {
                "vulnerability": {"type": "SSRF", "file": "src/a.py", "line": 5, "severity": "HIGH", "is_new": True},
                "rule_id": "SSRF001",
                "risk": 8.5,
                "candidate_id": "llm_variant_1",
                "quality_score": 0.47,
                "validation": {
                    "success": False,
                    "score": 0.3,
                    "test_results": {"success": False, "mode": "docker"},
                },
                "diff": "--- a/src/a.py\n+++ b/src/a.py\n@@ -1 +1 @@\n-a\n+b",
            },
        ]
        report = format_report(findings, scan_number=1)
        assert "shared across 2 findings" in report

    def test_format_report_no_shared_note_when_candidates_distinct(self):
        """Findings with distinct candidates must not render the shared note."""
        findings = [
            {
                "vulnerability": {"type": "COMMAND_INJECTION", "file": "src/a.py", "line": 1, "severity": "HIGH", "is_new": True},
                "rule_id": "CMD001",
                "risk": 8.5,
                "candidate_id": "cand_1",
                "quality_score": 0.9,
                "validation": {"success": True, "score": 0.9, "test_results": {"success": True, "mode": "docker"}},
                "diff": "--- a/src/a.py\n+++ b/src/a.py\n@@ -1 +1 @@\n-a\n+b",
            },
            {
                "vulnerability": {"type": "SSRF", "file": "src/b.py", "line": 5, "severity": "HIGH", "is_new": True},
                "rule_id": "SSRF001",
                "risk": 8.5,
                "candidate_id": "cand_2",
                "quality_score": 0.9,
                "validation": {"success": True, "score": 0.9, "test_results": {"success": True, "mode": "docker"}},
                "diff": "--- a/src/b.py\n+++ b/src/b.py\n@@ -1 +1 @@\n-a\n+b",
            },
        ]
        report = format_report(findings, scan_number=1)
        assert "shared across" not in report


class TestRiskBar:
    """Tests for _risk_bar."""

    def test_risk_bar_eight(self):
        bar = _risk_bar(8.5)
        assert bar == "█" * 8 + "░" * 2

    def test_risk_bar_five(self):
        bar = _risk_bar(5.0)
        assert bar == "█" * 5 + "░" * 5

    def test_risk_bar_two(self):
        bar = _risk_bar(2.0)
        assert bar == "█" * 2 + "░" * 8

    def test_risk_bar_0_all_empty(self):
        bar = _risk_bar(0.0)
        assert bar == "░" * 10

    def test_risk_bar_10_all_filled(self):
        bar = _risk_bar(10.0)
        assert bar == "█" * 10
        assert "░" not in bar

    def test_risk_bar_midpoints(self):
        bar4 = _risk_bar(4.0)
        assert bar4.count("█") == 4

        bar7 = _risk_bar(7.0)
        assert bar7.count("█") == 7

    def test_risk_bar_clamps(self):
        assert _risk_bar(-5) == "░" * 10
        assert _risk_bar(15) == "█" * 10

    def test_risk_bar_threshold_boundaries(self):
        assert _risk_bar(6.9).count("█") == 7
        assert _risk_bar(7.0).count("█") == 7
        assert _risk_bar(8.9).count("█") == 9  # round(8.9) = 9
        assert _risk_bar(9.0).count("█") == 9
        assert _risk_bar(3.9).count("█") == 4
        assert _risk_bar(4.0).count("█") == 4


class TestEnrichedComment:
    """Tests for the enterprise-grade comment enrichment."""

    def test_executive_summary_has_security_score(self):
        report = format_report([_rich_finding()], scan_number=1)
        assert "Dashboard" in report
        assert "Security Score" in report
        assert "/100" in report

    def test_finding_card_has_evidence_and_rule_id(self):
        report = format_report([_rich_finding()], scan_number=1)
        assert "Evidence" in report
        assert "CMD001" in report

    def test_finding_card_has_priority(self):
        report = format_report([_rich_finding()], scan_number=1)
        assert "Priority" in report
        assert "P1" in report

    def test_finding_card_omits_code_context(self):
        report = format_report([_rich_finding()], scan_number=1)
        assert "Code context" not in report
        assert "def run_cmd(cmd)" not in report

    def test_finding_card_has_risk_breakdown(self):
        report = format_report([_rich_finding()], scan_number=1)
        assert "Risk breakdown" in report
        assert "Severity" in report

    def test_finding_card_has_patch_evaluation(self):
        report = format_report([_rich_finding()], scan_number=1)
        assert "Patch evaluation" in report
        assert "Syntax (PASS)" in report
        assert "Patch quality **0.96**" in report

    def test_finding_card_has_test_counts(self):
        report = format_report([_rich_finding()], scan_number=1)
        assert "3 passed" in report

    def test_finding_card_shows_image_unavailable_note(self):
        finding = _rich_finding()
        finding["validation"]["test_results"] = {
            "success": False, "mode": "local", "skipped": False, "image_unavailable": True,
        }
        report = format_report([finding], scan_number=1)
        assert "Docker sandbox image not available" in report
        assert "docker build -f sandbox/Dockerfile.sandbox" in report

    def test_finding_card_shows_image_unavailable_from_sandbox(self):
        finding = _rich_finding()
        finding["validation"]["details"]["sandbox"] = {"success": False, "image_unavailable": True}
        finding["validation"]["test_results"] = {
            "success": False, "mode": "local", "skipped": False,
        }
        report = format_report([finding], scan_number=1)
        assert "Docker sandbox image not available" in report

    def test_finding_card_suppresses_regression_expected_when_infra_unavailable(self):
        finding = _rich_finding()
        finding["validation"]["test_results"] = {
            "success": False, "mode": "local", "skipped": False, "image_unavailable": True,
        }
        report = format_report([finding], scan_number=1)
        assert "Regression test failure expected" not in report

    def test_finding_card_shows_docker_unavailable_note(self):
        finding = _rich_finding()
        finding["validation"]["test_results"] = {
            "success": False, "mode": "local", "skipped": False, "docker_unavailable": True,
        }
        report = format_report([finding], scan_number=1)
        assert "Docker unavailable" in report

    def test_finding_card_summary_line_has_no_bold_asterisks(self):
        finding = _rich_finding()
        report = format_report([finding], scan_number=1)
        assert "| Risk 8.5/10 | Priority P1" in report
        assert "Risk **8.5/10**" not in report

    def test_finding_card_summary_line_uses_human_name(self):
        finding = _rich_finding()
        report = format_report([finding], scan_number=1)
        assert "<b>💉 Command Injection</b>" in report
        assert "Injection <sub><code>COMMAND_INJECTION</code></sub>" not in report

    def test_finding_title_has_no_index_number(self):
        finding = _rich_finding()
        report = format_report([finding], scan_number=1)
        assert "<sub>#1</sub>" not in report
        assert "<sub>#1" not in report
        assert "<b>💉 Command Injection</b>" in report

    def test_finding_card_shows_error_count(self):
        finding = _rich_finding()
        finding["validation"]["test_results"] = {
            "success": False, "mode": "docker", "skipped": False,
            "output": "1 error in 0.5s",
            "error": "tests/demo.py:1: in <module>\nModuleNotFoundError: No module named 'tests'",
        }
        report = format_report([finding], scan_number=1)
        assert "1 error, 0 skipped" in report
        assert "Tests could not run" in report

    def test_finding_card_shows_collection_error_reason(self):
        finding = _rich_finding()
        finding["validation"]["test_results"] = {
            "success": False, "mode": "docker", "skipped": False,
            "output": "0 passed, 0 failed, 0 skipped in 0.5s",
            "error": "tests/demo.py:1: in <module>\n    from tests.demo import compute\nModuleNotFoundError: No module named 'tests'",
        }
        report = format_report([finding], scan_number=1)
        assert "Tests could not run — ModuleNotFoundError: No module named 'tests'" in report
        assert "Regression test failure expected" not in report

    def test_finding_card_shows_collection_error_from_stdout(self):
        finding = _rich_finding()
        finding["validation"]["test_results"] = {
            "success": False, "mode": "docker", "skipped": False,
            "output": "tests/demo.py:2: in <module>\nImportError: cannot import name 'demo' from 'tests'\n\n1 error in 0.5s",
            "error": "hypothesis/_settings.py:78: HypothesisWarning: ...",
        }
        report = format_report([finding], scan_number=1)
        assert "Tests could not run — ImportError: cannot import name 'demo' from 'tests'" in report

    def test_finding_card_shows_skip_reason(self):
        finding = _rich_finding()
        finding["validation"]["test_results"] = {
            "success": False, "mode": "docker", "skipped": True,
            "error": "test imports from tests.demo which does not match the patched module",
        }
        report = format_report([finding], scan_number=1)
        assert "Regression tests skipped — test imports from tests.demo which does not match the patched module" in report

    def test_finding_card_suppresses_skip_reason_for_default_no_test_file(self):
        finding = _rich_finding()
        finding["validation"]["test_results"] = {
            "success": False, "mode": "docker", "skipped": True, "error": "No test file",
        }
        report = format_report([finding], scan_number=1)
        assert "Regression tests skipped" not in report

    def test_finding_card_shows_rebind_note(self):
        finding = _rich_finding()
        finding["validation"]["test_results"] = {
            "success": True, "mode": "docker", "output": "2 passed",
            "rebind": {"rebound": True, "rebound_map": {"tests.demo": "demo1"}},
        }
        report = format_report([finding], scan_number=1)
        assert "Test imports rebound to patched module (tests.demo → demo1)" in report

    def test_finding_card_status_line_has_colons(self):
        finding = _rich_finding()
        report = format_report([finding], scan_number=1)
        assert "**Patch confidence**: 90%" in report
        assert "**Detection**: 95%" in report
        assert "**Priority**: P1" in report
        assert "**Policy**: 🟢 Compliant" in report

    def test_footer_carries_pipeline_metadata(self):
        report = format_report([_rich_finding()], scan_number=1)
        assert "Scan Metadata" not in report
        assert "Rules version" not in report
        assert "ai-risk-guard" in report
        assert "2.1.0" in report
        assert "Rules **2026.08**" in report
        assert "PR diff / AST + Regex" in report
        assert "Docker sandbox + local fallback" in report

    def test_compliance_section(self):
        report = format_report([_rich_finding()], scan_number=1)
        assert "Compliance" in report
        assert "CWE-78" in report
        assert "OWASP Top 10" in report

    def test_trend_section_with_previous_scan(self):
        previous = {"findings_count": 3, "max_risk": 7.0, "scanned_at": "2026-07-30"}
        report = format_report([_rich_finding()], scan_number=2, previous_scan_summary=previous)
        assert "Repository Trend" in report
        assert "3" in report

    def test_no_trend_without_previous_scan(self):
        report = format_report([_rich_finding()], scan_number=1)
        assert "Repository Trend" not in report

    def test_empty_report_has_footer_metadata(self):
        report = format_report([], scan_number=1)
        assert "PR diff / AST + Regex" in report
        assert "Docker sandbox + local fallback" in report
        assert "No vulnerabilities detected" in report

    def _finding(self, vuln_type, risk, severity, priority, line=1, file="src/server.py"):
        return {
            "vulnerability": {
                "type": vuln_type,
                "file": file,
                "line": line,
                "code": "x",
                "severity": severity,
                "cwe": "CWE-78",
                "owasp": "A03:2021",
                "is_new": True,
            },
            "risk": risk,
            "confidence": 0.9,
            "priority": priority,
        }

    def test_findings_ordered_priority_then_severity(self):
        findings = [
            self._finding("COMMAND_INJECTION", 5.0, "MEDIUM", "P2", line=1),
            self._finding("SSRF", 9.5, "HIGH", "P1", line=2),
            self._finding("SQL_INJECTION", 8.0, "HIGH", "P1", line=3),
            self._finding("PATH_TRAVERSAL", 4.5, "LOW", "P3", line=4),
            self._finding("CODE_INJECTION", 7.5, "MEDIUM", "P1", line=5),
        ]
        report = format_report(findings, scan_number=1)
        orders = []
        for t in ["Server-Side Request Forgery", "SQL Injection", "Code Injection", "Command Injection", "Path Traversal"]:
            orders.append(report.index(t))
        assert orders == sorted(orders), f"expected P1 group then P2 then P3, got {orders}"

    def test_findings_ordered_priority_then_severity_critical_first(self):
        findings = [
            self._finding("SQL_INJECTION", 9.6, "HIGH", "P1", line=1),
            self._finding("SSRF", 9.5, "HIGH", "P1", line=2),
            self._finding("CODE_INJECTION", 8.0, "HIGH", "P1", line=3),
        ]
        report = format_report(findings, scan_number=1)
        assert report.index("SQL Injection") < report.index("Server-Side Request Forgery") < report.index("Code Injection")

    def test_findings_header_shows_count(self):
        report = format_report([_rich_finding(), _rich_finding()], scan_number=1)
        assert "Findings (2)" in report

    def test_finding_numbering_absent(self):
        report = format_report([_rich_finding(), _rich_finding()], scan_number=1)
        assert "#1" not in report
        assert "#2" not in report

    def test_finding_card_has_risk_bar(self):
        report = format_report([_rich_finding()], scan_number=1)
        assert "**Risk**:" in report
        assert "█" in report

    def test_critical_risk_uses_critical_emoji(self):
        finding = self._finding("SQL_INJECTION", 9.0, "HIGH", "P1", line=2)
        report = format_report([finding], scan_number=1)
        assert "⛔" in report


class TestDashboardLayout:
    """Tests for the production dashboard-style PR comment."""

    def _finding(self, vuln_type, risk, severity, priority, line=1, file="src/server.py", cwe="CWE-78", is_new=True):
        return {
            "vulnerability": {
                "type": vuln_type,
                "file": file,
                "line": line,
                "code": "x",
                "severity": severity,
                "cwe": cwe,
                "owasp": "A03:2021",
                "is_new": is_new,
            },
            "risk": risk,
            "confidence": 0.9,
            "priority": priority,
        }

    def test_header_card_fields(self):
        report = format_report(
            [], scan_number=15, repo_name="owner/repo", pr_number=17,
            commit_sha="a18f32c2f9d6b0e8c4f5a1b2c3d4e5f6a7b8c9d0", action="COMMENT",
        )
        assert "AI RISK GUARD" in report
        assert "| owner/repo | 17 |" in report
        assert "| Repository | Pull Request | Status |" in report
        assert "| Commit |" not in report
        assert "`a18f32c`" not in report
        assert "✅ **COMMENT**" in report
        assert "Scan 15" in report

    def test_header_plain_text_no_links(self):
        report = format_report(
            [], scan_number=1, repo_name="owner/repo", pr_number=17, action="COMMENT",
        )
        assert "[owner/repo]" not in report
        assert "[#17]" not in report

    def test_header_status_request_changes(self):
        report = format_report([], scan_number=1, action="REQUEST_CHANGES")
        assert "❌ **REQUEST_CHANGES**" in report

    def test_header_status_derived_when_action_missing(self):
        findings = [self._finding("SSRF", 9.5, "HIGH", "P1")]
        report = format_report(findings, scan_number=1)
        assert "**REQUEST_CHANGES**" in report or "**COMMENT**" in report

    def test_kpi_severity_counts(self):
        findings = [
            self._finding("SSRF", 9.5, "HIGH", "P1"),
            self._finding("SQL_INJECTION", 8.0, "HIGH", "P1"),
            self._finding("COMMAND_INJECTION", 8.2, "HIGH", "P1"),
            self._finding("PATH_TRAVERSAL", 6.0, "MEDIUM", "P2"),
            self._finding("CODE_INJECTION", 2.0, "LOW", "P3"),
        ]
        report = format_report(findings, scan_number=1, scan_duration=121.0)
        assert "| **3** | **2** | **0** | **0** | **121s** |" in report

    def test_security_health_bar(self):
        report = format_report([_rich_finding()], scan_number=1)
        assert "**Security Score**" in report
        assert "/100" in report
        assert "Max risk" in report
        assert "█" in report

    def test_max_risk_badge_matches_finding_severity(self):
        finding = _rich_finding()
        assert finding["risk"] == 8.5
        report = format_report([finding], scan_number=1)
        assert "Max risk**: ⛔ CRITICAL 8.5/10" in report

    def test_patch_table_uses_patch_quality_label(self):
        finding = _rich_finding()
        report = format_report([finding], scan_number=1)
        assert "| Patch Engine | Language | Patch quality | Fixes |" in report
        assert "Patch quality 96%" in report
        assert "Confidence 96%" not in report

    def test_decision_banner_request_changes(self):
        findings = [self._finding("SSRF", 9.5, "HIGH", "P1")]
        report = format_report(findings, scan_number=1, action="REQUEST_CHANGES")
        assert "❌ **REQUEST CHANGES**" in report
        assert "1 vulnerability must be resolved" in report

    def test_decision_banner_comment(self):
        findings = [self._finding("SSRF", 6.0, "MEDIUM", "P2")]
        report = format_report(findings, scan_number=1, action="COMMENT")
        assert "✅ **COMMENT**" in report
        assert "1 finding needs review" in report

    def test_silent_finding_shows_informational_banner(self):
        findings = [
            self._finding("TLS_VERIFICATION_DISABLED", 6.0, "MEDIUM", "P2", is_new=True)
        ]
        findings[0]["is_silent"] = True
        report = format_report(findings, scan_number=1)
        assert "informational finding" in report
        assert "TLS Verification Disabled" in report
        assert "❌ **REQUEST CHANGES**" not in report

    def test_silent_and_actionable_mixed_banner_counts_actionable(self):
        findings = [
            self._finding("SQL_INJECTION", 3.0, "MEDIUM", "P2", is_new=True),
            self._finding("DEBUG_CODE", 2.0, "LOW", "P3", is_new=True),
        ]
        findings[1]["is_silent"] = True
        report = format_report(findings, scan_number=1)
        assert "1 finding needs review" in report
        assert "SQL Injection" in report
        assert "Debug Code" in report

    def test_icon_mapping_present(self):
        findings = [self._finding("COMMAND_INJECTION", 8.5, "HIGH", "P1")]
        report = format_report(findings, scan_number=1)
        assert "💉 Command Injection" in report
        assert "<code>COMMAND_INJECTION</code>" not in report

    def test_footer_has_version_duration_checks(self):
        findings = [self._finding("SQL_INJECTION", 6.0, "MEDIUM", "P2")]
        report = format_report(findings, scan_number=1, repo_name="owner/repo", pr_number=17, scan_duration=121.0)
        assert "ai-risk-guard" in report
        assert "v2.1.0" in report
        assert "Generated in **121s**" in report
        assert "✅ Check:" in report
        assert "🚀" in report

    def test_empty_report_shows_dashboard_and_footer(self):
        report = format_report([], scan_number=1, scan_duration=5.0)
        assert "## 📊 Dashboard" in report
        assert "Security Score" in report
        assert "No vulnerabilities detected" in report
        assert "Generated in **5s**" in report

    def test_legacy_note_in_findings_header(self):
        findings = [
            self._finding("SQL_INJECTION", 6.0, "MEDIUM", "P2", is_new=True),
            self._finding("HARDCODED_SECRET", 9.0, "HIGH", "P1", file="config.py", is_new=False),
        ]
        report = format_report(findings, scan_number=1)
        assert "Findings (1)" in report
        assert "1 legacy finding" in report


def test_extract_targeted_hunks_keeps_import_insertion():
    diff = (
        "@@ -1,3 +1,4 @@\n"
        " import subprocess\n"
        " import hashlib\n"
        "+import shlex\n"
        "@@ -10,1 +11,1 @@\n"
        "-os.system(cmd)\n"
        "+subprocess.run(shlex.split(cmd), shell=False)\n"
    )
    findings = [{"type": "COMMAND_INJECTION", "line": 10}]
    out = extract_targeted_hunks(diff, findings)
    assert "+import shlex" in out
    assert "+subprocess.run(shlex.split(cmd), shell=False)" in out


def test_extract_targeted_hunks_returns_full_diff_when_no_findings():
    diff = "@@ -1,1 +1,1 @@\n-a\n+b\n"
    out = extract_targeted_hunks(diff, [])
    assert out == diff


