import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
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
    with (
        patch("core.llm.model_resolver.resolve_gemini_model", return_value="gemini-3.5-flash"),
        patch("core.triage.llm_triage.LLMTriage.explain_regression_tests", return_value=None),
    ):
        yield
