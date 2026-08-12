"""
tests/test_orchestrator.py
Tests for the OrchestrationAgent — the PR decision engine.
"""

from unittest.mock import patch

from core.agents.orchestrator_agent import OrchestrationAgent


class TestOrchestrationAgent:
    def setup_method(self):
        self.agent = OrchestrationAgent()

    def test_execute_empty_results_returns_context(self):
        context = {"results": []}
        result = self.agent.execute(context)
        assert result is context
        assert "executive_decision" not in context

    def test_execute_critical_risk_requests_changes(self):
        with patch.object(self.agent, "_attach_sarif_to_pr"), \
             patch("core.agents.orchestrator_agent.set_pr_labels"):
            context = {
                "results": [
                    {"vulnerability": {"is_new": True}, "risk": 9.0}
                ],
                "pr_context": {
                    "repo_name": "test/repo",
                    "pr_number": 1,
                    "access_token": "test",
                    "commit_sha": "abc123",
                }
            }
            result = self.agent.execute(context)
            assert result["executive_decision"] == "REQUEST_CHANGES"

    def test_execute_low_risk_posts_comment(self):
        with patch.object(self.agent, "_attach_sarif_to_pr"), \
             patch("core.agents.orchestrator_agent.set_pr_labels"):
            context = {
                "results": [
                    {"vulnerability": {"is_new": True}, "risk": 1.0}
                ],
                "pr_context": {
                    "repo_name": "test/repo",
                    "pr_number": 1,
                    "access_token": "test",
                    "commit_sha": "abc123",
                }
            }
            result = self.agent.execute(context)
            assert result["executive_decision"] == "COMMENT"

    def test_execute_only_considers_new_vulnerabilities(self):
        with patch.object(self.agent, "_attach_sarif_to_pr"), \
             patch("core.agents.orchestrator_agent.set_pr_labels"):
            context = {
                "results": [
                    {"vulnerability": {"is_new": False}, "risk": 9.5},
                    {"vulnerability": {"is_new": True}, "risk": 2.0},
                ],
                "pr_context": {
                    "repo_name": "test/repo",
                    "pr_number": 1,
                    "access_token": "test",
                    "commit_sha": "abc123",
                }
            }
            result = self.agent.execute(context)
            # max_risk should be 2.0 (only new finding), so decision is COMMENT
            assert result["executive_decision"] == "COMMENT"

    def test_silent_finding_does_not_gate_decision(self):
        with patch.object(self.agent, "_attach_sarif_to_pr"), \
             patch("core.agents.orchestrator_agent.set_pr_labels"):
            context = {
                "results": [
                    {"vulnerability": {"is_new": True}, "risk": 6.0, "is_silent": True}
                ],
                "pr_context": {
                    "repo_name": "test/repo",
                    "pr_number": 1,
                    "access_token": "test",
                    "commit_sha": "abc123",
                }
            }
            result = self.agent.execute(context)
            assert result["executive_decision"] == "COMMENT"

    def test_actionable_finding_gates_despite_silent_presence(self):
        with patch.object(self.agent, "_attach_sarif_to_pr"), \
             patch("core.agents.orchestrator_agent.set_pr_labels"):
            context = {
                "results": [
                    {"vulnerability": {"is_new": True}, "risk": 9.0, "is_silent": False},
                    {"vulnerability": {"is_new": True}, "risk": 6.0, "is_silent": True},
                ],
                "pr_context": {
                    "repo_name": "test/repo",
                    "pr_number": 1,
                    "access_token": "test",
                    "commit_sha": "abc123",
                }
            }
            result = self.agent.execute(context)
            assert result["executive_decision"] == "REQUEST_CHANGES"

    def test_attach_sarif_disabled_by_config(self):
        with patch("core.agents.orchestrator_agent.config") as mock_config, \
             patch("core.agents.orchestrator_agent.set_pr_labels"):
            mock_config.app.sarif.upload_to_code_scanning = False
            mock_config.risk.gating.max_allowed_risk = 999.0
            mock_config.risk.gating.auto_request_changes_above = 500.0

            context = {
                "results": [{"vulnerability": {"is_new": True}, "risk": 3.0}],
                "file_path": "test.py",
                "pr_context": {
                    "repo_name": "test/repo",
                    "pr_number": 1,
                    "access_token": "test",
                    "commit_sha": "abc123",
                }
            }
            result = self.agent.execute(context)
            assert "sarif_output" not in result
