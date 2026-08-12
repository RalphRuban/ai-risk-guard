"""
Adaptive confidence learning engine.
"""

from datetime import UTC, datetime

from utils.db import get_feedback_records, get_feedback_stats


class ConfidenceLearningEngine:
    """
    Adaptive learning engine that adjusts confidence based on historical feedback.
    Uses time-weighted decay so recent feedback matters more than old feedback.
    Includes statistical damping to prevent over-reacting to small sample sizes.
    """

    MIN_SAMPLES = 5      # Don't adjust weights until we have a baseline of data
    DECAY_HALFLIFE_DAYS = 30  # A record's weight halves every 30 days

    def success_rate(self, vuln_type: str) -> float:
        """
        Query database for time-weighted success rate of a specific vulnerability type.
        Recent feedback counts more than old feedback (exponential decay).
        """
        stats = get_feedback_stats(vuln_type)

        if stats["total"] < self.MIN_SAMPLES:
            return 0.5

        records = get_feedback_records(vuln_type)
        if not records:
            return 0.5

        now = datetime.now(UTC).replace(tzinfo=None)
        total_weight = 0.0
        accepted_weight = 0.0

        for record in records:
            ts = record["timestamp"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            days_ago = (now - ts).total_seconds() / 86400.0
            weight = 2 ** (-days_ago / self.DECAY_HALFLIFE_DAYS)
            total_weight += weight
            if record["outcome"] == "ACCEPTED":
                accepted_weight += weight

        rate = accepted_weight / total_weight if total_weight > 0 else 0.5
        return round(rate, 3)

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