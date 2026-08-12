"""
Context-aware weighted risk scoring engine.
"""

import logging
from typing import Any

from core.config import config
from core.metadata.vuln_metadata import severity_level_for
from core.risk.context_engine import ContextRiskEngine
from utils.logger import logger

log = logging.getLogger("ai_risk_guard.risk_engine")


def normalize_severity(severity: str) -> float:
    return config.risk.severity_normalization.get(severity, 0.5)


def normalize_type(vulnerability_type: str) -> float:
    return config.risk.type_normalization.get(vulnerability_type, 0.5)


def effective_severity(vulnerability: dict[str, Any]) -> str:
    """Single source of truth for the severity used in risk scoring.

    Prefers the type-based severity (``severity_level_for``) so that the score
    agrees with the severity label the PR comment displays. Falls back to the
    stored severity for unknown types.
    """
    type_severity = severity_level_for(vulnerability.get("type", ""))
    if type_severity:
        return type_severity
    return vulnerability.get("severity", "MEDIUM")


def _validation_factor(validation: dict[str, Any] | None) -> float:
    """Map patch validation results to a risk factor (0.2 = fully verified).

    Accepts both the full ``validation_details`` shape (``syntax``/``rescan``
    sub-dicts) and the legacy ``{"success": bool}`` shape. A patch that clears
    syntax but not the security re-scan is treated as partially verified.
    """
    if not validation:
        return 1.0
    if "syntax" in validation or "rescan" in validation:
        syntax_ok = (validation.get("syntax") or {}).get("success") is True
        rescan_ok = (validation.get("rescan") or {}).get("success") is True
        if syntax_ok and rescan_ok:
            return 0.2
        if syntax_ok:
            return 0.6
        return 1.0
    return 0.2 if validation.get("success") is True else 1.0


def _get_risk_factors(
    vulnerability: dict[str, Any],
    pr: dict[str, Any],
    confidence: float,
    validation: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    quality_score: float | None = None,
) -> dict[str, float]:
    """Helper to calculate individual risk factors."""
    metrics = metrics or {}
    
    # Higher quality score reduces risk (inverse relationship)
    quality_factor = (1.0 - (quality_score or 0.5)) * 0.15

    return {
        "severity": normalize_severity(effective_severity(vulnerability)),
        "type": normalize_type(vulnerability.get("type", "")),
        "validation": _validation_factor(validation),
        "confidence": max(0.0, min(1.0, 1.0 - confidence)),
        "complexity": min(metrics.get("complexity", 1) / 10, 1.0),
        "sensitivity": ContextRiskEngine.file_sensitivity(vulnerability.get("file", "")),
        "exposure": 0.7, # Default exposure for now
        "quality": quality_factor,
    }


def calculate_risk(
    vulnerability: dict[str, Any],
    pr: dict[str, Any],
    confidence: float = 0.5,
    validation: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    quality_score: float | None = None,
) -> float:
    """Calculate total risk score (0-10)."""
    try:
        factors = _get_risk_factors(vulnerability, pr, confidence, validation, metrics, quality_score)
        weights = config.risk.weights
        score = sum(factors[k] * weights[k] for k in weights)
        return round(score * 10, 2)
    except Exception as e:
        logger.error(f"Risk calculation error: {e}", "RISK")
        log.exception("Risk calculation error")
        return 0.0


FACTOR_LABELS = {
    "severity": "Inherent severity of the vulnerability type",
    "type": "Risk normalization for this vulnerability category",
    "validation": "Patch validation outcome (passing reduces risk)",
    "confidence": "Confidence in the patch correctness (low confidence increases risk)",
    "complexity": "Code complexity impact (higher complexity increases risk)",
    "sensitivity": "Sensitivity of the affected file or directory",
    "exposure": "Potential attack surface exposure",
    "quality": "Patch quality score (higher quality reduces risk)",
}


def explain_risk(
    vulnerability: dict[str, Any],
    pr: dict[str, Any],
    confidence: float,
    validation: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Provide breakdown of risk factors with qualitative explanations."""
    try:
        factors = _get_risk_factors(vulnerability, pr, confidence, validation, metrics)
        weights = config.risk.weights
        severity_label = effective_severity(vulnerability)
        return {
            factor: {
                "value": round(value, 2),
                "weight": weights[factor],
                "contribution": round(value * weights[factor], 3),
                "label": FACTOR_LABELS.get(factor, "Risk factor"),
                "level": _factor_level(factor, value, severity_label),
            }
            for factor, value in factors.items()
        }
    except Exception as e:
        logger.error(f"Risk explanation error: {e}", "RISK")
        log.exception("Risk explanation error")
        return {}


def _factor_level(factor: str, value: float, severity_label: str) -> str:
    severity = severity_label.upper()
    if factor == "severity":
        if severity == "CRITICAL":
            return "Critical"
        if severity == "HIGH":
            return "High"
        if severity == "MEDIUM":
            return "Moderate"
        return "Low"
    if factor == "validation":
        return "Unverified" if value > 0.5 else "Verified"
    if factor == "confidence":
        return "Low Confidence" if value > 0.5 else "High Confidence"
    if factor == "complexity":
        return "Complex" if value > 0.5 else "Simple"
    if factor == "sensitivity":
        return "Sensitive" if value > 0.5 else "Standard"
    if factor == "exposure":
        return "Exposed" if value > 0.5 else "Isolated"
    if factor == "quality":
        return "High Quality" if value < 0.3 else "Low Quality"
    if value > 0.7:
        return "High"
    if value > 0.4:
        return "Moderate"
    return "Low"