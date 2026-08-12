from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_gemini_api():
    with patch("core.llm.model_resolver.resolve_gemini_model", return_value="gemini-3.5-flash"):
        yield
