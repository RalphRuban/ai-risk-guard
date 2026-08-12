"""
Multi-factor patch quality scoring engine.
"""

from typing import Any


class PatchScorer:
    def __init__(self, weights: dict[str, float] | None = None):
        if weights is None:
            try:
                from core.config import config
                weights_dict = config.quality.weights
                self.weights = {
                    "syntax_validity": weights_dict["syntax_validity"],
                    "security_validation": weights_dict["security_validation"],
                    "tests_passed": weights_dict["tests_passed"],
                    "complexity": weights_dict["complexity"],
                    "formatting_preserved": weights_dict["formatting_preserved"],
                    "confidence": weights_dict["confidence"],
                }
            except Exception:
                self.weights = weights or {
                    "syntax_validity": 0.20,
                    "security_validation": 0.25,
                    "tests_passed": 0.20,
                    "complexity": -0.10,
                    "formatting_preserved": 0.10,
                    "confidence": 0.15,
                }
        else:
            self.weights = weights

    def score(self, candidate: dict[str, Any], context: dict[str, Any] | None = None) -> float:
        context = context or {}
        score = 0.0

        syntax = candidate.get("validation_details", {}).get("syntax", {})
        if syntax.get("success") is True:
            score += self.weights["syntax_validity"]

        rescan = candidate.get("validation_details", {}).get("rescan", {})
        if rescan.get("success") is True:
            score += self.weights["security_validation"]

        test_results = candidate.get("test_results", {})
        if test_results.get("success") is True:
            test_mode = test_results.get("mode", "unknown")
            if test_mode == "docker":
                score += self.weights["tests_passed"]
            elif test_mode == "local":
                score += self.weights["tests_passed"] * 0.6
            else:
                score += self.weights["tests_passed"] * 0.4
        elif test_results.get("skipped") is True:
            score += 0.05

        metrics = context.get("metrics", {})
        complexity = metrics.get("complexity", 0)
        if complexity <= 3:
            score += abs(self.weights["complexity"])
        elif complexity >= 8:
            score += self.weights["complexity"]

        formatting_diff = candidate.get("formatting_diff", 0)
        if formatting_diff == 0:
            score += self.weights["formatting_preserved"]

        validation_score = candidate.get("validation_score", 0)
        score += self.weights["confidence"] * validation_score

        return round(max(0.0, min(1.0, score)), 4)

    def get_breakdown(self, candidate: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, float]:
        context = context or {}
        breakdown = {}

        syntax = candidate.get("validation_details", {}).get("syntax", {})
        syntax_score = self.weights["syntax_validity"] if syntax.get("success") is True else 0.0
        breakdown["syntax_validity"] = syntax_score

        rescan = candidate.get("validation_details", {}).get("rescan", {})
        rescan_score = self.weights["security_validation"] if rescan.get("success") is True else 0.0
        breakdown["security_validation"] = rescan_score

        test_results = candidate.get("test_results", {})
        if test_results.get("success") is True:
            test_mode = test_results.get("mode", "unknown")
            if test_mode == "docker":
                tests_score = self.weights["tests_passed"]
            elif test_mode == "local":
                tests_score = self.weights["tests_passed"] * 0.6
            else:
                tests_score = self.weights["tests_passed"] * 0.4
        elif test_results.get("skipped") is True:
            tests_score = 0.05
        else:
            tests_score = 0.0
        breakdown["tests_passed"] = tests_score

        metrics = context.get("metrics", {})
        complexity = metrics.get("complexity", 0)
        if complexity <= 3:
            breakdown["complexity"] = abs(self.weights["complexity"])
        elif complexity >= 8:
            breakdown["complexity"] = self.weights["complexity"]
        else:
            breakdown["complexity"] = 0.0

        formatting_diff = candidate.get("formatting_diff", 0)
        breakdown["formatting_preserved"] = self.weights["formatting_preserved"] if formatting_diff == 0 else 0.0

        validation_score = candidate.get("validation_score", 0)
        breakdown["confidence"] = self.weights["confidence"] * validation_score

        breakdown["total"] = round(sum(breakdown.values()), 4)
        breakdown["total"] = max(0.0, min(1.0, breakdown["total"]))

        return breakdown
