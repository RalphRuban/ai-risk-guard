"""
Context-aware weighted risk scoring engine.
"""

from typing import Dict, Any, Optional
from utils.logger import logger
from core.risk.context_engine import ContextRiskEngine
from core.confidence.learning_engine import ConfidenceLearningEngine

learning_engine = ConfidenceLearningEngine()

_WEIGHTS = {
    "severity": 0.22,
    "type": 0.14,
    "validation": 0.18,
    "confidence": 0.12,
    "complexity": 0.10,
    "sensitivity": 0.12,
    "exposure": 0.12,
}


def normalize_severity(severity: str) -> float:
    return {
        "HIGH": 1.0,
        "MEDIUM": 0.6,
        "LOW": 0.3,
    }.get(severity, 0.5)


def normalize_type(vulnerability_type: str) -> float:
    return {
        "COMMAND_INJECTION": 1.0,
        "CODE_INJECTION": 0.95,
        "INSECURE_DESERIALIZATION": 0.9,
        "HARDCODED_SECRET": 0.7,
    }.get(vulnerability_type, 0.5)


def _get_risk_factors(
    vulnerability: Dict[str, Any],
    pr: Dict[str, Any],
    confidence: float,
    validation: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """Helper to calculate individual risk factors."""
    metrics = metrics or {}
    
    # Adaptive adjustment based on historical feedback (Week 4)
    adjustment = learning_engine.confidence_adjustment(
        vulnerability.get("type", "")
    )

    return {
        "severity": normalize_severity(vulnerability.get("severity", "MEDIUM")),
        "type": normalize_type(vulnerability.get("type", "")),
        "validation": 0.2 if validation and validation.get("success") else 1.0,
        "confidence": max(0.0, min(1.0, (1.0 - confidence) - adjustment)),
        "complexity": min(metrics.get("complexity", 1) / 10, 1.0),
        "sensitivity": ContextRiskEngine.file_sensitivity(vulnerability.get("file", "")),
        "exposure": 0.7, # Default exposure for now
    }


def calculate_risk(
    vulnerability: Dict[str, Any],
    pr: Dict[str, Any],
    confidence: float = 0.5,
    validation: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> float:
    """Calculate total risk score (0-10)."""
    try:
        factors = _get_risk_factors(vulnerability, pr, confidence, validation, metrics)
        score = sum(factors[k] * _WEIGHTS[k] for k in _WEIGHTS)
        return round(score * 10, 2)
    except Exception as e:
        logger.error(f"Risk calculation error: {e}", "RISK")
        return 0.0


def explain_risk(
    vulnerability: Dict[str, Any],
    pr: Dict[str, Any],
    confidence: float,
    validation: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, float]]:
    """Provide breakdown of risk factors."""
    try:
        factors = _get_risk_factors(vulnerability, pr, confidence, validation, metrics)
        return {
            factor: {
                "value": round(value, 2),
                "weight": _WEIGHTS[factor],
                "contribution": round(value * _WEIGHTS[factor], 3),
            }
            for factor, value in factors.items()
        }
    except Exception as e:
        logger.error(f"Risk explanation error: {e}", "RISK")
        return {}