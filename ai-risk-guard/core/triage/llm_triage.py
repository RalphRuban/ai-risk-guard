"""
core/triage/llm_triage.py

LLM-backed refinements layered over the deterministic pipeline:

  - ``triage_vulnerabilities``  — confirm/refute low-confidence detections so
    rejected findings become non-gating instead of blocking PRs.
  - ``generate_explanations``   — context-aware "why this is a risk" text.
  - ``summarize_analysis``      — one-line PR summary for the report header.

All methods FAIL OPEN: when Gemini is unavailable, rate-limited, or returns
unparseable output, the deterministic results are returned unchanged.
"""

import re

from core.config import config
from core.llm.gemini_client import GeminiClient
from core.metadata.vuln_metadata import SILENT_TYPES
from core.reporting.summary import DETECTION_CONFIDENCE, parse_test_summary
from utils.logger import logger

_VERDICT_RE = re.compile(
    r"^\s*(\d+)\s*[:.)]\s*(CONFIRMED|REJECTED|UNCERTAIN)\b\s*(?:[:-]\s*(.*))?$",
    re.IGNORECASE,
)

_EXPLANATION_RE = re.compile(r"^\s*(\d+)\s*[:.)]\s*(.+)$", re.IGNORECASE)


class LLMTriage:
    """LLM-backed analysis refinements, isolated per request for thread safety."""

    def __init__(self):
        self.client = GeminiClient()

    @property
    def enabled(self) -> bool:
        return self.client.enabled

    # ------------------------------------------------------------------
    # Triage
    # ------------------------------------------------------------------

    def triage_vulnerabilities(self, vulnerabilities: list[dict]) -> list[dict]:
        """Confirm/refute low-confidence deterministic detections.

        Only findings whose per-type detection confidence is below
        ``config.app.triage.min_detection_confidence`` (and which are not
        already silent/informational) are sent to Gemini, in one batched call
        per file. Rejected findings are marked ``unconfirmed=True`` so the risk
        agent treats them as non-gating.

        Returns the (possibly mutated) input list.
        """
        if not config.app.triage.enabled or not self.enabled:
            return vulnerabilities

        candidates = self._triage_candidates(vulnerabilities)
        if not candidates:
            return vulnerabilities

        prompt = self._build_triage_prompt(candidates)
        response = self.client.cached_generate(prompt)
        if not response:
            logger.info("LLM triage unavailable — keeping deterministic findings", "TRIAGE")
            return vulnerabilities

        verdicts, reasons = self._parse_verdicts(response, len(candidates))
        for index, vuln in enumerate(candidates):
            verdict = verdicts.get(index, "UNCERTAIN")
            reason = reasons.get(index, "")
            vuln["triage"] = {"verdict": verdict.lower(), "reason": reason}
            if verdict == "REJECTED":
                vuln["unconfirmed"] = True
                self._observe_verdict("rejected")
                logger.info(
                    f"LLM triage REJECTED {vuln.get('type')}@{vuln.get('line')} — non-gating ({reason})",
                    "TRIAGE",
                )
            elif verdict == "CONFIRMED":
                self._observe_verdict("confirmed")
                logger.info(
                    f"LLM triage CONFIRMED {vuln.get('type')}@{vuln.get('line')} ({reason})",
                    "TRIAGE",
                )
            else:
                self._observe_verdict("uncertain")
        return vulnerabilities

    def _triage_candidates(self, vulnerabilities: list[dict]) -> list[dict]:
        threshold = config.app.triage.min_detection_confidence
        return [
            v for v in vulnerabilities
            if v.get("type") not in SILENT_TYPES
            and self._detection_confidence(v) < threshold
        ]

    def _detection_confidence(self, vuln: dict) -> float:
        return float(vuln.get("detection_confidence") or DETECTION_CONFIDENCE.get(vuln.get("type", ""), 0.9))

    def _build_triage_prompt(self, candidates: list[dict]) -> str:
        lines = []
        for index, vuln in enumerate(candidates):
            snippet = (vuln.get("code") or "").strip() or (vuln.get("message") or "")
            lines.append(
                f"{index}. Type: {vuln.get('type')} | Line: {vuln.get('line', '?')} | "
                f"Code: `{snippet[:200]}` | Message: {vuln.get('message', '')}"
            )
        return f"""
You are a meticulous security reviewer. The deterministic scanner flagged the
following Python findings. For each, decide whether it is a REAL exploitable
vulnerability or a FALSE POSITIVE (e.g. the input is a constant, the value is
sanitized earlier, the sink is unreachable, or the code is sample/demo).

{chr(10).join(lines)}

Reply with exactly one line per finding, in order, using this format:
INDEX: CONFIRMED|REJECTED|UNCERTAIN: one-line reason

- CONFIRMED when the finding is a genuine risk in this exact code.
- REJECTED when it is clearly a false positive in this exact code.
- UNCERTAIN when you cannot tell from the snippet.
"""

    @staticmethod
    def _parse_verdicts(response: str, expected_count: int) -> tuple[dict[int, str], dict[int, str]]:
        verdicts: dict[int, str] = {}
        reasons: dict[int, str] = {}
        for line in response.splitlines():
            match = _VERDICT_RE.match(line.strip())
            if not match:
                continue
            index = int(match.group(1))
            if index < 0 or index >= expected_count:
                continue
            verdicts[index] = match.group(2).upper()
            reasons[index] = (match.group(3) or "").strip()
        return verdicts, reasons

    # ------------------------------------------------------------------
    # Explanations
    # ------------------------------------------------------------------

    def generate_explanations(self, vulnerabilities: list[dict], original_code: str) -> dict[int, str]:
        """Return ``{index: explanation}`` for each finding, or ``{}`` on failure.

        ``index`` aligns with the order of ``vulnerabilities``.
        """
        if not config.app.explainer.enabled or not self.enabled or not vulnerabilities:
            return {}

        findings = []
        for index, vuln in enumerate(vulnerabilities):
            snippet = (vuln.get("code") or "").strip()
            findings.append(
                f"{index}. Type: {vuln.get('type')} | Line: {vuln.get('line', '?')} | "
                f"Code: `{snippet[:200]}`"
            )

        prompt = f"""
You are a senior security engineer explaining findings to a developer.
Explain in 2-3 sentences why each of these code patterns is a security risk,
referencing the actual code, and give one sentence of remediation.

{chr(10).join(findings)}

Reply with exactly one numbered line per finding, in order:
INDEX. explanation and remediation

For example:
0. Executing an OS command built from an unvalidated variable allows an attacker to inject arbitrary shell commands. Use subprocess.run with shell=False and pass arguments as a list.
"""
        response = self.client.cached_generate(prompt)
        if not response:
            return {}

        explanations: dict[int, str] = {}
        for line in response.splitlines():
            match = _EXPLANATION_RE.match(line.strip())
            if not match:
                continue
            index = int(match.group(1))
            if 0 <= index < len(vulnerabilities):
                explanations[index] = match.group(2).strip()
        return explanations

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summarize_analysis(self, findings: list[dict]) -> str | None:
        """Return a one-sentence PR summary, or ``None`` when unavailable.

        ``findings`` are the final result dicts (with ``vulnerability``, ``diff``).
        """
        if not config.app.summary.enabled or not self.enabled or not findings:
            return None

        lines = []
        for result in findings:
            vuln = result.get("vulnerability") or {}
            file_path = vuln.get("file_rel", vuln.get("file", "?"))
            lines.append(
                f"- {vuln.get('type', '?')} in {file_path}:{vuln.get('line', '?')} "
                f"(risk {result.get('risk', 0):.1f})"
            )

        prompt = f"""
You are a security tool summarizing findings for a pull request.
Write ONE concise sentence for a developer describing what was found and the
state of the patches (applied / suppressed).

Findings:
{chr(10).join(lines)}

Reply with only the single sentence, no preamble, no markdown.
"""
        response = self.client.cached_generate(prompt)
        if not response:
            return None
        text = response.strip()
        return text or None

    # ------------------------------------------------------------------
    # Regression-test explanation
    # ------------------------------------------------------------------

    def explain_regression_tests(self, test_results: dict) -> str | None:
        """Return a short plain-language explanation of the regression results.

        Called by the PR reporter so the technical ``ℹ️`` block (test counts,
        pinned test names, mocked env vars, rebind info) shown on every finding
        of a file can be replaced with one readable paragraph.

        Fails open: returns ``None`` when disabled, when Gemini is unavailable,
        or when the payload has nothing meaningful to explain — callers then
        render the deterministic block verbatim.
        """
        if not config.app.regression_explain.enabled or not self.enabled or not test_results:
            return None

        summary = parse_test_summary(test_results.get("output", ""))
        expected_failures = test_results.get("expected_failures") or []
        regression_failures = test_results.get("regression_failures") or []
        mocked_env = test_results.get("mocked_env_vars") or []
        rebind = (test_results.get("rebind") or {}).get("rebound_map") or {}
        skipped = test_results.get("skipped") is True
        success = test_results.get("success") is True
        mode = test_results.get("mode") or "unknown"

        meaningful = bool(summary or expected_failures or regression_failures or mocked_env or rebind)
        if not meaningful:
            return None

        max_names = config.app.regression_explain.max_test_names_in_prompt

        def _clip(names: list) -> str:
            names = list(names)[:max_names]
            text = ", ".join(names)
            if len(names) >= max_names:
                text += ", ..."
            return text

        facts = [
            f"- Outcome: {'passed' if success else ('skipped' if skipped else 'failed')} (mode: {mode})",
        ]
        if summary:
            facts.append(f"- Counts: {summary['passed']} passed, {summary['failed']} failed, {summary['skipped']} skipped")
        if expected_failures:
            facts.append(f"- Expected failures (pin removed vulnerabilities): {_clip(expected_failures)}")
        if regression_failures:
            facts.append(f"- Unexpected regression failures: {_clip(regression_failures)}")
        if mocked_env:
            facts.append(f"- Sandbox mocked env vars: {', '.join(mocked_env)}")
        if rebind:
            mapping = ", ".join(f"{k} -> {v}" for k, v in rebind.items())
            facts.append(f"- Test imports rebound to the patched module: {mapping}")

        prompt = f"""
You are a security tool explaining automated regression-test results to a
developer reviewing a pull request. A sandbox ran the project's tests against
an auto-generated security patch.

The facts below are technical. Write a SHORT, readable explanation in 2-4
sentences, in plain developer language, with NO markdown, NO bullet lists, and
no preamble such as "Here is".

Rules:
- A developer must instantly understand whether the fix is safe and whether the
  tests prove it.
- Failing tests listed as "Expected failures (pin removed vulnerabilities)" are
  GOOD: they fail because the patch removed the vulnerability they asserted.
  Say this clearly and reassuringly.
- "Unexpected regression failures" are BAD: call them out explicitly.
- Sandbox mocked env vars just mean the test environment substituted secrets
  with dummy values; mention them only when the results depend on them.
- Test-import rebinding means the tests were pointed at the patched module.
- Never claim tests passed when they were skipped or did not run.

Facts:
{chr(10).join(facts)}
"""
        response = self.client.cached_generate(prompt)
        if not response:
            return None
        text = response.strip()
        return text or None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _observe_verdict(verdict: str) -> None:
        try:
            from app.metrics import triage_verdicts_total
            triage_verdicts_total.labels(verdict=verdict).inc()
        except ImportError:
            pass
