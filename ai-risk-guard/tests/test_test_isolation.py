"""
tests/test_test_isolation.py
Regression tests for the conftest-level DB isolation (Section A2): the test
session must never create or mutate the developer's real SQLite database at
``data/dashboard.db``.
"""

import os
from pathlib import Path

import utils.db as udb

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_conftest_forces_temp_db_path():
    db_path = os.environ.get("DB_PATH")
    assert db_path, "conftest must set DB_PATH for the whole test session"
    assert "ai-risk-guard-test-" in str(db_path)
    assert Path(db_path).resolve().parent != (_REPO_ROOT / "data").resolve()


def test_app_import_uses_temp_db_not_repo_db():
    # utils.db resolves DB_PATH at import; with conftest's env override this must
    # point into the temp dir, never at the repo's real data/dashboard.db.
    repo_db = (_REPO_ROOT / "data" / "dashboard.db").resolve()
    assert Path(udb.DB_PATH).resolve() != repo_db
    assert "ai-risk-guard-test-" in str(udb.DB_PATH)
