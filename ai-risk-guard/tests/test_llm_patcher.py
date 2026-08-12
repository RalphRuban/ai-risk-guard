"""
Tests for LLM Patcher rate limit handling.
"""

import os
import time
from unittest.mock import MagicMock, patch

from core.config import config
from core.patch.llm_patcher import (
    LLMPatcher,
    _is_rate_limit_error,
    is_rate_limited,
    reset_rate_limit_state,
)


class TestIsRateLimitError:
    def test_detects_429(self):
        assert _is_rate_limit_error(Exception("429 Too Many Requests"))

    def test_detects_quota(self):
        assert _is_rate_limit_error(Exception("quota exceeded for API"))

    def test_detects_resource_exhausted(self):
        assert _is_rate_limit_error(Exception("resource exhausted"))

    def test_detects_rate_limit(self):
        assert _is_rate_limit_error(Exception("rate limit exceeded"))

    def test_detects_too_many_requests(self):
        assert _is_rate_limit_error(Exception("too many requests"))

    def test_ignores_generic_error(self):
        assert not _is_rate_limit_error(Exception("internal server error"))

    def test_ignores_timeout(self):
        assert not _is_rate_limit_error(Exception("timeout"))

    def test_ignores_syntax_error(self):
        assert not _is_rate_limit_error(Exception("invalid syntax"))


class TestRateLimitState:
    def setup_method(self):
        reset_rate_limit_state()

    def test_initial_state_not_rate_limited(self):
        assert not is_rate_limited()

    def test_reset_is_idempotent(self):
        reset_rate_limit_state()
        assert not is_rate_limited()
        reset_rate_limit_state()
        assert not is_rate_limited()


class TestGenerateCandidates:
    def setup_method(self):
        reset_rate_limit_state()

    def _make_patcher(self):
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}),
            patch("core.patch.llm_patcher.resolve_gemini_model", return_value="gemini-3.5-flash"),
        ):
            patcher = LLMPatcher()
        patcher.client = MagicMock()
        patcher.gemini_cache.get = MagicMock(return_value=None)
        patcher.gemini_cache.set = MagicMock()
        return patcher

    def test_skips_when_rate_limited(self):
        import core.patch.llm_patcher as mod
        mod._gemini_rate_limited_event.set()
        try:
            patcher = self._make_patcher()
            candidates, prompt, raw = patcher.generate_candidates("code = 1", [])
            assert candidates == ["code = 1"]
            assert prompt is None
            assert raw is None
            patcher.client.models.generate_content.assert_not_called()
        finally:
            mod._gemini_rate_limited_event.clear()

    def test_retry_success(self):
        patcher = self._make_patcher()
        mock_response = MagicMock()
        mock_response.text = "fixed_code\n---VARIANT_BOUNDARY---\nmore_code"
        patcher.client.models.generate_content.side_effect = [
            Exception("429 Too Many Requests"),
            mock_response,
        ]
        with patch.object(time, "sleep") as mock_sleep:
            candidates, prompt, raw = patcher.generate_candidates("code = 1", [])
        assert len(candidates) == 2
        assert prompt is not None
        assert raw is not None
        assert not is_rate_limited()
        assert patcher.client.models.generate_content.call_count == 2
        assert mock_sleep.call_count == 1

    def test_retry_fails_sets_flag(self):
        patcher = self._make_patcher()
        patcher.client.models.generate_content.side_effect = Exception("429 rate limit")
        with patch.object(time, "sleep"):
            candidates, prompt, raw = patcher.generate_candidates("code = 1", [])
        assert candidates == ["code = 1"]
        assert prompt is None
        assert raw is None
        assert is_rate_limited()
        expected_calls = 2 + (len(config.app.llm.model_fallback_chain) - 1)
        assert patcher.client.models.generate_content.call_count == expected_calls
        reset_rate_limit_state()

    def test_retry_fails_non_rate_limit(self):
        patcher = self._make_patcher()
        patcher.client.models.generate_content.side_effect = Exception("internal server error")
        candidates, prompt, raw = patcher.generate_candidates("code = 1", [])
        assert candidates == ["code = 1"]
        assert prompt is None
        assert raw is None
        assert not is_rate_limited()
        assert patcher.client.models.generate_content.call_count == 1

    def test_cache_hit_skips_api_call(self):
        patcher = self._make_patcher()
        patcher.gemini_cache.get = MagicMock(return_value="cached\n---VARIANT_BOUNDARY---\ncached_v2")
        candidates, prompt, raw = patcher.generate_candidates("code = 1", [])
        assert len(candidates) == 2
        assert prompt is not None
        assert raw is not None
        patcher.client.models.generate_content.assert_not_called()
        patcher.gemini_cache.set.assert_not_called()

    def test_success_does_not_set_flag(self):
        patcher = self._make_patcher()
        mock_response = MagicMock()
        mock_response.text = "good_code\n---VARIANT_BOUNDARY---\nbetter_code"
        patcher.client.models.generate_content.return_value = mock_response
        candidates, prompt, raw = patcher.generate_candidates("code = 1", [])
        assert len(candidates) == 2
        assert prompt is not None
        assert raw is not None
        assert not is_rate_limited()
        patcher.gemini_cache.set.assert_not_called()

    def test_disabled_patcher_returns_original_code(self):
        patcher = LLMPatcher()
        patcher.enabled = False
        candidates, prompt, raw = patcher.generate_candidates("code = 1", [])
        assert candidates == ["code = 1"]
        assert prompt is None
        assert raw is None
