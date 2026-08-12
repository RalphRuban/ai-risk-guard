"""
tests/test_risk_engine_fixes.py
Regression tests for the risk-scoring, re-scan gating, and reporting fixes.
"""

from core.config import config
from core.metadata.vuln_metadata import VULN_METADATA
from core.risk.risk_engine import (
    _factor_level,
    _validation_factor,
    calculate_risk,
    effective_severity,
    explain_risk,
    normalize_severity,
)
from services.github.reporter import _format_risk_breakdown


class TestSeverityNormalization:
    def test_critical_is_configured(self):
        assert normalize_severity("CRITICAL") == 1.0

    def test_all_metadata_severities_are_configured(self):
        seen = {meta["severity"] for meta in VULN_METADATA.values()}
        for label in seen:
            assert label in config.risk.severity_normalization, label

    def test_type_normalization_covers_every_type(self):
        for vuln_type in VULN_METADATA:
            assert vuln_type in config.risk.type_normalization, vuln_type


class TestEffectiveSeverity:
    def test_uses_type_based_severity(self):
        assert effective_severity({"type": "COMMAND_INJECTION"}) == "CRITICAL"
        assert effective_severity({"type": "HARDCODED_SECRET"}) == "HIGH"
        assert effective_severity({"type": "WEAK_CRYPTOGRAPHY"}) == "MEDIUM"

    def test_falls_back_to_stored_severity(self):
        assert effective_severity({"type": "UNKNOWN_TYPE", "severity": "LOW"}) == "LOW"


class TestFactorLevel:
    def test_severity_levels_respect_label(self):
        assert _factor_level("severity", 1.0, "CRITICAL") == "Critical"
        assert _factor_level("severity", 1.0, "HIGH") == "High"
        assert _factor_level("severity", 0.6, "MEDIUM") == "Moderate"
        assert _factor_level("severity", 0.3, "LOW") == "Low"


class TestValidationFactor:
    def test_legacy_success_shape(self):
        assert _validation_factor({"success": True}) == 0.2
        assert _validation_factor({"success": False}) == 1.0

    def test_full_details_shape_gates_on_rescan(self):
        verified = {"syntax": {"success": True}, "rescan": {"success": True}}
        assert _validation_factor(verified) == 0.2
        partial = {"syntax": {"success": True}, "rescan": {"success": False}}
        assert _validation_factor(partial) == 0.6
        broken = {"syntax": {"success": False}, "rescan": {"success": False}}
        assert _validation_factor(broken) == 1.0

    def test_missing_validation_is_max_risk(self):
        assert _validation_factor(None) == 1.0


class TestRiskRescanGating:
    def test_failed_rescan_raises_risk(self):
        vuln = {"type": "HARDCODED_SECRET", "severity": "HIGH", "file": "test.py"}
        passed = calculate_risk(
            vuln, {}, confidence=0.9,
            validation={"syntax": {"success": True}, "rescan": {"success": True}},
            quality_score=0.9,
        )
        failed = calculate_risk(
            vuln, {}, confidence=0.9,
            validation={"syntax": {"success": True}, "rescan": {"success": False}},
            quality_score=0.9,
        )
        assert failed > passed

    def test_breakdown_contains_all_factors(self):
        vuln = {"type": "SSRF", "severity": "HIGH", "file": "test.py"}
        breakdown = explain_risk(
            vuln, {}, confidence=0.9,
            validation={"syntax": {"success": True}, "rescan": {"success": True}},
        )
        assert set(config.risk.weights) == set(breakdown)


class TestSeverityAwarePriority:
    def test_critical_is_never_below_p2(self):
        from core.reporting.summary import compute_priority
        assert compute_priority(1.0, severity="CRITICAL") == "P2"


class TestBreakdownReporting:
    def test_breakdown_renders_every_factor(self):
        vuln = {"type": "SSRF", "severity": "HIGH", "file": "test.py"}
        breakdown = explain_risk(
            vuln, {}, confidence=0.9,
            validation={"syntax": {"success": True}, "rescan": {"success": True}},
        )
        rendered = _format_risk_breakdown({"risk_breakdown": breakdown})
        # header + separator + one row per factor
        expected_rows = len(breakdown) + 2
        assert len(rendered.strip().splitlines()) == expected_rows
