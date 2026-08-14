"""
Adaptive confidence scoring engine.
"""

import logging
from typing import Any

from core.confidence.learning_engine import (
    ConfidenceLearningEngine,
)

learning_engine = ConfidenceLearningEngine()

log = logging.getLogger("ai_risk_guard.confidence")


BASE_CONFIDENCE = {
    "COMMAND_INJECTION": 0.75,
    "CODE_INJECTION": 0.73,
    "HARDCODED_SECRET": 0.70,
    "INSECURE_DESERIALIZATION": 0.82,
}


def calculate_confidence(
    vulnerability: dict[str, Any],
    patch: str,
    validation: dict[str, Any] | None = None,
    test_results: dict[str, Any] | None = None,
    quality_score: float | None = None,
) -> float:
    """
    Calculate confidence score based on vulnerability type, validation results,
    test results, quality score, and patch quality.
    """
    try:
        score = BASE_CONFIDENCE.get(
            vulnerability.get("type", ""),
            0.65
        )

        if validation and validation.get("success"):
            score += 0.1
        else:
            score -= 0.25

        if vulnerability.get("severity") == "HIGH":
            score += 0.03

        # Boost if regression tests pass (environment-aware)
        if test_results and test_results.get("success") is True:
            test_mode = test_results.get("mode", "unknown")
            if test_mode == "docker":
                score += 0.12
            else:
                score += 0.04

        # Boost from quality score
        if quality_score is not None:
            score += quality_score * 0.08

        patch_length = len(
            (patch or "").strip()
        )

        if patch_length < 10:
            score -= 0.1

        if patch_length > 400:
            score -= 0.08

        score += learning_engine.confidence_adjustment(
            vulnerability.get("type", "")
        )

        score = max(0.2, min(0.95, score))

        return round(score, 3)

    except Exception as e:
        log.error("Confidence calculation failed: %s", e)
        return 0.5