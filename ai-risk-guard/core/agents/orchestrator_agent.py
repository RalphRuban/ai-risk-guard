"""
Orchestration Agent.
The 'Executive' agent that takes real-world actions (GitHub Decisions) based on risk analysis.
"""

from typing import Dict, Any, List
import requests
from core.agents.base_agent import BaseAgent
from utils.logger import logger

class OrchestrationAgent(BaseAgent):
    """
    Agent responsible for making autonomous decisions on GitHub PRs.
    """
    
    def __init__(self):
        super().__init__("Orchestrator")

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        results = context.get("results", [])
        if not results:
            return context

        # 1. Calculate the 'Worst' Risk Score
        max_risk = max(r.get("risk", 0) for r in results)
        repo_name = context.get("pr_context", {}).get("repo_name")
        pr_number = context.get("pr_context", {}).get("pr_number")
        token = context.get("pr_context", {}).get("access_token")

        if not all([repo_name, pr_number, token]):
            self.log("Insufficient PR context for autonomous action", "warning")
            return context

        self.log(f"Making executive decision for PR #{pr_number} (Max Risk: {max_risk})")

        # 2. Executive Logic
        decision = "COMMENT"
        if max_risk >= 8.0:
            decision = "REQUEST_CHANGES"
            self.log(f"CRITICAL RISK: Requesting changes on PR #{pr_number}", "error")
            self._take_github_action(repo_name, pr_number, token, "REQUEST_CHANGES", 
                                   "🚨 CRITICAL SECURITY RISK: This PR contains high-risk vulnerabilities and violates security policy. Merging is blocked.")
        elif max_risk >= 4.0:
            decision = "REQUEST_CHANGES"
            self.log(f"MODERATE RISK: Requesting changes on PR #{pr_number}")
            self._take_github_action(repo_name, pr_number, token, "REQUEST_CHANGES", 
                                   "⚠️ SECURITY CONCERNS: Vulnerabilities detected. Please review the AI-suggested patches before merging.")
        else:
            self.log(f"LOW RISK: Standard comment posted.")

        context["executive_decision"] = decision
        return context

    def _take_github_action(self, repo, pr, token, action_type, message):
        """Perform actions via GitHub Reviews API."""
        try:
            url = f"https://api.github.com/repos/{repo}/pulls/{pr}/reviews"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json"
            }
            
            # Map system actions to GitHub actions
            event_map = {
                "REQUEST_CHANGES": "REQUEST_CHANGES",
                "COMMENT": "COMMENT",
                "APPROVE": "APPROVE"
            }

            payload = {
                "body": message,
                "event": event_map.get(action_type, "COMMENT")
            }

            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in (200, 201):
                self.log(f"GitHub Action successful: {action_type}")
            else:
                self.log(f"GitHub Action failed: {response.text}", "error")

        except Exception as e:
            self.log(f"Failed to communicate with GitHub: {e}", "error")
