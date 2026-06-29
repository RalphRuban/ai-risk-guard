"""
Risk Agent.
Responsible for risk assessment, confidence scoring, and metric extraction.
"""

import os
import difflib
from typing import Dict, Any, List
from core.agents.base_agent import BaseAgent
from core.risk.risk_engine import calculate_risk, explain_risk
from core.risk.metrics_extractor import extract_metrics
from core.confidence.confidence import calculate_confidence
from core.policy.policy_engine import PolicyEngine

class RiskAgent(BaseAgent):
    """
    Agent specialized in risk analysis and confidence scoring.
    Now includes Policy-Aware risk scoring.
    """
    
    def __init__(self):
        super().__init__("Risk")
        self.policy_engine = PolicyEngine()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        vulnerabilities = context.get("vulnerabilities", [])
        candidates = context.get("patch_candidates", [])
        file_path = context.get("file_path", "")
        repo_root = context.get("repo_root")
        pr_context = context.get("pr_context", {})
        
        if not vulnerabilities or not candidates:
            self.log("No vulnerabilities or candidates to analyze")
            return context

        self.log(f"Ranking {len(candidates)} candidates for {len(vulnerabilities)} findings")
        
        metrics = extract_metrics(file_path)
        context["metrics"] = metrics
        
        # Check if this file is in a sensitive area (Policy Week 3)
        is_sensitive = self.policy_engine.is_path_sensitive(file_path)
        if is_sensitive:
            self.log(f"High-Sensitivity file detected: {file_path}", "warning")

        if repo_root:
            rel_file = os.path.relpath(file_path, repo_root)
        else:
            rel_file = os.path.basename(file_path)

        # 1. Evaluate every candidate
        for candidate in candidates:
            total_risk = 0.0
            policy_success = candidate.get("validation_details", {}).get("policy", {}).get("success", False)
            
            for vuln in vulnerabilities:
                risk = calculate_risk(
                    vulnerability=vuln,
                    pr=pr_context,
                    confidence=candidate.get("validation_score", 0.5),
                    validation=candidate.get("validation_details", {}).get("syntax"),
                    metrics=metrics
                )
                
                # Escalate risk if file is sensitive or policy is violated
                if is_sensitive:
                    risk = min(10.0, risk * 1.25)
                if not policy_success:
                    risk = min(10.0, risk + 2.0)
                    
                total_risk += risk
            
            avg_risk = total_risk / len(vulnerabilities)
            candidate["ranking_score"] = (candidate.get("validation_score", 0) * 10) - avg_risk

        # 2. Pick the Winner
        candidates.sort(key=lambda x: x["ranking_score"], reverse=True)
        winner = candidates[0]
        self.log(f"Winner selected: {winner['id']} (Score: {winner['ranking_score']:.2f})")
        
        # 2b. Ensure winner has a diff
        if not winner.get("diff"):
            original_code = context.get("original_code", "")
            diff = "".join(
                difflib.unified_diff(
                    original_code.splitlines(keepends=True),
                    winner["code"].splitlines(keepends=True),
                    fromfile="before.py",
                    tofile="after.py",
                )
            )
            winner["diff"] = diff

        # 3. Format final results
        final_results = []
        for vuln in vulnerabilities:
            vuln["file_rel"] = rel_file
            
            confidence = calculate_confidence(
                vulnerability=vuln,
                patch=winner["code"],
                validation=winner["validation_details"]["syntax"]
            )
            
            risk_score = calculate_risk(
                vulnerability=vuln,
                pr=pr_context,
                confidence=confidence,
                validation=winner["validation_details"]["syntax"],
                metrics=metrics
            )
            
            # Apply final reporting escalation
            if is_sensitive: risk_score = min(10.0, risk_score * 1.2)

            risk_breakdown = explain_risk(
                vulnerability=vuln,
                pr=pr_context,
                confidence=confidence,
                validation=winner["validation_details"]["syntax"],
                metrics=metrics
            )
            
            final_results.append({
                "vulnerability": vuln,
                "confidence": confidence,
                "risk": risk_score,
                "risk_breakdown": risk_breakdown,
                "validation": {
                    "success": winner.get("validation_score", 0) >= 1.0,
                    "score": winner.get("validation_score", 0),
                    "policy_violations": winner["validation_details"].get("policy", {}).get("violations", [])
                },
                "sandbox": winner["validation_details"]["sandbox"],
                "rescan": winner["validation_details"]["rescan"],
                "patch": winner["code"],
                "diff": winner.get("diff", ""),
                "candidate_id": winner["id"],
                "candidate_source": winner["source"]
            })
            
        context["results"] = final_results
        self.log(f"Risk analysis complete. Selected Patch: {winner['id']}")
        
        return context
