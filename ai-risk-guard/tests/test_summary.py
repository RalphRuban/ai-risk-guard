"""
tests/test_summary.py
Tests for core/reporting/summary.py pure helper functions.
"""

from core.reporting.summary import (
    compliance_counts,
    compute_priority,
    compute_security_score,
    extract_secret_value,
    parse_test_summary,
    patch_evaluation,
    risk_factor_label,
    shannon_entropy,
)


class TestSecurityScore:
    def test_empty_results_full_score(self):
        assert compute_security_score([]) == 100.0

    def test_zero_risk_full_score(self):
        results = [{"risk": 0.0, "risk_breakdown": {}}]
        assert compute_security_score(results) == 100.0

    def test_high_risk_lowers_score(self):
        results = [
            {
                "risk": 10.0,
                "risk_breakdown": {
                    "severity": {"value": 1.0, "weight": 0.22},
                    "type": {"value": 1.0, "weight": 0.14},
                    "validation": {"value": 1.0, "weight": 0.16},
                    "confidence": {"value": 1.0, "weight": 0.12},
                    "complexity": {"value": 1.0, "weight": 0.0},
                    "sensitivity": {"value": 1.0, "weight": 0.12},
                    "exposure": {"value": 1.0, "weight": 0.12},
                    "quality": {"value": 1.0, "weight": 0.12},
                }
            }
        ]
        assert compute_security_score(results) == 0.0

    def test_clamped_negative(self):
        results = [
            {
                "risk": 8.5,
                "risk_breakdown": {
                    "severity": {"value": 1.0, "weight": 0.22},
                },
            }
        ]
        score = compute_security_score(results)
        assert 0.0 <= score <= 100.0

    def test_falls_back_to_risk_when_no_breakdown(self):
        results = [{"risk": 5.0, "risk_breakdown": {}}]
        score = compute_security_score(results)
        assert score == 50.0

    def test_handles_riskfactor_objects(self):
        class FakeFactor:
            def __init__(self, value):
                self.value = value

        results = [
            {
                "risk": 8.5,
                "risk_breakdown": {
                    "severity": FakeFactor(1.0),
                    "validation": FakeFactor(0.2),
                },
            }
        ]
        score = compute_security_score(results)
        assert 0.0 <= score <= 100.0


class TestPriority:
    def test_p1_high_risk(self):
        assert compute_priority(9.0) == "P1"

    def test_p1_at_max_allowed_threshold(self):
        assert compute_priority(8.5, severity="HIGH") == "P1"

    def test_severity_does_not_force_p1(self):
        assert compute_priority(2.0, severity="HIGH") == "P3"

    def test_p2_medium_risk(self):
        assert compute_priority(5.0, severity="LOW") == "P2"

    def test_p3_low_risk(self):
        assert compute_priority(1.0, severity="LOW") == "P3"


class TestEntropy:
    def test_high_entropy_random_secret(self):
        entropy = shannon_entropy("x9Kf2!qLm3#vR8")
        assert entropy > 3.0

    def test_low_entropy_placeholder(self):
        entropy = shannon_entropy("aaa")
        assert entropy == 0.0

    def test_empty_string(self):
        assert shannon_entropy("") == 0.0
        assert shannon_entropy(None) == 0.0

    def test_extract_secret_value(self):
        assert extract_secret_value('password = "sup3rs3cr3t"') == "sup3rs3cr3t"
        assert extract_secret_value("API_KEY = 'abcd1234'") == "abcd1234"
        assert extract_secret_value("no secret here") is None


class TestTestParser:
    def test_parses_counts(self):
        result = parse_test_summary("3 passed, 1 failed, 2 skipped in 0.5s")
        assert result["passed"] == 3
        assert result["failed"] == 1
        assert result["skipped"] == 2

    def test_none_on_empty(self):
        assert parse_test_summary("") is None
        assert parse_test_summary(None) is None

    def test_none_on_unrecognized(self):
        assert parse_test_summary("some random output") is None


class TestCompliance:
    def test_aggregates_counts(self):
        results = [
            {
                "vulnerability": {"cwe": "CWE-78", "owasp": "A03:2021"},
                "validation": {"policy_violations": []},
            },
            {
                "vulnerability": {"cwe": "CWE-78", "owasp": "A03:2021"},
                "validation": {"policy_violations": ["Forbidden import"]},
            },
            {
                "vulnerability": {"cwe": "CWE-798", "owasp": "A07:2021"},
                "validation": {"policy_violations": []},
            },
        ]
        counts = compliance_counts(results)
        assert counts["cwe"] == {"CWE-78": 2, "CWE-798": 1}
        assert counts["owasp"] == {"A03:2021": 2, "A07:2021": 1}
        assert counts["policy_violations"] == ["Forbidden import"]
        assert counts["policy_pass"] is False

    def test_empty(self):
        counts = compliance_counts([])
        assert counts["cwe"] == {}
        assert counts["owasp"] == {}
        assert counts["policy_pass"] is True


class TestPatchEvaluation:
    def test_all_pass(self):
        r = {
            "validation": {
                "details": {
                    "syntax": {"success": True},
                    "rescan": {"success": True},
                    "sandbox": {"success": True},
                    "policy": {"success": True},
                },
                "test_results": {"success": True},
            }
        }
        items = patch_evaluation(r)
        assert all(i["status"] == "PASS" for i in items)

    def test_test_skipped(self):
        r = {
            "validation": {
                "details": {"syntax": {"success": True}},
                "test_results": {"skipped": True},
            }
        }
        items = patch_evaluation(r)
        assert items[-1]["status"] == "SKIP"

    def test_failure_recorded(self):
        r = {
            "validation": {
                "details": {"syntax": {"success": False}},
                "test_results": {"success": False},
            }
        }
        items = patch_evaluation(r)
        assert items[0]["status"] == "FAIL"
        assert items[-1]["status"] == "FAIL"


class TestLabels:
    def test_risk_factor_label_known(self):
        assert risk_factor_label("severity") == "Severity"

    def test_risk_factor_label_fallback(self):
        assert risk_factor_label("unknown_factor") == "Unknown Factor"
