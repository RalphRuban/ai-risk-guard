"""
Adaptive confidence scoring engine.
"""

from core.confidence.learning_engine import (
    ConfidenceLearningEngine,
)


from typing import Dict, Any, Optional

learning_engine = ConfidenceLearningEngine()


BASE_CONFIDENCE = {
    "COMMAND_INJECTION": 0.75,
    "CODE_INJECTION": 0.73,
    "HARDCODED_SECRET": 0.70,
    "INSECURE_DESERIALIZATION": 0.82,
}


def calculate_confidence(
    vulnerability: Dict[str, Any],
    patch: str,
    validation: Optional[Dict[str, Any]] = None
) -> float:
    """
    Calculate confidence score based on vulnerability type, validation results, and patch quality.
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

    except Exception:
        return 0.5