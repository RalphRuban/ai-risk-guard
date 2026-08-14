"""
tests/test_deferred_validation.py
Tests for deferred re-validation: scans that failed closed because Docker was
unavailable are queued (validation_status='pending') and re-run once Docker is
available again, updating the existing PR comment/check.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import utils.db as udb
from app import app as app_module
from app.app import app as flask_app
from utils.db import (
    get_pending_validation_scans,
    get_scan,
    mark_scan_validated,
    mark_scan_validation_pending,
    record_scan,
    sync_user_installations,
    upsert_repo,
    upsert_user,
)


def _csrf_headers(client):
    client.get("/api/me")
    cookie = client.get_cookie("csrf_token")
    return {"X-CSRF-Token": cookie.value} if cookie else {}


def _seed_scan(github_id=111, login="alice", install_id=5):
    repo_id = 1
    upsert_user(github_id, login, "Alice", "")
    sync_user_installations(github_id, [{"id": install_id, "account": {"type": "User", "login": login}}])
    upsert_repo({
        "id": repo_id, "full_name": f"{login}/app", "owner": login,
        "name": "app", "description": "", "language": "Python",
        "private": 0, "default_branch": "main", "install_id": install_id,
    })
    return record_scan(
        repo_id=repo_id, pr_number=1, pr_title="a", branch="main", commit_sha="abc123",
        findings_count=1, max_risk=8.0, duration_ms=10,
    )


class TestDbHelpers:
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

    def test_scan_defaults_to_ok(self):
        scan_id = _seed_scan()
        assert get_scan(scan_id)["validation_status"] == "ok"

    def test_pending_roundtrip(self):
        scan_id = _seed_scan()
        mark_scan_validation_pending(scan_id)
        assert get_scan(scan_id)["validation_status"] == "pending"
        pending = get_pending_validation_scans()
        assert any(s["id"] == scan_id for s in pending)
        assert pending[0]["repo_full_name"] == "alice/app"
        assert pending[0]["install_id"] == 5
        assert pending[0]["commit_sha"] == "abc123"
        mark_scan_validated(scan_id)
        assert get_scan(scan_id)["validation_status"] == "ok"
        assert get_pending_validation_scans() == []

    def test_migration_idempotent(self):
        udb.init_db()
        udb.init_db()
        with udb._connect() as conn:
            cols = [row["name"] for row in conn.execute("PRAGMA table_info(scans)").fetchall()]
            assert cols.count("validation_status") == 1


class TestRevalidateWorker:
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

    def _pending(self, scan_id):
        return {
            "id": scan_id,
            "repo_id": 1,
            "pr_number": 1,
            "pr_title": "a",
            "branch": "main",
            "commit_sha": "abc123",
            "repo_full_name": "alice/app",
            "install_id": 5,
        }

    def test_revalidate_submits_and_marks_validated(self):
        scan_id = _seed_scan()
        mark_scan_validation_pending(scan_id)
        with (
            patch.object(app_module, "run_async_analysis") as mock_run,
            patch.object(app_module, "mark_scan_validated") as mock_mark,
            patch.object(app_module, "_analysis_slot") as mock_slot,
            patch.object(app_module, "executor") as mock_exec,
        ):
            mock_slot.acquire.return_value = True
            app_module._revalidate_pending_scan(self._pending(scan_id))
            mock_exec.submit.assert_called_once()
            job = mock_exec.submit.call_args[0][0]
            job()
            mock_run.assert_called_once_with(
                "alice/app", 1, 1, "a", 5, "main", "abc123"
            )
            mock_mark.assert_called_once_with(scan_id)
            mock_slot.release.assert_called()

    def test_revalidate_skips_when_capacity_reached(self):
        scan_id = _seed_scan()
        mark_scan_validation_pending(scan_id)
        with (
            patch.object(app_module, "_analysis_slot") as mock_slot,
            patch.object(app_module, "executor") as mock_exec,
        ):
            mock_slot.acquire.return_value = False
            app_module._revalidate_pending_scan(self._pending(scan_id))
            mock_exec.submit.assert_not_called()

    def test_revalidate_skips_missing_install(self):
        scan_id = _seed_scan()
        mark_scan_validation_pending(scan_id)
        pending = self._pending(scan_id)
        pending["install_id"] = None
        with (
            patch.object(app_module, "_analysis_slot"),
            patch.object(app_module, "executor") as mock_exec,
        ):
            app_module._revalidate_pending_scan(pending)
            mock_exec.submit.assert_not_called()


class TestRevalidateEndpoint:
    def setup_method(self):
        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()
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

    def test_revalidate_queues_scan(self):
        scan_id = _seed_scan()
        with self.client.session_transaction() as sess:
            sess["user"] = {"github_id": "111", "login": "alice"}
        with (
            patch.object(app_module, "_analysis_slot") as mock_slot,
            patch.object(app_module, "executor"),
        ):
            mock_slot.acquire.return_value = True
            resp = self.client.post(
                f"/api/scans/{scan_id}/revalidate", headers=_csrf_headers(self.client)
            )
        assert resp.status_code == 202
        assert get_scan(scan_id)["validation_status"] == "pending"

    def test_revalidate_404_for_other_user(self):
        scan_id = _seed_scan()
        upsert_user(222, "bob", "Bob", "")
        sync_user_installations(222, [{"id": 6, "account": {"type": "User", "login": "bob"}}])
        with self.client.session_transaction() as sess:
            sess["user"] = {"github_id": "222", "login": "bob"}
        with (
            patch.object(app_module, "_analysis_slot"),
            patch.object(app_module, "executor"),
        ):
            resp = self.client.post(
                f"/api/scans/{scan_id}/revalidate", headers=_csrf_headers(self.client)
            )
        assert resp.status_code == 404