import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Force the Gemini API key to empty BEFORE any test module import.
#
# Several test modules import app.app at top level, and app/app.py runs
# load_dotenv(PROJ_ENV) during import. On a developer machine PROJ_ENV points
# at a real env file that contains a live GEMINI_API_KEY, which used to leak
# into tests and make them call the real Gemini API (client construction +
# model resolution are network calls). load_dotenv() defaults to
# override=False, so pre-seeding GEMINI_API_KEY to empty here wins.
# ---------------------------------------------------------------------------
os.environ["GEMINI_API_KEY"] = ""

# Isolate the test session from the developer's real SQLite database.
#
# utils/db.py resolves DB_PATH at import time, and app.app runs init_db() at
# import (app/app.py). Some test modules import app.app at module top level
# (test_ci_validation.py, test_webhook_e2e.py), which used to create/update the
# real data/dashboard.db before any fixture could patch DB_PATH. Setting the
# env var here — before any test module import — redirects that startup init
# into a throwaway temp database instead.
# ---------------------------------------------------------------------------
_TMP_DB_DIR = Path(tempfile.mkdtemp(prefix="ai-risk-guard-test-"))
os.environ["DB_PATH"] = str(_TMP_DB_DIR / "dashboard.db")

# Initialize the throwaway database so every table exists up front. Tests that
# never import app.app (which normally runs init_db at import) previously relied
# on the developer's persistent data/dashboard.db having all tables; a fresh
# temp DB would be missing them (e.g. patch_feedback, scan_cache).
from utils.db import init_db

init_db()


@pytest.fixture(autouse=True)
def mock_gemini_api():
    # Stub google.genai.Client so constructing a client is a local no-op —
    # would otherwise hit the real Gemini endpoint for client bootstrap and
    # model validation. gemini_client and llm_patcher share the google.genai
    # module object, so this one patch covers both. resolve_gemini_model is
    # imported BY VALUE into core.llm.gemini_client and core.patch.llm_patcher,
    # so each module attribute must be patched where it is referenced.
    with (
        patch("core.llm.model_resolver.resolve_gemini_model", return_value="gemini-3.5-flash"),
        patch("core.llm.gemini_client.resolve_gemini_model", return_value="gemini-3.5-flash"),
        patch("core.patch.llm_patcher.resolve_gemini_model", return_value="gemini-3.5-flash"),
        patch("google.genai.Client", return_value=MagicMock()),
        patch("core.triage.llm_triage.LLMTriage.explain_regression_tests", return_value=None),
    ):
        yield
