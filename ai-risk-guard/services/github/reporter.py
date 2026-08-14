"""
Advanced GitHub PR security reporter with Code Scanning API support.
"""

import base64
import collections
import gzip
import json
import re
import time
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import requests

from core.config import config
from core.metadata.versions import (
    ANALYSIS_ENGINE,
    LANGUAGE,
    PATCH_ENGINE,
    RULES_VERSION,
    SCAN_MODE,
    TOOL_NAME,
    TOOL_VERSION,
    VALIDATOR,
)
from core.metadata.vuln_metadata import severity_level_for, vuln_name
from core.reporting.summary import (
    compliance_counts,
    compute_priority,
    compute_security_score,
    factor_value,
    parse_test_summary,
    patch_evaluation,
    risk_factor_label,
)
from core.sarif.converter import build_analysis_result
from core.sarif.sarif_generator import SARIFGenerator
from utils.db import record_bot_comment
from utils.logger import logger
from utils.retry import RateLimitError, retry

sarif_generator = SARIFGenerator()

BOT_MARKER = "<!-- ai-risk-guard -->"

# Scan times are shown to the developer in Indian Standard Time (UTC+5:30).
IST = timezone(timedelta(hours=5, minutes=30))

RISK_LABEL_PREFIX = "security-risk-"

_RETRY_KWARGS: dict[str, Any] = {
    "max_attempts": 3,
    "base_delay": 1.0,
    "backoff": 2.0,
    "max_delay": 30.0,
    "jitter": True,
    "retryable_exceptions": (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        RateLimitError,
    ),
}


def _raise_on_rate_limit(response):
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "5")
        raise RateLimitError(retry_after=float(retry_after))
    remaining = response.headers.get("X-RateLimit-Remaining")
    if remaining is not None and remaining.isdigit() and int(remaining) < 10:
        reset_ts = response.headers.get("X-RateLimit-Reset", "unknown")
        logger.warning(
            f"GitHub rate limit low: {remaining} remaining (resets at {reset_ts})",
            "GITHUB",
        )
    return response


def _retry_logger(exc, attempt, delay):
    logger.warning(f"GitHub API attempt {attempt} failed: {exc}, retrying in {delay:.1f}s", "GITHUB")


def _get_max_risk(results: list) -> float:
    """Return the highest risk score across all findings."""
    return max((r.get("risk", 0) for r in results), default=0.0)


def _risk_label_name(max_risk: float) -> str:
    """Return the security-risk label for a given max risk score."""
    if max_risk >= 7.0:
        return f"{RISK_LABEL_PREFIX}high"
    if max_risk >= 4.0:
        return f"{RISK_LABEL_PREFIX}medium"
    return f"{RISK_LABEL_PREFIX}low"


def _extract_scan_number(body: str) -> int:
    """Extract scan number from a comment body by searching for ``<!-- ai-risk-guard scan:N -->``."""
    match = re.search(r'<!-- ai-risk-guard scan:(\d+) -->', body)
    return int(match.group(1)) if match else 0


def _risk_bar(score: float) -> str:
    """Render risk score as a 10-block bar chart using plain text."""
    filled = round(min(max(score, 0.0), 10.0))
    return "█" * filled + "░" * (10 - filled)


_SEVERITY_EMOJI = {
    "CRITICAL": "⛔",
    "HIGH": "🔴",
    "MEDIUM": "🟡",
    "LOW": "🟢",
}

_PRIORITY_RANK = {"P1": 0, "P2": 1, "P3": 2}
_SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

_VULN_TYPE_META = {
    "SQL_INJECTION": ("💉", "Injection"),
    "COMMAND_INJECTION": ("💉", "Injection"),
    "CODE_INJECTION": ("💉", "Injection"),
    "PATH_TRAVERSAL": ("📂", "File System"),
    "SSRF": ("🌐", "Network"),
    "HARDCODED_SECRET": ("🔑", "Secrets"),
    "INSECURE_DESERIALIZATION": ("📦", "Deserialization"),
    "WEAK_CRYPTOGRAPHY": ("🧬", "Cryptography"),
    "INSECURE_CIPHER": ("🧬", "Cryptography"),
    "TLS_VERIFICATION_DISABLED": ("🔓", "Transport Security"),
    "DEBUG_CODE": ("🐛", "Code Quality"),
}

_SCORE_LEVELS = (
    (90.0, "🟢", "Excellent"),
    (75.0, "🟢", "Good"),
    (50.0, "🟡", "Moderate"),
    (25.0, "🟠", "At Risk"),
    (0.0, "🔴", "Critical"),
)

_GATE_ICON = {"PASS": "🟢", "FAIL": "🔴", "SKIP": "⏭️"}


def _score_level(score: float) -> tuple:
    """Return (emoji, label) for a 0-100 security score."""
    for threshold, emoji, label in _SCORE_LEVELS:
        if score >= threshold:
            return emoji, label
    return "🔴", "Critical"


def _score_bar(score: float, width: int = 16) -> str:
    """Render a 0-100 score as a block bar."""
    filled = round(min(max(score, 0.0), 100.0) / 100.0 * width)
    return "█" * filled + "░" * (width - filled)


def _extract_collection_error(stderr: str, limit: int = 160) -> str:
    """Extract a concise reason from pytest stderr when a run never started.

    Prefers the first ModuleNotFoundError/ImportError/SyntaxError/ERROR line so
    the PR comment can explain *why* the regression tests could not run instead
    of falling back to a generic pre-patch note.
    """
    lines = [ln.strip() for ln in (stderr or "").splitlines() if ln.strip()]
    for ln in lines:
        if re.search(r"(ModuleNotFoundError|ImportError|SyntaxError|NameError|ERROR)", ln):
            text = ln
            if text.startswith("ERROR:"):
                text = text[6:].strip()
            return text[:limit]
    return (lines[0] if lines else "pytest collection error")[:limit]


def _finding_severity(r) -> str:
    """Return the display severity level for a finding.

    Uses the per-type CVSS classification (matching GitHub Code Scanning),
    falling back to the finding's declared severity for unknown types.
    """
    vuln = r.get("vulnerability", {}) or {}
    level = severity_level_for(vuln.get("type", ""))
    if level:
        return level
    sev = str(vuln.get("severity", "MEDIUM")).upper()
    return sev if sev in _SEVERITY_EMOJI else "MEDIUM"


def _severity_counts(results: list) -> dict:
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for r in results:
        counts[_finding_severity(r)] += 1
    return counts


def _finding_sort_key(r) -> tuple:
    """Sort key: priority (P1 first), then severity, then risk desc, then file:line."""
    vuln = r.get("vulnerability", {}) or {}
    priority = r.get("priority") or ""
    priority_rank = _PRIORITY_RANK.get(str(priority).upper(), 3)
    risk = r.get("risk", 0)
    severity = _risk_badge(risk)
    if severity not in _SEVERITY_RANK and vuln.get("severity"):
        severity = str(vuln["severity"]).upper()
    severity_rank = _SEVERITY_RANK.get(severity, 3)
    file_path = vuln.get("file_rel", vuln.get("file", ""))
    line = vuln.get("line", 0)
    return (priority_rank, severity_rank, -risk, file_path, line)


def _sort_findings(results: list) -> list:
    """Return findings sorted by priority, then severity, then risk."""
    return sorted(results, key=_finding_sort_key)


def extract_targeted_hunks(diff: str, findings: list, context: int = 5) -> str:
    """Extract only the diff hunks relevant to the given findings.

    findings: list of dicts with "type" and "line" keys (line is 1-indexed, original file)
    context: lines of padding context per finding
    Returns a single combined diff string or the original diff if parsing fails.
    """
    if not diff or not findings:
        return diff

    lines = diff.splitlines(keepends=True)
    hunk_re = re.compile(r'^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@')

    hunks = []
    current = None
    current_lines = []

    for line in lines:
        m = hunk_re.match(line)
        if m:
            if current is not None:
                hunks.append((current, current_lines))
            old_start = int(m.group(1))
            old_count_str = m.group(2)
            old_count = int(old_count_str) if old_count_str else 1
            current = (old_start, old_start + old_count - 1)
            current_lines = [line]
        else:
            current_lines.append(line)

    if current is not None:
        hunks.append((current, current_lines))

    if not hunks:
        return diff

    # Build set of interesting line numbers
    interesting = set()
    for f in findings:
        line = f.get("line", 0)
        for offset in range(-context, context + 1):
            interesting.add(line + offset)

    # Collect hunks that overlap with interesting lines, plus any hunk that
    # adds imports (e.g. `import shlex`) so injected dependencies are always
    # visible even when the fixer places them far from the finding lines.
    import_re = re.compile(r"^\+import |^\+from ")
    result = []
    for (hunk_start, hunk_end), hunk_lines in hunks:
        adds_import = any(import_re.match(line) for line in hunk_lines[1:])
        if adds_import or any(l >= hunk_start and l <= hunk_end for l in interesting):
            result.extend(hunk_lines)

    return "".join(result) if result else diff





_OWASP_MAP = {
    "SQL_INJECTION": "[A03:2021](https://owasp.org/Top10/2021/A03_2021-Injection/)",
    "COMMAND_INJECTION": "[A03:2021](https://owasp.org/Top10/2021/A03_2021-Injection/)",
    "CODE_INJECTION": "[A03:2021](https://owasp.org/Top10/2021/A03_2021-Injection/)",
    "PATH_TRAVERSAL": "[A01:2021](https://owasp.org/Top10/2021/A01_2021-Broken_Access_Control/)",
    "HARDCODED_SECRET": "[A07:2021](https://owasp.org/Top10/2021/A07_2021-Identification_and_Authentication_Failures/)",
    "INSECURE_DESERIALIZATION": "[A08:2021](https://owasp.org/Top10/2021/A08_2021-Software_and_Data_Integrity_Failures/)",
    "WEAK_CRYPTOGRAPHY": "[A02:2021](https://owasp.org/Top10/2021/A02_2021-Cryptographic_Failures/)",
    "INSECURE_CIPHER": "[A02:2021](https://owasp.org/Top10/2021/A02_2021-Cryptographic_Failures/)",
    "SSRF": "[A10:2021](https://owasp.org/Top10/2021/A10_2021-Server-Side_Request_Forgery_(SSRF)/)",
}


def _risk_badge(score: float) -> str:
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    return "LOW"


def _format_risk_breakdown(r):
    """Render the contributing risk factors as a small table.

    Every weighted factor is shown (sorted by value) so the table can be
    reconciled with the headline risk score and the PR security score.
    """
    breakdown = r.get("risk_breakdown", {})
    if not breakdown:
        return ""
    rows = sorted(
        breakdown.items(),
        key=lambda kv: factor_value(kv[1]),
        reverse=True,
    )
    lines = ["| Factor | Level | Value |", "|--------|-------|-------|"]
    for factor, data in rows:
        value = factor_value(data)
        level = data.get("level", "") if isinstance(data, dict) else ""
        lines.append(f"| {risk_factor_label(factor)} | {level} | {value:.2f} |")
    return "\n".join(lines) + "\n"


def _shared_candidate_count(results, r):
    """How many findings in `results` share the same patch candidate as `r`."""
    candidate_id = r.get("candidate_id")
    if not candidate_id:
        return 1
    return sum(1 for other in results if other.get("candidate_id") == candidate_id)


# Process-level memo so the LLM regression explanation is generated at most once
# per distinct test_results payload per process (a file's findings all share one
# payload, so this turns N card renders into one Gemini call).
_regression_explanation_cache: dict[str, str | None] = {}


def _regression_explanation(test_results) -> str | None:
    """Return a readable LLM explanation for the test results, or ``None``.

    Fail-open: returns ``None`` (never raises) when the LLM is unavailable,
    rate-limited, or disabled, so callers fall back to the deterministic block.
    """
    if not test_results:
        return None
    key = json.dumps(test_results, sort_keys=True, default=str)
    if key in _regression_explanation_cache:
        return _regression_explanation_cache[key]
    try:
        from core.triage.llm_triage import LLMTriage
        text = LLMTriage().explain_regression_tests(test_results)
    except Exception:
        text = None
    _regression_explanation_cache[key] = text
    return text


def _format_regression_details(r) -> str:
    """Render the technical regression-test detail block for one result.

    Mirrors the deterministic block shown in every finding card; used as a
    collapsed per-file section when the readable LLM paragraph replaces it in
    the cards, so test counts, pinned test names, env vars and rebind info stay
    available on demand.
    """
    validation = r.get("validation", {})
    details = validation.get("details", {})
    sandbox_res = details.get("sandbox", {})
    test_results = validation.get("test_results", {})
    test_summary = parse_test_summary(test_results.get("output", ""))
    expected_failures = test_results.get("expected_failures") or []
    regression_failures = test_results.get("regression_failures") or []

    parts = []
    if test_summary:
        count_parts = [f"{test_summary['passed']} passed"]
        if expected_failures:
            count_parts.append(f"{len(expected_failures)} expected")
        remaining_failed = test_summary["failed"] - len(expected_failures)
        if remaining_failed > 0:
            count_parts.append(f"{remaining_failed} failed")
        if test_summary.get("error"):
            count_parts.append(f"{test_summary['error']} error" + ("s" if test_summary["error"] != 1 else ""))
        count_parts.append(f"{test_summary['skipped']} skipped")
        parts.append(f"ℹ️ Regression tests: {', '.join(count_parts)} (mode: docker)")
    elif test_results.get("mode") == "docker":
        parts.append("ℹ️ Test environment: docker")

    if expected_failures and not regression_failures:
        parts.append(
            f"ℹ️ *{len(expected_failures)} failing test(s) pin the removed vulnerabilities "
            f"({', '.join(expected_failures)}) — expected to fail after the fix, not regressions.*"
        )

    rebind_info = test_results.get("rebind") or {}
    if rebind_info.get("rebound"):
        mapping = " → ".join(f"{k} → {v}" for k, v in (rebind_info.get("rebound_map") or {}).items())
        if mapping:
            parts.append(f"ℹ️ *Test imports rebound to patched module ({mapping}).*")

    mocked_env = test_results.get("mocked_env_vars") or []
    if mocked_env:
        parts.append(f"ℹ️ *Sandbox mocked env vars: {', '.join(mocked_env)} — tests asserting the original values fail on substitution, not a patch regression.*")

    skip_reason = (test_results.get("error") or "").strip()
    if test_results.get("skipped") and skip_reason and skip_reason != "No test file":
        parts.append(f"⏭️ *Regression tests skipped — {skip_reason}.*")

    no_true_regressions = (
        bool(expected_failures)
        and not regression_failures
        and not test_results.get("skipped")
        and test_results.get("success") is True
    )

    if no_true_regressions:
        parts.append(f"✅ No regressions — {len(expected_failures)} test(s) pin the removed vulnerabilities and are expected to fail after the fix.")
    elif test_results.get("success") is False and not test_results.get("skipped") and not (test_results.get("image_unavailable") or sandbox_res.get("image_unavailable")):
        total_run = (test_summary["passed"] + test_summary["failed"]) if test_summary else 0
        err_text = "".join(filter(None, [
            test_results.get("error") or "",
            "\n",
            test_results.get("output") or "",
        ])).strip()
        if total_run == 0 and err_text:
            reason = _extract_collection_error(err_text)
            parts.append(f"⚠️ *Tests could not run — {reason}*")
        elif regression_failures:
            parts.append(
                f"⚠️ *Regression test failure — {len(regression_failures)} test(s) fail outside the fixed behavior: "
                f"{', '.join(regression_failures)}.*"
            )
        else:
            parts.append("⚠️ *Regression test failure expected — tests were written for pre-patch code.*")
    return "\n\n".join(parts)


def _format_finding_card(r, is_legacy=False, index=None, total=None, shared_count=1):
    vulnerability = r["vulnerability"]
    vulnerability_type = vulnerability["type"]
    severity = _finding_severity(r)
    risk = r.get("risk", 0)
    confidence = r.get("confidence", 0)
    sev_emoji = _SEVERITY_EMOJI.get(severity, "")
    priority = r.get("priority", compute_priority(risk, vulnerability.get("severity", "LOW")))

    type_icon = _VULN_TYPE_META.get(vulnerability_type, ("⚠️", "Security"))[0]

    cwe = vulnerability.get("cwe", "")
    cwe_link = f"[{cwe}](https://cwe.mitre.org/data/definitions/{cwe.replace('CWE-', '')}.html)" if cwe else ""
    owasp_link = _OWASP_MAP.get(vulnerability_type, "")

    legacy_tag = " *(legacy)*" if is_legacy else ""
    unconfirmed_tag = " *(unconfirmed by AI review — not blocking)*" if r.get("unconfirmed") else ""

    card = ""
    card += f"\n<details><summary><b>{type_icon} {vuln_name(vulnerability_type)}</b>{legacy_tag}{unconfirmed_tag}<br>{sev_emoji} {severity} | Risk {risk}/10 | Priority {priority}</summary>\n\n&nbsp;\n\n"
    card += f"**Risk**: {_risk_bar(risk)} **{risk}/10**\n\n"

    validation = r.get("validation", {})
    v_success = validation.get("success", False)
    validation.get("score", 0)
    v_icon = "🟢" if v_success else "🔴"
    v_status = "Validated" if v_success else "Not validated"

    policy_violations = validation.get("policy_violations", [])
    p_text = f"🔴 {len(policy_violations)} file-level violation" + ("s" if len(policy_violations) > 1 else "") if policy_violations else "🟢 Compliant"

    detection_conf = r.get("detection_confidence", 0.9)

    card += f"**Status**: {v_icon} {v_status} | **Patch confidence**: {confidence * 100:.0f}% | **Detection**: {detection_conf * 100:.0f}% | **Priority**: {priority} | **Policy**: {p_text}\n\n"

    if r.get("patch_suppressed"):
        supp_score = r.get("suppression_score", 0)
        card += f"ℹ️ **Patch suppressed** — best candidate scored too low ({supp_score:.2f}), so no automatic fix was produced.\n\n"

    evidence = r.get("evidence", {})
    rule_text = evidence.get("rule", "")
    rule_id = r.get("rule_id", "")
    if rule_text:
        card += f"**Evidence** ({rule_id}): {rule_text}\n\n"

    risk_rationale = r.get("llm_rationale") or r.get("risk_rationale", "")
    if risk_rationale:
        card += f"**Why this is a risk**\n\n{risk_rationale}\n\n"

    refs = " ".join(filter(None, [cwe_link, owasp_link]))
    if refs:
        card += f"**References**: {refs}\n\n"

    rb = _format_risk_breakdown(r)
    if rb:
        card += f"**Risk breakdown**\n\n{rb}\n"

    details = validation.get("details", {})
    sandbox_res = details.get("sandbox", {})
    test_results = validation.get("test_results", {})

    test_summary = parse_test_summary(test_results.get("output", ""))
    expected_failures = test_results.get("expected_failures") or []
    regression_failures = test_results.get("regression_failures") or []
    regression_explanation = _regression_explanation(test_results)

    if regression_explanation:
        card += f"**Regression tests**\n\n{regression_explanation}\n\n"
    else:
        if test_summary:
            count_parts = [f"{test_summary['passed']} passed"]
            if expected_failures:
                count_parts.append(f"{len(expected_failures)} expected")
            remaining_failed = test_summary["failed"] - len(expected_failures)
            if remaining_failed > 0:
                count_parts.append(f"{remaining_failed} failed")
            if test_summary.get("error"):
                count_parts.append(f"{test_summary['error']} error" + ("s" if test_summary["error"] != 1 else ""))
            count_parts.append(f"{test_summary['skipped']} skipped")
            card += f"ℹ️ Regression tests: {', '.join(count_parts)} (mode: docker)\n\n"
        elif test_results.get("mode") == "docker":
            card += "ℹ️ Test environment: docker\n\n"

        if expected_failures and not regression_failures:
            card += (
                f"ℹ️ *{len(expected_failures)} failing test(s) pin the removed vulnerabilities "
                f"({', '.join(expected_failures)}) — expected to fail after the fix, not regressions.*\n\n"
            )

        rebind_info = test_results.get("rebind") or {}
        if rebind_info.get("rebound"):
            mapping = " → ".join(f"{k} → {v}" for k, v in (rebind_info.get("rebound_map") or {}).items())
            if mapping:
                card += f"ℹ️ *Test imports rebound to patched module ({mapping}).*\n\n"

        mocked_env = test_results.get("mocked_env_vars") or []
        if mocked_env:
            card += f"ℹ️ *Sandbox mocked env vars: {', '.join(mocked_env)} — tests asserting the original values fail on substitution, not a patch regression.*\n\n"

        skip_reason = (test_results.get("error") or "").strip()
        if test_results.get("skipped") and skip_reason and skip_reason != "No test file":
            card += f"⏭️ *Regression tests skipped — {skip_reason}.*\n\n"

    infra_unavailable = (
        test_results.get("image_unavailable")
        or sandbox_res.get("image_unavailable")
    )
    if infra_unavailable and not test_results.get("skipped"):
        if validation.get("static_only"):
            card += (
                "ℹ️ *Static-only validation — Docker sandbox unavailable, so runtime "
                "execution and regression tests could not run (scans fail closed when "
                "Docker or the sandbox image is missing). Syntax, security re-scan, "
                "and policy checks completed statically. Build the image with: "
                "`docker build -f sandbox/Dockerfile.sandbox -t ai-risk-guard:sandbox .`*\n\n"
            )
        else:
            card += (
                "ℹ️ *Docker sandbox unavailable — sandbox validation could not run "
                "(scans fail closed when Docker or the sandbox image is missing). "
                "Build the image with: "
                "`docker build -f sandbox/Dockerfile.sandbox -t ai-risk-guard:sandbox .`*\n\n"
            )

    no_true_regressions = (
        bool(expected_failures)
        and not regression_failures
        and not test_results.get("skipped")
        and test_results.get("success") is True
    )

    if validation.get("validated_by") == "ci_runner":
        card += (
            "🤖 *Runtime validation completed on a GitHub Actions runner — the App's "
            "own Docker sandbox was unavailable at scan time, so sandbox execution "
            "and regression tests were re-run on a hosted runner and the evidence "
            "re-injected here.*\n\n"
        )

    if not regression_explanation:
        if no_true_regressions:
            card += f"✅ No regressions — {len(expected_failures)} test(s) pin the removed vulnerabilities and are expected to fail after the fix.\n\n"
        elif test_results.get("success") is False and not test_results.get("skipped") and not infra_unavailable:
            total_run = (test_summary["passed"] + test_summary["failed"]) if test_summary else 0
            err_text = "".join(filter(None, [
                test_results.get("error") or "",
                "\n",
                test_results.get("output") or "",
            ])).strip()
            if total_run == 0 and err_text:
                reason = _extract_collection_error(err_text)
                card += f"⚠️ *Tests could not run — {reason}*\n\n"
            elif regression_failures:
                card += (
                    f"⚠️ *Regression test failure — {len(regression_failures)} test(s) fail outside the fixed behavior: "
                    f"{', '.join(regression_failures)}.*\n\n"
                )
            else:
                card += "⚠️ *Regression test failure expected — tests were written for pre-patch code.*\n\n"

    items = patch_evaluation(r)
    if items:
        evals = " | ".join(f"{_GATE_ICON.get(i['status'], '')} {i['label']} ({i['status']})" for i in items)
        quality = r.get("quality_score", 0)
        quality_str = f" — Patch quality **{quality:.2f}**" if quality > 0 else ""
        card += f"**Patch evaluation**: {evals}{quality_str}\n\n"

    if shared_count > 1:
        card += f"ℹ️ *Patch and evaluation shared across {shared_count} findings in this file (single candidate per file).*\n\n"

    remediation = r.get("remediation", "")
    if remediation:
        card += f"**How to fix**\n\n{remediation}\n"

    card += "</details>\n"
    return card


def _format_compliance(results):
    """Render OWASP/CWE/policy aggregates as a collapsible section."""
    counts = compliance_counts(results)
    blocks = []
    if counts["owasp"]:
        rows = ["| Reference | Findings |", "|-----------|----------|"]
        rows += [f"| {k} | {v} |" for k, v in sorted(counts["owasp"].items())]
        blocks.append("**OWASP Top 10**\n\n" + "\n".join(rows))
    if counts["cwe"]:
        rows = ["| Reference | Findings |", "|-----------|----------|"]
        rows += [f"| {k} | {v} |" for k, v in sorted(counts["cwe"].items())]
        blocks.append("**CWE**\n\n" + "\n".join(rows))
    if not counts["policy_pass"]:
        violation_counts = collections.Counter(counts["policy_violations"])
        viol_lines = [f"{count}x: {violation}" for violation, count in violation_counts.most_common()]
        blocks.append("**Policy violations**\n\n" + "\n".join(viol_lines))
    else:
        blocks.append("**Policy**: ✅ No violations")
    return "<details><summary>🧾 Compliance</summary>\n\n" + "\n\n".join(blocks) + "\n\n</details>\n"


def _format_ist_timestamp(value: str) -> str:
    """Convert a stored UTC timestamp string to IST for display.

    SQLite stores ``scanned_at`` as UTC ``YYYY-MM-DD HH:MM:SS``. Returns the
    value unchanged when it cannot be parsed so display never breaks.
    """
    if not value:
        return ""
    dt = None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(value, fmt)  # noqa: DTZ007 - stored value is naive UTC, made aware below
            break
        except ValueError:
            continue
    if dt is None:
        return value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST).strftime("%Y-%m-%d %H:%M")


def _format_trend(previous):
    """Render the previous-scan comparison as a collapsible section."""
    if not previous:
        return ""
    findings_count = previous.get("findings_count", 0)
    max_risk = previous.get("max_risk", 0)
    scanned_at = previous.get("scanned_at", "")
    lines = [
        "| Metric | Previous scan |",
        "|--------|---------------|",
        f"| Findings | {findings_count} |",
        f"| Max risk | {max_risk}/10 |",
    ]
    if scanned_at:
        lines.append(f"| Scanned | {_format_ist_timestamp(scanned_at)} IST |")
    return "<details><summary>📈 Repository Trend</summary>\n\n" + "\n".join(lines) + "\n\n</details>\n"


def _format_header(repo_name, pr_number, action, scan_number, timestamp):
    """Dashboard-style header card."""
    status_icon = "❌" if action == "REQUEST_CHANGES" else "✅"
    repo_cell = repo_name or "—"
    pr_cell = str(pr_number) if pr_number else "—"
    status_cell = f"{status_icon} **{action}**" if action else "—"
    lines = [
        "# 🔐 AI RISK GUARD",
        "",
        f"> **Security Analysis Completed** | Scan {scan_number} | {timestamp}",
        "",
        "| Repository | Pull Request | Status |",
        "|------------|--------------|--------|",
        f"| {repo_cell} | {pr_cell} | {status_cell} |",
        "",
    ]
    return "\n".join(lines)


def _format_kpi(new_results, scan_duration):
    """KPI cards row: severity counts + scan duration."""
    counts = _severity_counts(new_results)
    duration = f"{scan_duration:.0f}s" if scan_duration is not None else "—"
    lines = [
        "| ⛔ Critical | 🔴 High | 🟡 Medium | 🟢 Low | ⏱ Duration |",
        "|:---:|:---:|:---:|:---:|:---:|",
        f"| **{counts['CRITICAL']}** | **{counts['HIGH']}** | **{counts['MEDIUM']}** | **{counts['LOW']}** | **{duration}** |",
    ]
    return "\n".join(lines)


def _format_security_health(security_score, max_risk, badge):
    """Security score health bar + max risk line."""
    emoji, label = _score_level(security_score)
    lines = [
        f"> 🎯 **Security Score** {_score_bar(security_score)} **{security_score}/100** | {emoji} {label}",
        f"> ⚠ **Max risk**: {_SEVERITY_EMOJI.get(badge, '')} {badge} {max_risk}/10",
    ]
    return "\n".join(lines)


def _format_decision_banner(action, total_new, informational=0):
    """Prominent decision line."""
    if action == "REQUEST_CHANGES":
        word = "vulnerability" if total_new == 1 else "vulnerabilities"
        return f"> ❌ **REQUEST CHANGES** — {total_new} {word} must be resolved"
    if total_new:
        word = "finding" if total_new == 1 else "findings"
        verb = "needs" if total_new == 1 else "need"
        return f"> ✅ **COMMENT** — {total_new} {word} {verb} review"
    if informational:
        word = "informational finding" if informational == 1 else "informational findings"
        return f"> ✅ **COMMENT** — {informational} {word} (no action required)"
    return "> ✅ **No vulnerabilities detected**"


def _format_footer(repo_name, pr_number, scan_duration):
    """Professional footer with version, duration, pipeline, and links."""
    duration = f"{scan_duration:.0f}s" if scan_duration is not None else "—"
    lines = [
        (
            f"🔐 **{TOOL_NAME}** v{TOOL_VERSION} | Rules **{RULES_VERSION}** | "
            f"Analysis: {SCAN_MODE} / {ANALYSIS_ENGINE} | Validator: {VALIDATOR} | "
            f"Generated in **{duration}**"
        ),
    ]
    if repo_name and pr_number:
        lines.append(f"✅ Check: `ai-risk-guard/validation` in [Checks](https://github.com/{repo_name}/pull/{pr_number}/checks) | 📊 Dashboard: local instance")
    else:
        lines.append("✅ Check: `ai-risk-guard/validation` in Checks | 📊 Dashboard: local instance")
    lines.append("💡 **Feedback**: React with 🚀 to accept a patch or 👎 to reject it.")
    return "\n".join(lines)


def format_report(results, scan_number: int = 1, repo_name: str | None = None, rate_limited: bool = False, action: str | None = None, pr_number: int | None = None, scan_duration: float | None = None, previous_scan_summary: dict | None = None, commit_sha: str | None = None, scan_mode: str | None = None, llm_summary: str | None = None):
    """Build a professional PR comment with collapsible finding cards."""
    timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")

    new_results = _sort_findings([r for r in results if r.get("vulnerability", {}).get("is_new", True)])
    legacy_results = _sort_findings([r for r in results if not r.get("vulnerability", {}).get("is_new", True)])

    # Silent (informational) findings are shown but never gate the decision.
    actionable_new = [r for r in new_results if not r.get("is_silent")]
    max_risk = max((r.get("risk", 0) for r in actionable_new), default=0.0)
    if action is None:
        max_allowed = config.risk.gating.max_allowed_risk
        human_review_above = config.risk.gating.auto_request_changes_above
        action = "REQUEST_CHANGES" if max_risk >= max_allowed or max_risk >= human_review_above else "COMMENT"

    report = ""
    report += f"<!-- ai-risk-guard scan:{scan_number} -->\n"
    report += "\n" + _format_header(repo_name, pr_number, action, scan_number, timestamp) + "\n"
    if llm_summary:
        report += f"\n> 💡 **Summary**: {llm_summary}\n"

    if rate_limited:
        report += (
            "\n> ⚠️ **AI Rate Limit** — Gemini API rate limit reached (429). "
            "Retries exhausted. "
            "Analysis was completed with deterministic methods only.\n"
        )

    if not results:
        report += "\n---\n"
        report += "\n## 📊 Dashboard\n"
        report += "\n" + _format_kpi([], scan_duration) + "\n"
        report += "\n" + _format_security_health(100.0, 0.0, "LOW") + "\n"
        report += "\n" + _format_decision_banner(action, 0) + "\n"
        report += "\n---\n"
        report += f"\n{_format_footer(repo_name, pr_number, scan_duration)}\n"
        report += f"\n{BOT_MARKER}\n"
        return report

    max_finding = max(actionable_new, key=lambda r: r.get("risk", 0), default=None)
    badge = _finding_severity(max_finding) if max_finding else "LOW"
    security_score = compute_security_score(results)

    report += "\n---\n"
    report += "\n## 📊 Dashboard\n"
    report += "\n" + _format_kpi(new_results, scan_duration) + "\n"
    report += "\n" + _format_security_health(security_score, max_risk, badge) + "\n"
    report += "\n" + _format_decision_banner(action, len(actionable_new), informational=len(new_results) - len(actionable_new)) + "\n"

    if new_results:
        report += "\n---\n"
        report += f"\n## 🛡 Findings ({len(new_results)})\n"
        if legacy_results:
            report += f"\n<sup>⚠️ {len(legacy_results)} legacy finding(s) also present</sup>\n"
        for i, r in enumerate(new_results):
            shared_count = _shared_candidate_count(new_results, r)
            report += _format_finding_card(r, index=i + 1, total=len(new_results), shared_count=shared_count)
            if i < len(new_results) - 1:
                report += "\n---\n"

    if legacy_results:
        report += "\n---\n"
        report += f"\n## 📋 Legacy Findings ({len(legacy_results)})\n"
        for i, r in enumerate(legacy_results):
            shared_count = _shared_candidate_count(legacy_results, r)
            report += _format_finding_card(r, is_legacy=True, index=i + 1, total=len(legacy_results), shared_count=shared_count)
            if i < len(legacy_results) - 1:
                report += "\n---\n"

    patched_files = {}
    for r in new_results:
        diff = r.get("diff")
        if not diff:
            continue
        vuln = r["vulnerability"]
        file_path = vuln.get("file_rel", vuln.get("file", "unknown"))
        if file_path not in patched_files:
            patched_files[file_path] = {"diff": diff, "findings": []}
        patched_files[file_path]["findings"].append({
            "type": vuln["type"],
            "line": vuln.get("line", 0),
            "quality_score": r.get("quality_score", 0),
            "candidate_id": r.get("candidate_id", "unknown"),
            "candidate_source": r.get("candidate_source", ""),
            "result": r,
        })

    if patched_files:
        report += "\n---\n"
        report += "\n## 🧠 Patch & Validation\n"
        total_fixes = sum(len(info['findings']) for info in patched_files.values())
        combined_score = max((f.get("quality_score", 0) for info in patched_files.values() for f in info['findings']), default=0)
        conf_str = f"{combined_score * 100:.0f}%" if combined_score > 0 else "—"
        fixes_str = f"{total_fixes} fix" if total_fixes == 1 else f"{total_fixes} fixes"
        files_str = "1 file" if len(patched_files) == 1 else f"{len(patched_files)} files"
        report += "\n| Patch Engine | Language | Patch quality | Fixes |\n"
        report += "|--------------|----------|-----------|-------|\n"
        report += f"| {PATCH_ENGINE} | {LANGUAGE} | {conf_str} | {fixes_str} in {files_str} |\n"
        for file_path, info in patched_files.items():
            file_score = max((f.get("quality_score", 0) for f in info['findings']), default=0)
            candidate_source = info['findings'][0].get("candidate_source", "") if info['findings'] else ""
            conf_str = f" | Patch quality {file_score * 100:.0f}%" if file_score > 0 else ""
            src_str = f" | via {candidate_source}" if candidate_source else ""
            fix_word = "fix" if len(info['findings']) == 1 else "fixes"
            report += f"\n<details><summary><b>{file_path}</b> — {len(info['findings'])} {fix_word}{conf_str}{src_str}</summary>\n\n<br>\n\n"
            hunks = extract_targeted_hunks(info["diff"], info["findings"])
            if hunks:
                report += f"```diff\n{hunks}\n```\n"
            else:
                report += f"```diff\n{info['diff']}\n```\n"
            first_result = info['findings'][0].get("result") if info['findings'] else None
            first_test_results = ((first_result or {}).get("validation") or {}).get("test_results") or {}
            if first_test_results and _regression_explanation(first_test_results):
                details_block = _format_regression_details(first_result)
                if details_block:
                    report += f"\n<details><summary>🧪 Regression test details</summary>\n\n{details_block}\n\n</details>\n"
            report += "</details>\n"

    compliance_section = _format_compliance(results)
    if compliance_section:
        report += "\n---\n"
        report += "\n" + compliance_section

    trend_section = _format_trend(previous_scan_summary)
    if trend_section:
        report += "\n---\n"
        report += "\n" + trend_section

    report += "\n---\n"
    report += "\n" + _format_footer(repo_name, pr_number, scan_duration) + "\n"
    report += f"\n{BOT_MARKER}\n"

    return report


def generate_sarif(findings, file_path=None, commit_sha=None, scan_duration: float = 0.0):
    """
    Generate SARIF output from findings.
    
    Args:
        findings: List of vulnerability findings (dicts)
        file_path: Optional file path to use for the analysis
        commit_sha: Optional commit SHA for unique runAutomationDetails.id
        scan_duration: Wall-clock duration of the scan in seconds
        
    Returns:
        SARIF JSON string
    """
    if not findings:
        analysis_result = build_analysis_result([], file_path or "unknown", scan_duration)
        return sarif_generator.generate_json(analysis_result, commit_sha)
    
    actual_file = file_path or findings[0].get("vulnerability", {}).get("file", "unknown")
    analysis_result = build_analysis_result(findings, actual_file, scan_duration)
    
    logger.info(f"Generating SARIF for {len(findings)} findings, file={actual_file}", "GITHUB")
    return sarif_generator.generate_json(analysis_result, commit_sha)


def check_all_alerts_dismissed(repository, access_token, sarif_output, pr_number=None):
    """Check if all alerts in the current SARIF have already been dismissed in GitHub UI.

    Queries the Code Scanning Alerts API for dismissed alerts matching this PR.
    If every rule ID in the current SARIF appears in the dismissed set, the upload
    can be skipped — the user has already reviewed and dismissed them.
    """
    try:
        sarif = json.loads(sarif_output)
        results = sarif.get("runs", [{}])[0].get("results", [])
        if not results:
            return True

        current_rules = {r.get("ruleId", "") for r in results}

        params = {"state": "dismissed", "per_page": 100}
        if pr_number:
            params["pr"] = pr_number

        headers = _github_headers(access_token)
        url = f"https://api.github.com/repos/{repository}/code-scanning/alerts"
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code != 200:
            return False

        dismissed = response.json()
        if not isinstance(dismissed, list):
            return False

        dismissed_rules = {a.get("rule", {}).get("id", "") for a in dismissed}

        if current_rules.issubset(dismissed_rules):
            logger.info("All findings match previously dismissed alerts — skipping SARIF upload", "GITHUB")
            return True
        return False
    except Exception as e:
        logger.warning(f"Dismissed-alert check failed: {e}, proceeding with upload", "GITHUB")
        return False


@retry(
    max_attempts=3,
    base_delay=2.0,
    backoff=2.0,
    max_delay=30.0,
    jitter=True,
    retryable_exceptions=(
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
        RateLimitError,
    ),
    on_retry=lambda exc, attempt, delay: logger.warning(
        f"SARIF upload attempt {attempt} failed: {exc}, retrying in {delay:.1f}s", "GITHUB"
    ),
)
def upload_sarif_to_code_scanning(repository, pr_number, access_token, sarif_output, commit_sha):
    """
    Upload SARIF output to GitHub Code Scanning API.

    Posts gzip+base64 encoded SARIF to POST /repos/{owner}/{repo}/code-scanning/sarifs.
    Results appear natively in the Security tab with alerts, annotations, and dismiss flow.

    Implements exponential backoff retry (3 attempts) for transient failures
    and handles 429 rate limits with Retry-After header.

    Args:
        repository: Full repo name (owner/repo)
        pr_number: Pull request number (for ref construction)
        access_token: GitHub installation token with security_events:write
        sarif_output: SARIF JSON string
        commit_sha: SHA of the head commit of the PR
    """
    try:
        logger.info("Uploading SARIF to GitHub Code Scanning API", "GITHUB")

        # Gzip compress the SARIF JSON
        compressed = gzip.compress(sarif_output.encode("utf-8"))
        encoded = base64.b64encode(compressed).decode("ascii")

        url = (
            f"https://api.github.com/repos/"
            f"{repository}/code-scanning/sarifs"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }

        payload = {
            "commit_sha": commit_sha,
            "ref": f"refs/pull/{pr_number}/head",
            "sarif": encoded,
            "checkout_uri": f"https://github.com/{repository}",
        }

        logger.info(
            f"SARIF payload: {len(sarif_output)} bytes, "
            f"ref={payload['ref']}",
            "GITHUB"
        )

        response = requests.post(url, json=payload, headers=headers, timeout=60)

        if response.status_code == 202:
            data = response.json()
            analysis_id = data.get('id')
            logger.info(f"SARIF uploaded: {analysis_id}", "GITHUB")
            logger.info(f"SARIF upload response: {json.dumps(data)}", "GITHUB")
            _check_sarif_status(repository, analysis_id, access_token)
        elif response.status_code == 422:
            logger.info(f"SARIF already processed for this commit (duplicate ignored): {response.text[:200]}", "GITHUB")
            return
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "5")
            logger.warning(f"SARIF rate limited, retry after {retry_after}s", "GITHUB")
            raise RateLimitError(retry_after=float(retry_after))
        else:
            msg = f"SARIF upload error: {response.status_code} {response.text[:300]}"
            logger.error(msg, "GITHUB")
            raise RuntimeError(msg)

    except Exception as e:
        logger.error(f"Failed to upload SARIF to Code Scanning: {e}", "GITHUB")
        raise


def _check_sarif_status(repository, sarif_id, access_token):
    """Poll SARIF processing status after upload and log any processing errors."""
    try:
        url = f"https://api.github.com/repos/{repository}/code-scanning/sarifs/{sarif_id}"
        headers = _github_headers(access_token)
        for _attempt in range(3):
            response = requests.get(url, headers=headers, timeout=15)
            _raise_on_rate_limit(response)
            if response.status_code == 200:
                status = response.json()
                processing_status = status.get("processing_status", "unknown")
                logger.info(f"SARIF status: {processing_status}", "GITHUB")
                if status.get("errors"):
                    logger.warning(f"SARIF processing errors: {status['errors']}", "GITHUB")
                elif status.get("warnings"):
                    logger.warning(f"SARIF processing warnings: {status['warnings']}", "GITHUB")
                if processing_status != "pending":
                    return
                time.sleep(3)
            else:
                logger.warning(
                    f"SARIF status check returned {response.status_code}: {response.text[:200]}",
                    "GITHUB"
                )
                return
        logger.info("SARIF still processing after polling, status is informational", "GITHUB")
    except RateLimitError:
        raise
    except Exception as e:
        logger.warning(f"SARIF status check failed: {e}", "GITHUB")


def _finding_check_status(result: dict) -> tuple[str, str]:
    """Classify a single finding for the Check Run conclusion.

    Returns ``(status, note)`` where status is one of ``ok``, ``failed``,
    or ``inconclusive``.

    Signals used (all-4-signals, informational / non-gating):
      - ``validation.test_results.success`` — regression tests passed
      - ``validation.details.syntax.success`` — patched code is syntactically valid
      - ``validation.details.rescan.success`` — security re-scan is clean
      - ``patch_suppressed`` — no patch confirmation available
    """
    vuln_type = (result.get("vulnerability") or {}).get("type", "UNKNOWN")
    label = f"{vuln_type}: {result.get('rule_id', '')}".strip(" :")

    validation = result.get("validation") or {}
    details = validation.get("details") or {}
    test_results = validation.get("test_results") or {}

    if result.get("patch_suppressed"):
        return "inconclusive", f"{label} patch suppressed (no confirmation)"

    tests_passed = test_results.get("success") is True
    tests_skipped = test_results.get("skipped") is True
    infra_unavailable = bool(
        test_results.get("image_unavailable")
        or test_results.get("mode") == "unavailable"
    )

    syntax_ok = (details.get("syntax") or {}).get("success") is True
    rescan_ok = (details.get("rescan") or {}).get("success") is True

    if tests_skipped:
        return "inconclusive", f"{label} tests skipped (no confirmation)"
    if infra_unavailable:
        if validation.get("static_only"):
            return "inconclusive", f"{label} validated statically only (Docker unavailable)"
        return "inconclusive", f"{label} sandbox validation could not run (Docker unavailable)"
    if test_results.get("success") is False:
        return "failed", f"{label} applied patch failed regression tests"
    if not tests_passed:
        return "inconclusive", f"{label} test results unavailable or skipped"
    if not syntax_ok or not rescan_ok:
        return "failed", f"{label} applied patch did not clear syntax/re-scan"
    return "ok", f"{label} tests passed, syntax ok, re-scan clean"


def _check_conclusion(results: list, gating: bool = True) -> tuple[str, str]:
    """Compute the Check Run conclusion and Markdown summary from findings.

    Conclusion logic:
      - ``success`` — every finding has an applied patch whose regression tests
        passed, syntax is valid, and the security re-scan is clean.
      - ``neutral`` — any finding is inconclusive (tests skipped, Docker
        unavailable, or the patch was suppressed). Never blocks.
      - ``failure`` — a patch was applied but tests failed, or the applied
        patch did not clear the re-scan or syntax gate.

    When ``gating`` is False the check is informational only: a ``failure``
    is downgraded to ``neutral`` so it never blocks merges.

    Empty results → ``success`` (clean scan).
    """
    if not results:
        return "success", "No security vulnerabilities detected in this pull request."

    statuses = [_finding_check_status(r) for r in results]
    lines = []
    for idx, (status, note) in enumerate(statuses, 1):
        icon = {"ok": "✅", "failed": "❌", "inconclusive": "⚠️"}.get(status, "•")
        lines.append(f"- {icon} `#{idx}` {note}")

    if any(s == "failed" for s, _ in statuses):
        conclusion = "failure"
    elif any(s == "inconclusive" for s, _ in statuses):
        conclusion = "neutral"
    else:
        conclusion = "success"

    if not gating and conclusion == "failure":
        conclusion = "neutral"

    summary = (
        f"### AI Risk Guard — patch validation ({conclusion})\n\n"
        f"**{len(results)}** finding(s) reviewed.\n\n"
        + "\n".join(lines)
        + (
            "\n\n> Informational check. It reports validation evidence and never blocks merges."
            if conclusion != "success"
            else ""
        )
    )
    return conclusion, summary


def create_check_run(repository, pr_number, access_token, results, commit_sha):
    """Create an informational GitHub Check Run summarizing patch validation.

    Posts a completed check to ``POST /repos/{owner}/{repo}/check-runs`` so the
    PR's Checks tab shows live ``success`` / ``neutral`` / ``failure`` evidence
    for the actual changed code. The conclusion honors ``config.app.checks``:
    with gating disabled (the default), failures are reported as ``neutral`` so
    the check is informational / non-gating and never blocks the merge.

    Non-2xx responses are logged and ignored; the function never raises
    (mirrors ``upload_sarif_to_code_scanning``'s graceful degradation).
    """
    try:
        check_name = getattr(config.app.checks, "name", "ai-risk-guard/validation")
        gating = getattr(config.app.checks, "gating", False)
        conclusion, summary = _check_conclusion(results, gating=gating)

        url = f"https://api.github.com/repos/{repository}/check-runs"
        headers = _github_headers(access_token)
        payload = {
            "name": check_name,
            "head_sha": commit_sha,
            "status": "completed",
            "conclusion": conclusion,
            "completed_at": datetime.now(UTC).isoformat(),
            "output": {
                "title": "AI Risk Guard patch validation",
                "summary": summary,
            },
        }

        logger.info(
            f"Creating check run for {repository} #{pr_number} on {commit_sha[:12]} → {conclusion}",
            "GITHUB",
        )
        response = requests.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code in (200, 201):
            check_id = response.json().get("id")
            logger.info(f"Check run created: {check_id}", "GITHUB")
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "5")
            logger.warning(f"Check run rate limited, retry after {retry_after}s", "GITHUB")
        else:
            logger.warning(
                f"Check run creation failed: {response.status_code} {response.text[:300]}",
                "GITHUB",
            )
    except Exception as e:
        logger.warning(f"Check run creation failed: {e}", "GITHUB")


def _github_headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }


@retry(**_RETRY_KWARGS, on_retry=_retry_logger)
def find_existing_bot_comment(repository, pr_number, access_token) -> tuple[int, int] | None:
    """
    Find an existing bot comment on the PR by searching for ``BOT_MARKER``.

    Paginates through all comment pages (up to 1000 comments) to handle
    PRs with many comments.  Returns ``(comment_id, scan_number)`` of the
    **most recent** bot comment, or ``None`` if no bot comment exists.
    """
    try:
        page = 1
        per_page = 100
        max_pages = 10  # safety limit (1000 comments)

        matches = []

        while page <= max_pages:
            url = (
                f"https://api.github.com/repos/"
                f"{repository}/issues/{pr_number}/comments"
                f"?per_page={per_page}&page={page}"
            )
            headers = _github_headers(access_token)
            response = requests.get(url, headers=headers, timeout=15)
            _raise_on_rate_limit(response)
            if response.status_code != 200:
                return None

            comments = response.json()
            if not comments:
                break

            for comment in comments:
                if BOT_MARKER in comment.get("body", ""):
                    scan_number = _extract_scan_number(comment.get("body", ""))
                    matches.append((comment["id"], scan_number, comment.get("created_at", "")))
            page += 1

        if not matches:
            return None

        if len(matches) > 1:
            matches.sort(key=lambda m: m[2], reverse=True)
            stale = matches[1:]
            for sid, _, _ in stale:
                _delete_pr_comment(repository, sid, access_token)

        return (matches[0][0], matches[0][1])
    except RateLimitError:
        raise
    except Exception as e:
        logger.warning(f"find_existing_bot_comment failed: {e}")
        return None


@retry(**_RETRY_KWARGS, on_retry=_retry_logger)
def _delete_pr_comment(repository, comment_id, access_token):
    """Delete a PR comment by ID, ignoring errors."""
    try:
        url = (
            f"https://api.github.com/repos/"
            f"{repository}/issues/comments/{comment_id}"
        )
        headers = _github_headers(access_token)
        response = requests.delete(url, headers=headers, timeout=10)
        _raise_on_rate_limit(response)
    except RateLimitError:
        raise
    except Exception as e:
        logger.warning(f"Failed to delete PR comment {comment_id}: {e}")


@retry(**_RETRY_KWARGS, on_retry=_retry_logger)
def update_pr_comment(repository, comment_id, access_token, body: str) -> bool:
    """
    Update an existing PR comment via PATCH.

    Returns True on success.
    """
    try:
        url = (
            f"https://api.github.com/repos/"
            f"{repository}/issues/comments/{comment_id}"
        )
        headers = _github_headers(access_token)
        response = requests.patch(url, json={"body": body}, headers=headers, timeout=15)
        _raise_on_rate_limit(response)
        if response.status_code in (200, 201):
            logger.info("PR comment updated successfully", "GITHUB")
            return True
        logger.error(
            f"GitHub API error updating comment: {response.status_code} {response.text[:200]}",
            "GITHUB",
        )
        return False
    except RateLimitError:
        raise
    except Exception as e:
        logger.error(f"GitHub comment update error: {e}", "GITHUB")
        return False



@retry(**_RETRY_KWARGS, on_retry=_retry_logger)
def remove_pr_labels(repository, pr_number, access_token, labels):
    """Remove one or more labels from a PR via DELETE per label."""
    for label in labels:
        try:
            url = (
                f"https://api.github.com/repos/"
                f"{repository}/issues/{pr_number}/labels/{label}"
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            }
            response = requests.delete(url, headers=headers, timeout=10)
            _raise_on_rate_limit(response)
            # 200 = removed, 404 = already absent — both acceptable
            if response.status_code not in (200, 404):
                logger.warning(
                    f"Label removal failed for '{label}': {response.status_code}",
                    "GITHUB",
                )
        except RateLimitError:
            raise
        except Exception as e:
            logger.warning(f"Label removal error for '{label}': {e}", "GITHUB")


@retry(**_RETRY_KWARGS, on_retry=_retry_logger)
def set_pr_labels(repository, pr_number, access_token, max_risk):
    """
    Set security risk labels on a PR via PUT /repos/{owner}/{repo}/issues/{pr}/labels.

    Always adds ``ai-risk-guard`` label.
    Adds a risk-based label: ``security-risk-high``, ``security-risk-medium``, ``security-risk-low``.
    Removes any existing risk labels first to avoid conflicts.

    Args:
        repository: Full repo name (owner/repo)
        pr_number: Pull request number
        access_token: GitHub installation token
        max_risk: Highest risk score from the scan
    """
    try:
        if not getattr(config.app.github_app, "set_pr_labels", True):
            return

        # Remove old risk labels before applying new ones
        existing_risk = [
            f"{RISK_LABEL_PREFIX}high",
            f"{RISK_LABEL_PREFIX}medium",
            f"{RISK_LABEL_PREFIX}low",
        ]
        remove_pr_labels(repository, pr_number, access_token, existing_risk)

        new_label = _risk_label_name(max_risk)
        labels = ["ai-risk-guard", new_label]

        url = (
            f"https://api.github.com/repos/"
            f"{repository}/issues/{pr_number}/labels"
        )
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }
        response = requests.put(url, json={"labels": labels}, headers=headers, timeout=10)
        _raise_on_rate_limit(response)
        if response.status_code in (200, 201):
            logger.info(f"PR labels set: {labels}", "GITHUB")
        else:
            logger.error(
                f"Label set failed: {response.status_code} {response.text[:200]}",
                "GITHUB",
            )
    except RateLimitError:
        raise
    except Exception as e:
        logger.error(f"Label set error: {e}", "GITHUB")


MAX_COMMENT_LENGTH = 65000


def _truncate_report(report: str, max_len: int = MAX_COMMENT_LENGTH, repo_name: str | None = None, pr_number: int | None = None) -> str:
    """Truncate the patches section if the report exceeds GitHub's comment size limit."""
    if len(report) <= max_len:
        return report

    patches_marker = "\n---\n\n## 🧠 Patch & Validation\n"
    if patches_marker not in report:
        return report[:max_len - 100] + "\n\n> ⚠️ Report truncated due to comment size limit.\n" + f"\n{BOT_MARKER}\n"

    before_patches = report.split(patches_marker)[0] + patches_marker
    remaining = max_len - len(before_patches) - 100
    if remaining <= 0:
        return report[:max_len - 100] + "\n\n> ⚠️ Report truncated due to comment size limit.\n" + f"\n{BOT_MARKER}\n"

    # Build truncated patches section: keep the metadata table + first patch only
    patches_content = report.split(patches_marker)[1]
    patch_blocks = patches_content.split("\n<details>")
    kept = patch_blocks[:2]
    rest_count = len(patch_blocks) - 2
    truncated = "\n<details>".join(kept)
    if rest_count > 0:
        truncated += f"\n\n> ⚠️ {rest_count} patch(es) truncated due to comment size limit."

    report = before_patches + truncated + "\n\n---\n\n" + _format_footer(repo_name, pr_number, None) + f"\n\n{BOT_MARKER}\n"

    if len(report) > max_len:
        report = report[:max_len - 100] + "\n\n> ⚠️ Report truncated due to comment size limit.\n" + f"\n{BOT_MARKER}\n"

    return report


def _fetch_previous_scan_summary(repo_name, pr_number=None):
    """Best-effort previous scan summary for the repository trend section."""
    try:
        from utils import db
        previous = db.get_previous_scan_summary(repo_name, exclude_pr=pr_number)
        return previous or None
    except Exception as e:
        logger.warning(f"Failed to fetch previous scan summary: {e}", "GITHUB")
        return None


@retry(**_RETRY_KWARGS, on_retry=_retry_logger)
def post_pr_comment(repository, pr_number, results, access_token, rate_limited: bool = False, action: str | None = None, scan_start: float | None = None, commit_sha: str | None = None, scan_mode: str | None = None, llm_summary: str | None = None):
    """Post (or update) the bot security report on a PR.

    Returns the comment id of the resulting bot comment (or None when the
    report was suppressed by config). Also records the comment in the
    ``bot_comments`` table so the reaction poller can harvest 🚀/👎 feedback.
    """
    try:
        logger.info("Posting GitHub PR comment", "GITHUB")

        should_comment = getattr(config.app.sarif, "comment_on_pr", True)
        if not should_comment:
            return None

        should_update = getattr(config.app.sarif, "update_existing_comment", True)
        existing = None
        if should_update:
            existing = find_existing_bot_comment(repository, pr_number, access_token)

        scan_duration = round(time.time() - scan_start, 1) if scan_start else None
        previous_scan = _fetch_previous_scan_summary(repository, pr_number)

        if existing is not None:
            comment_id, scan_number = existing
            next_scan = scan_number + 1
            report = format_report(results, scan_number=next_scan, repo_name=repository, rate_limited=rate_limited, action=action, pr_number=pr_number, scan_duration=scan_duration, previous_scan_summary=previous_scan, commit_sha=commit_sha, scan_mode=scan_mode, llm_summary=llm_summary)
            report = _truncate_report(report, repo_name=repository, pr_number=pr_number)
            update_pr_comment(repository, comment_id, access_token, report)
        else:
            report = format_report(results, scan_number=1, repo_name=repository, rate_limited=rate_limited, action=action, pr_number=pr_number, scan_duration=scan_duration, previous_scan_summary=previous_scan, commit_sha=commit_sha, scan_mode=scan_mode, llm_summary=llm_summary)
            report = _truncate_report(report, repo_name=repository, pr_number=pr_number)
            url = (
                f"https://api.github.com/repos/"
                f"{repository}/issues/"
                f"{pr_number}/comments"
            )
            headers = _github_headers(access_token)
            response = requests.post(url, json={"body": report}, headers=headers, timeout=15)
            _raise_on_rate_limit(response)

            if response.status_code in (200, 201):
                logger.info("PR comment posted successfully", "GITHUB")
                comment_id = response.json().get("id")
            else:
                logger.error(
                    f"GitHub API error: {response.status_code} {response.text[:200]}",
                    "GITHUB",
                )
                comment_id = None

        if comment_id:
            try:
                record_bot_comment(comment_id, repository, pr_number)
            except Exception as e:
                logger.warning(f"Failed to record bot comment {comment_id}: {e}", "GITHUB")
        return comment_id

    except Exception as e:
        logger.error(f"GitHub reporter error: {e}", "GITHUB")
        raise


