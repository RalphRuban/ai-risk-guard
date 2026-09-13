"""Repo-scoped resolution of open findings (P2-10).

PR numbers are only unique per repository, so resolving findings on merge must
scope by repo to avoid clearing an unrelated repo's findings that reuse the
same PR number.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import utils.db as udb
from utils.db import (
    record_finding,
    record_scan,
    resolve_open_findings_for_pr,
    upsert_repo,
)


def _seed(repo_id: int, full_name: str, pr_number: int) -> int:
    owner, name = full_name.split("/", 1)
    upsert_repo({
        "id": repo_id, "full_name": full_name, "owner": owner, "name": name,
        "description": "", "language": "Python", "private": 0,
        "default_branch": "main", "install_id": 1,
    })
    scan_id = record_scan(
        repo_id=repo_id, pr_number=pr_number, pr_title="t", branch="main",
        commit_sha=f"sha{repo_id}", findings_count=1, max_risk=5.0, duration_ms=1,
    )
    record_finding(scan_id, "SQL_INJECTION", "HIGH", 8.0, "a.py", 1)
    return scan_id


def _statuses(scan_id: int) -> list[str]:
    with udb._connect() as conn:
        rows = conn.execute(
            "SELECT status FROM findings WHERE scan_id = ?", (scan_id,)
        ).fetchall()
    return [row["status"] for row in rows]


class TestResolveOpenFindingsScoping:
    def setup_method(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        self._patch = patch.object(udb, "DB_PATH", Path(self._tmp))
        self._patch.start()
        udb.init_db()

    def teardown_method(self):
        self._patch.stop()
        try:
            os.unlink(self._tmp)
        except PermissionError:
            pass

    def test_scopes_to_repo(self):
        scan_a = _seed(1, "acme/a", 7)
        scan_b = _seed(2, "acme/b", 7)

        assert resolve_open_findings_for_pr(7, "acme/a") == 1
        assert _statuses(scan_a) == ["resolved"]
        assert _statuses(scan_b) == ["open"]

    def test_unknown_repo_resolves_nothing(self):
        scan_a = _seed(1, "acme/a", 7)

        assert resolve_open_findings_for_pr(7, "acme/other") == 0
        assert _statuses(scan_a) == ["open"]

    def test_legacy_no_repo_resolves_across_repos(self):
        scan_a = _seed(1, "acme/a", 7)
        scan_b = _seed(2, "acme/b", 7)

        assert resolve_open_findings_for_pr(7) == 2
        assert _statuses(scan_a) == ["resolved"]
        assert _statuses(scan_b) == ["resolved"]
