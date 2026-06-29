"""
Adaptive confidence learning engine.
"""

from utils.db import get_feedback_stats


class ConfidenceLearningEngine:
    """
    Adaptive learning engine that adjusts confidence based on historical feedback.
    Includes statistical damping to prevent over-reacting to small sample sizes.
    """

    MIN_SAMPLES = 5  # Don't adjust weights until we have a baseline of data

    def success_rate(self, vuln_type: str) -> float:
        """
        Query database for historical success rate of a specific vulnerability type.
        """
        stats = get_feedback_stats(vuln_type)

        # Stability: If we have low data, stay neutral
        if stats["total"] < self.MIN_SAMPLES:
            return 0.5 

        return round(stats["accepted"] / stats["total"], 3)

    def confidence_adjustment(self, vuln_type: str) -> float:
        """
        Calculate a weight adjustment based on historical performance.
        Tiered for conservative, predictable growth.
        """
        rate = self.success_rate(vuln_type)

        # High Confidence: Consistently accepted
        if rate >= 0.90: return 0.10
        if rate >= 0.75: return 0.05

        # Low Confidence: Consistently rejected
        if rate <= 0.25: return -0.15
        if rate <= 0.40: return -0.05

        return 0.0