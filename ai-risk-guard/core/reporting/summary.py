"""
core/reporting/summary.py
Pure helper functions shared by the PR comment (services/github/reporter.py)
and the SARIF generator (core/sarif/sarif_generator.py).

Keeping these here guarantees the comment and SARIF always agree on derived
values (security score, priority, compliance counts, etc.) even though they
are rendered in very different formats.
"""

import math
import re
from typing import Any

from core.config import config
from core.risk.risk_engine import FACTOR_LABELS

# Risk priorities derived from the same gating thresholds used to decide
# whether a human review or a block is required.
PRIORITY_P1 = "P1"
PRIORITY_P2 = "P2"
PRIORITY_P3 = "P3"

# Detection confidence for each rule. Rules are deterministic AST/regex
# matches; the small discount reflects heuristic edge cases (e.g. dynamic
# strings that turn out to be constant in practice).
DETECTION_CONFIDENCE: dict[str, float] = {
    "COMMAND_INJECTION": 0.95,
    "CODE_INJECTION": 0.95,
    "SQL_INJECTION": 0.90,
    "PATH_TRAVERSAL": 0.90,
    "SSRF": 0.90,
    "INSECURE_DESERIALIZATION": 0.95,
    "WEAK_CRYPTOGRAPHY": 0.95,
    "HARDCODED_SECRET": 0.90,
}

_FACTOR_DISPLAY = {
    "severity": "Severity",
    "type": "Category",
    "validation": "Validation",
    "confidence": "Patch confidence",
    "complexity": "Complexity",
    "sensitivity": "Sensitivity",
    "exposure": "Exposure",
    "quality": "Patch quality",
}


def risk_factor_label(factor: str) -> str:
    """Human-readable label for a risk factor name."""
    return _FACTOR_DISPLAY.get(factor, FACTOR_LABELS.get(factor, factor.replace("_", " ").title()))


def factor_value(factor: Any) -> float:
    """Extract the numeric value from a risk factor (dict or RiskFactor)."""
    if isinstance(factor, dict):
        return float(factor.get("value", 0.0))
    return float(getattr(factor, "value", 0.0))


def compute_priority(risk: float, severity: str = "LOW") -> str:
    """Map a risk score to a remediation priority (P1/P2/P3).

    Priority is risk-driven so it stays consistent with the risk score shown on
    each finding. Severity acts as a floor: a CRITICAL finding is never downgraded
    below P2 regardless of its computed risk.

    P1: blocks the merge (>= max_allowed_risk).
    P2: requires human review before merge (>= auto_request_changes_above),
        or the finding is CRITICAL.
    P3: low risk, schedule a fix.
    """
    try:
        max_allowed = config.risk.gating.max_allowed_risk
        review_above = config.risk.gating.auto_request_changes_above
    except Exception:
        max_allowed, review_above = 8.5, 4.0
    if risk >= max_allowed:
        return PRIORITY_P1
    if risk >= review_above:
        return PRIORITY_P2
    if (severity or "LOW").upper() == "CRITICAL":
        return PRIORITY_P2
    return PRIORITY_P3


def compute_security_score(results: list[dict[str, Any]]) -> float:
    """Compute a 0-100 security score for the PR.

    Formula (documented in the PR comment):
        for each finding, normalized_risk = sum(value[f] * weight[f]) / sum(weights)
        avg_risk = mean(normalized_risk across findings)
        security_score = 100 * (1 - avg_risk)

    A score of 100 means no measurable risk; 0 means maximum risk. The result
    is clamped to [0, 100] and rounded to one decimal.
    """
    if not results:
        return 100.0
    weights = dict(config.risk.weights)
    total_weight = sum(weights.values()) or 1.0

    contributions = []
    for r in results:
        breakdown = r.get("risk_breakdown", {})
        if breakdown:
            contrib = sum(
                factor_value(breakdown[k]) * weights[k]
                for k in weights if k in breakdown
            ) / total_weight
        else:
            contrib = min(max(float(r.get("risk", 0.0)) / 10.0, 0.0), 1.0)
        contributions.append(contrib)

    avg_risk = sum(contributions) / len(contributions) if contributions else 0.0
    score = round(100.0 * (1.0 - avg_risk), 1)
    return max(0.0, min(100.0, score))


def compliance_counts(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate OWASP/CWE/policy statistics across findings."""
    owasp: dict[str, int] = {}
    cwe: dict[str, int] = {}
    policy_violations = [
        violation
        for r in results
        for violation in (r.get("validation", {}) or {}).get("policy_violations", []) or []
    ]
    for r in results:
        vuln = r.get("vulnerability", {}) or {}
        owasp_key = vuln.get("owasp") or ""
        if owasp_key:
            owasp[owasp_key] = owasp.get(owasp_key, 0) + 1
        cwe_key = vuln.get("cwe") or ""
        if cwe_key:
            cwe[cwe_key] = cwe.get(cwe_key, 0) + 1
    return {
        "owasp": owasp,
        "cwe": cwe,
        "policy_violations": policy_violations,
        "policy_pass": not policy_violations,
    }


def parse_test_summary(output: str) -> dict[str, int] | None:
    """Parse pytest output for test counts, e.g. '3 passed, 1 failed'.

    Returns None if no recognizable summary is found.
    """
    if not output:
        return None
    counts: dict[str, int] = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    matched = False
    for key in ("passed", "failed", "error", "skipped"):
        m = re.search(r"(\d+)\s+" + re.escape(key), output)
        if m:
            counts[key] = int(m.group(1))
            matched = True
    return counts if matched else None


def patch_evaluation(r: dict[str, Any]) -> list[dict[str, str]]:
    """Derive a per-item PASS/FAIL/SKIP checklist for a finding's patch."""
    details = r.get("validation", {}).get("details", {}) or {}
    test_results = r.get("validation", {}).get("test_results", {}) or {}
    items = [
        {"label": "Syntax", "status": "PASS" if details.get("syntax", {}).get("success") else "FAIL"},
        {"label": "Security re-scan", "status": "PASS" if details.get("rescan", {}).get("success") else "FAIL"},
        {"label": "Sandbox", "status": "PASS" if details.get("sandbox", {}).get("success") else "FAIL"},
        {"label": "Policy", "status": "PASS" if details.get("policy", {}).get("success") else "FAIL"},
    ]
    if test_results.get("skipped"):
        items.append({"label": "Regression tests", "status": "SKIP"})
    else:
        items.append({"label": "Regression tests", "status": "PASS" if test_results.get("success") else "FAIL"})
    return items


def validation_summary(r: dict[str, Any]) -> dict[str, Any]:
    """Compact summary of the validation pipeline for a finding."""
    validation = r.get("validation", {}) or {}
    test_results = validation.get("test_results", {}) or {}
    return {
        "success": bool(validation.get("success")),
        "score": float(validation.get("score", 0.0)),
        "mode": test_results.get("mode", "unknown"),
        "docker_unavailable": bool(test_results.get("docker_unavailable")),
        "local_fallback": test_results.get("local_fallback"),
        "test_summary": parse_test_summary(test_results.get("output", "")),
        "expected_failures": test_results.get("expected_failures") or [],
        "regression_failures": test_results.get("regression_failures") or [],
        "policy_violations": validation.get("policy_violations", []) or [],
    }


def shannon_entropy(value: str) -> float:
    """Shannon entropy (bits per character) of a string.

    High entropy (typically > 3.0) is a strong signal that a value is a real
    secret rather than a placeholder. Used to enrich HARDCODED_SECRET findings.
    """
    value = (value or "").strip()
    if not value:
        return 0.0
    freq: dict[str, int] = {}
    for ch in value:
        freq[ch] = freq.get(ch, 0) + 1
    n = len(value)
    entropy = -sum((count / n) * math.log2(count / n) for count in freq.values())
    return round(entropy, 2)


def extract_secret_value(code: str) -> str | None:
    """Extract the string literal from a hardcoded-secret line.

    e.g. 'password = "sup3rs3cr3t"' -> 'sup3rs3cr3t'
    """
    m = re.search(r"[\"']([^\"']{4,})[\"']", code or "")
    return m.group(1) if m else None
