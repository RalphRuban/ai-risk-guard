"""
tests/test_patch_agent.py
Tests for the PatchAgent — AST + LLM patch coordination.
"""

from unittest.mock import MagicMock, patch

from core.agents.patch_agent import PatchAgent


class TestPatchAgent:
    def setup_method(self):
        # Patch LLMPatcher at the class level to avoid API calls
        self.llm_patcher_patch = patch("core.agents.patch_agent.LLMPatcher")
        self.mock_llm_patcher_cls = self.llm_patcher_patch.start()
        self.mock_llm_patcher = MagicMock()
        self.mock_llm_patcher.enabled = False
        self.mock_llm_patcher_cls.return_value = self.mock_llm_patcher
        self.agent = PatchAgent()

    def teardown_method(self):
        self.llm_patcher_patch.stop()

    def test_execute_no_vulnerabilities_returns_context(self):
        with patch("core.agents.patch_agent.apply_patches_safely") as mock_apply:
            context = {"original_code": "x = 1", "vulnerabilities": []}
            result = self.agent.execute(context)
            assert result is context
            mock_apply.assert_not_called()

    def test_execute_ast_baseline_candidate(self):
        with patch("core.agents.patch_agent.apply_patches_safely") as mock_apply:
            mock_apply.return_value = {
                "final_code": "x = 2",
                "combined_diff": "@@ -1 +1 @@\n-x = 1\n+x = 2",
            }
            context = {
                "original_code": "x = 1",
                "vulnerabilities": [{"type": "HARDCODED_SECRET", "line": 1}],
            }
            result = self.agent.execute(context)
            candidates = result["patch_candidates"]
            assert len(candidates) == 1
            assert candidates[0]["source"] == "deterministic_ast"
            assert candidates[0]["code"] == "x = 2"

    def test_execute_llm_candidates_appended_when_enabled(self):
        self.mock_llm_patcher.enabled = True
        self.mock_llm_patcher.model_id = "gemini-3.5-flash"
        self.mock_llm_patcher.generate_candidates.return_value = (["def foo(): pass", "def bar(): pass"], "some-prompt", "some-raw-response")

        with patch("core.agents.patch_agent.apply_patches_safely") as mock_apply:
            mock_apply.return_value = {
                "final_code": "x = 2",
                "combined_diff": "diff",
            }
            context = {
                "original_code": "x = 1",
                "vulnerabilities": [{"type": "HARDCODED_SECRET", "line": 1}],
            }
            result = self.agent.execute(context)
            candidates = result["patch_candidates"]
            assert len(candidates) == 3
            assert candidates[0]["source"] == "deterministic_ast"
            assert candidates[1]["source"] == "gemini-3.5-flash"
            assert candidates[2]["source"] == "gemini-3.5-flash"
            assert result.get("llm_prompt") == "some-prompt"
            assert result.get("llm_raw_response") == "some-raw-response"

    def test_execute_no_llm_candidates_when_disabled(self):
        self.mock_llm_patcher.enabled = False

        with patch("core.agents.patch_agent.apply_patches_safely") as mock_apply:
            mock_apply.return_value = {
                "final_code": "x = 2",
                "combined_diff": "diff",
            }
            context = {
                "original_code": "x = 1",
                "vulnerabilities": [{"type": "HARDCODED_SECRET", "line": 1}],
            }
            result = self.agent.execute(context)
            candidates = result["patch_candidates"]
            assert len(candidates) == 1
            assert candidates[0]["source"] == "deterministic_ast"

    def test_execute_stores_original_code_key(self):
        with patch("core.agents.patch_agent.apply_patches_safely") as mock_apply:
            mock_apply.return_value = {
                "final_code": "x = 2",
                "combined_diff": "diff",
            }
            context = {
                "original_code": "x = 1",
                "vulnerabilities": [{"type": "HARDCODED_SECRET", "line": 1}],
            }
            self.agent.execute(context)
            mock_apply.assert_called_once()
            _, kwargs = mock_apply.call_args
            assert kwargs["code"] == "x = 1"
