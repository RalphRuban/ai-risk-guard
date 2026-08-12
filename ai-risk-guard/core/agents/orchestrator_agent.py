"""
Orchestration Agent.
The 'Executive' agent that takes real-world actions (GitHub Decisions) based on risk analysis.
"""

from typing import Any

from core.agents.base_agent import BaseAgent
from core.config import config
from services.github.reporter import (
    generate_sarif,
    set_pr_labels,
)


class OrchestrationAgent(BaseAgent):
    """
    Agent responsible for making autonomous decisions on GitHub PRs.
    """
    
    def __init__(self):
        super().__init__("Orchestrator")

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        results = context.get("results", [])
        if not results:
            return context

        # 1. Calculate the 'Worst' Risk Score for NEW vulnerabilities only (Hybrid Gating).
        # Silent (informational) findings never gate the PR decision.
        new_results = [r for r in results if r.get("vulnerability", {}).get("is_new", False)]
        actionable = [r for r in new_results if not r.get("is_silent")]
        max_risk = max((r.get("risk", 0) for r in actionable), default=0.0)
        silent_count = len(new_results) - len(actionable)
        if silent_count:
            self.log(f"Ignoring {silent_count} silent finding(s) for decision gating")
        repo_name = context.get("pr_context", {}).get("repo_name")
        pr_number = context.get("pr_context", {}).get("pr_number")
        token = context.get("pr_context", {}).get("access_token")
        commit_sha = context.get("pr_context", {}).get("commit_sha")

        if not all([repo_name, pr_number, token]):
            self.log("Insufficient PR context for autonomous action", "warning")
            return context

        if not commit_sha:
            self.log("commit_sha is missing from PR context — SARIF upload will be skipped", "warning")

        self.log(f"Making executive decision for PR #{pr_number} (Max Risk: {max_risk})")

        # 2. Executive Logic - read thresholds from config
        max_allowed_risk = config.risk.gating.max_allowed_risk
        human_review_above = config.risk.gating.auto_request_changes_above
        
        decision = "COMMENT"
        if max_risk >= max_allowed_risk:
            decision = "REQUEST_CHANGES"
            self.log(f"CRITICAL RISK: Requesting changes on PR #{pr_number}", "error")
        elif max_risk >= human_review_above:
            decision = "REQUEST_CHANGES"
            self.log(f"MODERATE RISK: Requesting changes on PR #{pr_number}")
        else:
            self.log("LOW RISK: Standard comment posted.")

        context["executive_decision"] = decision
        
        # 3. Set PR labels based on max risk
        set_pr_labels(repo_name, pr_number, token, max_risk)

        # 5. Generate and attach SARIF if we have results
        if results and repo_name and pr_number and token:
            try:
                self._attach_sarif_to_pr(results, repo_name, pr_number, token, context)
            except Exception as e:
                self.log(f"Failed to attach SARIF to PR: {e}", "warning")
        
        return context

    def _attach_sarif_to_pr(self, results, repo_name, pr_number, token, context):
        """Generate SARIF output and store in context (upload happens in app.py)."""
        should_upload = getattr(config.app.sarif, "upload_to_code_scanning", True)
        if not should_upload:
            self.log("SARIF upload disabled via configuration")
            return

        file_path = context.get("file_path", "unknown")
        commit_sha = context.get("pr_context", {}).get("commit_sha")
        scan_duration = context.get("scan_duration", 0.0)
        sarif_output = generate_sarif(results, file_path, commit_sha=commit_sha, scan_duration=scan_duration)
        
        if sarif_output and commit_sha:
            context["sarif_output"] = sarif_output
            context["sarif_commit_sha"] = commit_sha
            self.log("SARIF generated (upload will run in parallel with PR comment)", "GITHUB")
        else:
            self.log(
                f"SARIF generation skipped: sarif_output={'yes' if sarif_output else 'no'}, "
                f"commit_sha={'yes' if commit_sha else 'None'}",
                "warning",
            )


