"""
Risk Agent.
Responsible for risk assessment, confidence scoring, and metric extraction.
"""

import difflib
import logging
import os
from typing import Any

from core.agents.base_agent import BaseAgent
from core.confidence.confidence import calculate_confidence
from core.config import config
from core.metadata.vuln_metadata import RULE_IDS, SILENT_TYPES, VULN_METADATA
from core.policy.policy_engine import PolicyEngine
from core.quality.patch_scorer import PatchScorer
from core.reporting.explainer import generate_evidence
from core.reporting.summary import (
    DETECTION_CONFIDENCE,
    compute_priority,
    extract_secret_value,
    shannon_entropy,
)
from core.risk.metrics_extractor import extract_metrics
from core.risk.risk_engine import calculate_risk, effective_severity, explain_risk

log = logging.getLogger("ai_risk_guard.risk_agent")

class RiskAgent(BaseAgent):
    """
    Agent specialized in risk analysis and confidence scoring.
    Now includes Policy-Aware risk scoring.
    """
    
    def __init__(self):
        super().__init__("Risk")
        self.policy_engine = PolicyEngine()
        self.patch_scorer = PatchScorer()

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        vulnerabilities = context.get("vulnerabilities", [])
        candidates = context.get("patch_candidates", [])
        file_path = context.get("file_path", "")
        repo_root = context.get("repo_root")
        pr_context = context.get("pr_context", {})
        
        if not vulnerabilities or not candidates:
            self.log("No vulnerabilities or candidates to analyze")
            return context

        self.log(f"Ranking {len(candidates)} candidates for {len(vulnerabilities)} findings")
        
        try:
            metrics = extract_metrics(file_path)
            context["metrics"] = metrics
        except Exception as e:
            self.log(f"Failed to extract metrics: {e}", "warning")
            metrics = {}
            context["metrics"] = {}
        
        try:
            is_sensitive = self.policy_engine.is_path_sensitive(file_path)
            if is_sensitive:
                self.log(f"High-Sensitivity file detected: {file_path}", "warning")
        except Exception as e:
            self.log(f"Policy check failed: {e}", "warning")
            is_sensitive = False

        if repo_root:
            rel_file = os.path.relpath(file_path, repo_root)
        else:
            rel_file = os.path.basename(file_path)

        # 1. Evaluate every candidate using PatchScorer
        for candidate in candidates:
            try:
                total_risk = 0.0
                policy_success = candidate.get("validation_details", {}).get("policy", {}).get("success", False)
                
                quality_score = self.patch_scorer.score(candidate, context)
                candidate["quality_score"] = quality_score
                quality_breakdown = self.patch_scorer.get_breakdown(candidate, context)
                candidate["quality_breakdown"] = quality_breakdown
                
                for vuln in vulnerabilities:
                    risk = calculate_risk(
                        vulnerability=vuln,
                        pr=pr_context,
                        confidence=candidate.get("validation_score", 0.5),
                        validation=candidate.get("validation_details", {}).get("syntax"),
                        metrics=metrics,
                        quality_score=quality_score,
                    )
                    
                    if is_sensitive:
                        risk = min(10.0, risk * 1.25)
                    if not policy_success:
                        risk = min(10.0, risk + 2.0)
                        
                    total_risk += risk
                
                avg_risk = total_risk / max(len(vulnerabilities), 1)
                # Normalized risk penalty: scales with (1 - quality) so a good
                # patch on a risky file is never clamped to zero. Previously the
                # flat penalty (avg_risk / 10, up to 1.0) wiped out every
                # candidate when the file was high-risk, creating artificial
                # ties that the LLM tie-break then won.
                risk_penalty = (avg_risk / 10.0) * (1.0 - quality_score)
                candidate["ranking_score"] = max(0.0, round(quality_score - risk_penalty, 4))

            except Exception as e:
                self.log(f"Failed to evaluate candidate {candidate.get('id', 'unknown')}: {e}", "error")
                candidate["ranking_score"] = -1.0

        # 2. Pick the Winner with explicit tie-breaking
        # Primary sort by ranking_score (descending), on tie prefer LLM variants over deterministic_ast

        # Defensive guard: never select a candidate that is byte-identical to the
        # ORIGINAL unpatched source (e.g. a fallback that reused the input instead
        # of generating a real patch). Such "patches" would be posted unchanged.
        original_code = (context.get("original_code") or "").strip()
        if original_code:
            for candidate in candidates:
                if (candidate.get("code") or "").strip() == original_code:
                    self.log(
                        f"Candidate {candidate.get('id', 'unknown')} is identical to the original "
                        f"code — treating as a fallback and excluding from winner selection",
                        "warning",
                    )
                    candidate["ranking_score"] = -1.0

        def _candidate_key(c):
            score = c.get("ranking_score", -1)
            # Tie-break by (ranking, quality, validation) so a higher-scoring
            # candidate wins a tie instead of defaulting to the LLM preference.
            quality = c.get("quality_score", 0) or 0
            validation = c.get("validation_score", 0) or 0
            tiebreaker = 0 if c.get("source") != "deterministic_ast" else 1
            return (-score, -quality, -validation, tiebreaker)

        sorted_candidates = sorted(candidates, key=_candidate_key)
        if not sorted_candidates:
            self.log("No candidates available — skipping risk analysis", "warning")
            return context
        winner = sorted_candidates[0]

        # Log accurately whether the winner was decided by score/quality/validation
        # or fell through to the LLM-vs-deterministic preference.
        if len(candidates) > 1:
            runner_up = sorted_candidates[1]
            winner_primary = _candidate_key(winner)[:3]
            runner_primary = _candidate_key(runner_up)[:3]
            if winner_primary == runner_primary:
                llm_count = sum(1 for c in candidates if c.get("source") != "deterministic_ast")
                if llm_count > 0:
                    self.log(f"Tie broken: {llm_count} LLM variant(s) tied with deterministic — preferred LLM", "debug")

        self.log(f"Winner selected: {winner['id']} (Score: {winner.get('ranking_score', 0):.2f})")

        # If the best candidate scored too low, suppress the patch (no patch to show)
        winner_ranking = winner.get("ranking_score", 0)
        patch_suppressed = winner_ranking < 0.1
        if patch_suppressed:
            self.log(f"Winner score too low ({winner_ranking:.2f}) — suppressing patch output", "warning")
            winner["diff"] = ""
        winner["patch_suppressed"] = patch_suppressed
        winner["suppression_score"] = winner_ranking
        
        # 2b. Ensure winner has a diff (never regenerate for suppressed patches —
        #     a suppressed finding must not leak a diff into the report as if applied)
        if not patch_suppressed:
            try:
                if not winner.get("diff"):
                    original_code = context.get("original_code", "")
                    if original_code:
                        diff = "".join(
                            difflib.unified_diff(
                                original_code.splitlines(keepends=True),
                                winner["code"].splitlines(keepends=True),
                                fromfile="before.py",
                                tofile="after.py",
                            )
                        )
                        winner["diff"] = diff
            except Exception as e:
                self.log(f"Failed to generate diff: {e}", "warning")
                winner["diff"] = ""

        # 3. Format final results
        final_results = []
        for vuln in vulnerabilities:
            try:
                vuln["file_rel"] = rel_file

                vuln_type = vuln.get("type", "")
                details = winner.get("validation_details", {}) or {}
                syntax_details = details.get("syntax") or {}
                rescan_details = details.get("rescan") or {}

                # Scope the security re-scan to this vulnerability. A patch that
                # fixes this finding is "clean" here even when unrelated findings
                # remain elsewhere in the file; a same-type remaining finding means
                # the fix did not actually remove this vulnerability.
                per_vuln_rescan: dict[str, Any] = {}
                if rescan_details:
                    per_vuln_rescan = dict(rescan_details)
                    same_type_remaining = [
                        v for v in (rescan_details.get("remaining_vulnerabilities") or [])
                        if v.get("type") == vuln_type
                    ]
                    per_vuln_rescan["success"] = bool(rescan_details.get("success")) or not same_type_remaining
                    per_vuln_rescan["scoped_remaining"] = same_type_remaining

                syntax_ok = syntax_details.get("success") is True
                rescan_ok = per_vuln_rescan.get("success") is True

                per_vuln_validation = {
                    "success": syntax_ok and rescan_ok,
                    "score": winner.get("validation_score", 0),
                    "policy_violations": details.get("policy", {}).get("violations", []),
                    "details": {**details, "rescan": per_vuln_rescan},
                    "test_results": winner.get("test_results", {}),
                    "static_only": bool(details.get("static_only")),
                }

                confidence = calculate_confidence(
                    vulnerability=vuln,
                    patch=winner["code"],
                    validation=per_vuln_validation,
                    test_results=winner.get("test_results"),
                    quality_score=winner.get("quality_score"),
                )
                
                risk_score = calculate_risk(
                    vulnerability=vuln,
                    pr=pr_context,
                    confidence=confidence,
                    validation=per_vuln_validation,
                    metrics=metrics,
                    quality_score=winner.get("quality_score"),
                )
                
                if is_sensitive:
                    risk_score = min(10.0, risk_score * 1.2)

                risk_breakdown = explain_risk(
                    vulnerability=vuln,
                    pr=pr_context,
                    confidence=confidence,
                    validation=per_vuln_validation,
                    metrics=metrics
                )
                
                evidence = generate_evidence(vuln)
                meta = VULN_METADATA.get(vuln.get("type", ""), {})
                severity_label = effective_severity(vuln)

                # Detection confidence reflects LLM triage: confirmed findings
                # are promoted, rejected/unconfirmed ones keep the base value.
                base_conf = DETECTION_CONFIDENCE.get(vuln_type, 0.9)
                if (vuln.get("triage") or {}).get("verdict") == "confirmed":
                    detection_confidence = max(base_conf, 0.98)
                else:
                    detection_confidence = base_conf

                result = {
                    "vulnerability": vuln,
                    "confidence": confidence,
                    "risk": risk_score,
                    "risk_breakdown": risk_breakdown,
                    "evidence": evidence,
                    "remediation": meta.get("remediation", ""),
                    "risk_rationale": meta.get("risk_rationale", ""),
                    "rule_id": RULE_IDS.get(vuln_type, vuln_type),
                    "priority": compute_priority(risk_score, severity_label),
                    "detection_confidence": detection_confidence,
                    "is_silent": vuln_type in SILENT_TYPES or bool(vuln.get("unconfirmed")),
                    "unconfirmed": bool(vuln.get("unconfirmed")),
                    "triage": vuln.get("triage"),
                    "quality_score": winner.get("quality_score", 0),
                    "quality_breakdown": winner.get("quality_breakdown", {}),
                    "validation": per_vuln_validation,
                    "patch_suppressed": winner.get("patch_suppressed", False),
                    "suppression_score": winner.get("suppression_score", 0),
                    "patch": winner["code"],
                    "diff": winner.get("diff", ""),
                    "candidate_id": winner["id"],
                    "candidate_source": winner["source"]
                }

                if vuln_type == "HARDCODED_SECRET":
                    secret_value = extract_secret_value(vuln.get("code", ""))
                    if secret_value:
                        result["secret_entropy"] = shannon_entropy(secret_value)

                final_results.append(result)

            except Exception as e:
                self.log(f"Failed to format result for vulnerability {vuln.get('type', 'unknown')}: {e}", "error")
                log.exception("Error formatting risk result")
            
        # LLM context-aware explanations (fail-open: static rationale is kept)
        llm_triage = context.get("llm_triage")
        if llm_triage is not None and getattr(config.app.explainer, "enabled", True):
            try:
                explanations = llm_triage.generate_explanations(
                    vulnerabilities, context.get("original_code", "")
                )
                for idx, result in enumerate(final_results):
                    explanation = explanations.get(idx)
                    if explanation:
                        result["llm_rationale"] = explanation
            except Exception as e:
                self.log(f"LLM explanation generation failed: {e}", "warning")

        context["results"] = final_results
        self.log(f"Risk analysis complete. Selected Patch: {winner['id']}")
        
        return context
