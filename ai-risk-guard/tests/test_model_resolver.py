"""
tests/test_model_resolver.py
Tests for Gemini model resolution with fallback chain.
"""

from unittest.mock import MagicMock

import pytest

from core.llm.model_resolver import ModelResolutionError, resolve_gemini_model


class TestModelResolver:
    def test_first_model_available(self):
        client = MagicMock()
        result = resolve_gemini_model(client, ["gemini-3.5-flash"])
        assert result == "gemini-3.5-flash"
        client.models.get.assert_called_once_with(model="gemini-3.5-flash")

    def test_fallback_to_second_model(self):
        client = MagicMock()
        client.models.get.side_effect = [Exception("not found"), None]
        result = resolve_gemini_model(client, ["gemini-bad", "gemini-good"])
        assert result == "gemini-good"
        assert client.models.get.call_count == 2

    def test_all_models_unavailable_raises(self):
        client = MagicMock()
        client.models.get.side_effect = Exception("not found")
        with pytest.raises(ModelResolutionError):
            resolve_gemini_model(client, ["gemini-a", "gemini-b", "gemini-c"])
        assert client.models.get.call_count == 3

    def test_custom_fallback_chain_overrides_default(self):
        client = MagicMock()
        result = resolve_gemini_model(client, ["my-custom-model"])
        assert result == "my-custom-model"
        client.models.get.assert_called_once_with(model="my-custom-model")

    def test_default_fallback_chain_used_when_none_provided(self):
        client = MagicMock()
        result = resolve_gemini_model(client)
        assert result in ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
