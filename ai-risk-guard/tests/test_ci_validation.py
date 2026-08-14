"""
tests/test_ci_validation.py
Tests for CI-runner fallback validation (Phase E): capturing candidates that
failed closed because Docker was unavailable, dispatching them to a GitHub
Actions runner via repository_dispatch, receiving the results, and re-injecting
them into a re-analysis pass so the PR comment/check pick up runtime evidence.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import core.ci.validation as ci_validation
import utils.db as udb
from app import app as app_module
from app.app import app as flask_app
from core.agents.validator_agent import ValidatorAgent
from core.config import config
from core.validator.sandbox import Sandbox
from services.github import ci_dispatch
from utils.db import (
    complete_pending_validation,
    count_ci_results_available,
    get_ci_result,
    get_pending_scans_for_commit,
    get_pending_validation,
    get_pending_validations_for_commit,
    has_inflight_ci_validation,
    init_db,
    record_pending_validation,
    record_scan,
    sync_user_installations,
    update_pending_validation_status,
    upsert_repo,
    upsert_user,
)

SAFE_CODE = "def add(a, b):\n    return a + b\n"
UNAVAILABLE_RUN = {
    "success": False,
    "error": "Sandbox unavailable (Docker required)",
    "image_unavailable": True,
    "mode": "unavailable",
}
UNAVAILABLE_TESTS = {
    "success": False,
    "skipped": False,
    "output": "",
    "error": "Sandbox unavailable (Docker required)",
    "image_unavailable": True,
    "mode": "unavailable",
}
CI_SANDBOX = {"success": True, "output": "ok", "error": "", "mode": "docker"}
CI_TESTS = {
    "success": True,
    "skipped": False,
    "output": "1 passed in 0.01s",
    "error": "",
    "mode": "docker",
}


class _TmpDb:
    def __enter__(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        self._patch = patch.object(udb, "DB_PATH", Path(self._tmp))
        self._patch.start()
        init_db()
        return self

    def __exit__(self, *exc):
        self._patch.stop()
        try:
            os.unlink(self._tmp)
        except PermissionError:
            pass


def _enable_ci(monkeypatch):
    monkeypatch.setattr(config.app.ci_runner, "enabled", True)
    monkeypatch.setattr(config.app.ci_runner, "base_url", "https://arg.example")
    monkeypatch.setenv(config.app.ci_runner.secret_env, "s3cret")


def _seed_repo_and_scan(install_id=5):
    upsert_user(111, "alice", "Alice", "")
    sync_user_installations(111, [{"id": install_id, "account": {"type": "User", "login": "alice"}}])
    upsert_repo({
        "id": 1, "full_name": "alice/app", "owner": "alice", "name": "app",
        "description": "", "language": "Python", "private": 0,
        "default_branch": "main", "install_id": install_id,
    })
    return record_scan(
        repo_id=1, pr_number=1, pr_title="a", branch="main", commit_sha="abc123",
        findings_count=1, max_risk=8.0, duration_ms=10,
    )


class TestCiDbHelpers:
    def test_record_roundtrip_and_idempotency(self):
        with _TmpDb():
            jid1 = record_pending_validation(
                repo_full_name="alice/app", pr_number=1, commit_sha="abc123",
                source_filename="main.py", candidate_id="baseline_ast",
                patched_code=SAFE_CODE, test_filename="test_main.py",
                test_content="def test_add(): assert add(1, 2) == 3",
                extra_files=[{"path": "conftest.py", "content": ""}],
                scan_mode="docker_only", sandbox_network="none",
            )
            jid2 = record_pending_validation(
                repo_full_name="alice/app", pr_number=1, commit_sha="abc123",
                source_filename="main.py", candidate_id="baseline_ast",
                patched_code=SAFE_CODE,
            )
            assert jid1 == jid2
            rows = get_pending_validations_for_commit("alice/app", "abc123")
            assert len(rows) == 1
            row = get_pending_validation(jid1)
            assert row["patched_code"] == SAFE_CODE
            assert row["scan_mode"] == "docker_only"
            assert row["status"] == "pending"

    def test_status_transitions_and_result_lookup(self):
        with _TmpDb():
            jid = record_pending_validation(
                repo_full_name="alice/app", pr_number=1, commit_sha="abc123",
                source_filename="main.py", candidate_id="baseline_ast",
                patched_code=SAFE_CODE,
            )
            update_pending_validation_status(jid, "dispatched")
            assert get_pending_validation(jid)["status"] == "dispatched"
            assert has_inflight_ci_validation("alice/app", "abc123") is True
            assert count_ci_results_available("alice/app", "abc123") == 0
            assert get_ci_result("alice/app", "abc123", "main.py", "baseline_ast") is None

            result_json = ci_validation.build_result_json(CI_SANDBOX, CI_TESTS, SAFE_CODE)
            complete_pending_validation(jid, result_json)
            assert get_pending_validation(jid)["status"] == "completed"
            assert has_inflight_ci_validation("alice/app", "abc123") is False
            assert count_ci_results_available("alice/app", "abc123") == 1
            row = get_ci_result("alice/app", "abc123", "main.py", "baseline_ast")
            assert row is not None
            assert row["result_json"]

    def test_status_filter(self):
        with _TmpDb():
            record_pending_validation(
                repo_full_name="alice/app", pr_number=1, commit_sha="abc123",
                source_filename="main.py", candidate_id="baseline_ast",
                patched_code=SAFE_CODE,
            )
            pending = get_pending_validations_for_commit("alice/app", "abc123", statuses=["pending"])
            completed = get_pending_validations_for_commit("alice/app", "abc123", statuses=["completed"])
            assert len(pending) == 1
            assert completed == []

    def test_get_pending_scans_for_commit(self):
        with _TmpDb():
            scan_id = _seed_repo_and_scan()
            assert get_pending_scans_for_commit("alice/app", "abc123") == []
            udb.mark_scan_validation_pending(scan_id)
            scans = get_pending_scans_for_commit("alice/app", "abc123")
            assert len(scans) == 1
            assert scans[0]["id"] == scan_id
            assert scans[0]["repo_full_name"] == "alice/app"


class TestCiValidationCore:
    def test_configured_gating(self, monkeypatch):
        monkeypatch.setattr(config.app.ci_runner, "enabled", True)
        monkeypatch.setattr(config.app.ci_runner, "base_url", "")
        monkeypatch.delenv("CI_VALIDATION_BASE_URL", raising=False)
        assert ci_validation.ci_validation_configured() is False
        monkeypatch.setenv("CI_VALIDATION_BASE_URL", "https://arg.example")
        monkeypatch.setenv(config.app.ci_runner.secret_env, "s3cret")
        assert ci_validation.ci_validation_configured() is True

    def test_ci_validation_enabled_needs_pr_metadata(self, monkeypatch):
        _enable_ci(monkeypatch)
        assert ci_validation.ci_validation_enabled({}) is False
        ctx = {"pr_context": {"repo_name": "alice/app"}}
        assert ci_validation.ci_validation_enabled(ctx) is False
        ctx["pr_context"]["commit_sha"] = "abc123"
        assert ci_validation.ci_validation_enabled(ctx) is True

    def test_record_job_needs_repo_and_commit(self, monkeypatch):
        with _TmpDb():
            _enable_ci(monkeypatch)
            ctx = {"pr_context": {"repo_name": "alice/app"}}
            assert ci_validation.record_pending_validation_job(
                ctx, {"id": "baseline_ast"}, "main.py", SAFE_CODE, None, [], "docker_only", "none"
            ) == 0

    def test_result_injection_hash_guard(self, monkeypatch):
        with _TmpDb():
            _enable_ci(monkeypatch)
            jid = record_pending_validation(
                repo_full_name="alice/app", pr_number=1, commit_sha="abc123",
                source_filename="main.py", candidate_id="baseline_ast",
                patched_code=SAFE_CODE,
            )
            complete_pending_validation(
                jid, ci_validation.build_result_json(CI_SANDBOX, CI_TESTS, SAFE_CODE)
            )
            ctx = {"pr_context": {"repo_name": "alice/app", "commit_sha": "abc123"}}
            cand = {"id": "baseline_ast"}
            got = ci_validation.get_ci_validation_result(ctx, cand, "main.py", SAFE_CODE)
            assert got is not None
            assert got["sandbox"] == CI_SANDBOX
            # Stale code (different hash) must NOT be re-injected.
            got = ci_validation.get_ci_validation_result(ctx, cand, "main.py", "def other(): pass\n")
            assert got is None

    def test_result_injection_missing(self, monkeypatch):
        with _TmpDb():
            _enable_ci(monkeypatch)
            ctx = {"pr_context": {"repo_name": "alice/app", "commit_sha": "abc123"}}
            assert ci_validation.get_ci_validation_result(
                ctx, {"id": "baseline_ast"}, "main.py", SAFE_CODE
            ) is None


class TestValidatorCaptureAndInject:
    def _context(self, test_file_path=None, extra=None):
        ctx = {
            "file_path": str(self._src_path),
            "repo_root": str(self._src_path.parent),
            "original_code": SAFE_CODE,
            "test_file_path": test_file_path,
            "test_deps": [],
            "pr_context": {
                "repo_name": "alice/app",
                "pr_number": 1,
                "commit_sha": "abc123",
                "scan_settings": {},
            },
            "patch_candidates": [
                {"id": "baseline_ast", "code": SAFE_CODE, "source": "deterministic_ast"}
            ],
        }
        if extra:
            ctx.update(extra)
        return ctx

    def setup_method(self):
        self._work = tempfile.mkdtemp(prefix="arg_ci_test_")
        self._src_path = Path(self._work) / "main.py"
        self._src_path.write_text(SAFE_CODE, encoding="utf-8")
        self._test_path = Path(self._work) / "test_main.py"
        self._test_path.write_text("def test_add():\n    assert add(1, 2) == 3\n", encoding="utf-8")
        self._tmp_db = _TmpDb()
        self._tmp_db.__enter__()

    def teardown_method(self):
        self._tmp_db.__exit__(None, None, None)
        import shutil
        shutil.rmtree(self._work, ignore_errors=True)

    def test_capture_records_pending_job(self, monkeypatch):
        _enable_ci(monkeypatch)
        ctx = self._context(test_file_path=str(self._test_path))
        with (
            patch.object(Sandbox, "run", return_value=dict(UNAVAILABLE_RUN)),
            patch.object(Sandbox, "run_tests", return_value=dict(UNAVAILABLE_TESTS)),
        ):
            ValidatorAgent().execute(ctx)
        cand = ctx["patch_candidates"][0]
        assert cand["validation_details"]["static_only"] is True
        assert cand["validation_details"].get("validated_by") is None
        jobs = get_pending_validations_for_commit("alice/app", "abc123")
        assert len(jobs) == 1
        assert jobs[0]["candidate_id"] == "baseline_ast"
        assert jobs[0]["source_filename"] == "main.py"
        assert jobs[0]["patched_code"] == SAFE_CODE
        assert "test_add" in jobs[0]["test_content"]

    def test_inject_completed_ci_result(self, monkeypatch):
        _enable_ci(monkeypatch)
        # First pass captures the pending job...
        ctx = self._context(test_file_path=str(self._test_path))
        with (
            patch.object(Sandbox, "run", return_value=dict(UNAVAILABLE_RUN)),
            patch.object(Sandbox, "run_tests", return_value=dict(UNAVAILABLE_TESTS)),
        ):
            ValidatorAgent().execute(ctx)
        jid = get_pending_validations_for_commit("alice/app", "abc123")[0]["id"]
        # ...CI runner completes it with runtime evidence...
        complete_pending_validation(
            jid, ci_validation.build_result_json(CI_SANDBOX, CI_TESTS, SAFE_CODE)
        )
        # ...and the re-analysis re-injects it.
        ctx2 = self._context(test_file_path=str(self._test_path))
        with (
            patch.object(Sandbox, "run", return_value=dict(UNAVAILABLE_RUN)),
            patch.object(Sandbox, "run_tests", return_value=dict(UNAVAILABLE_TESTS)),
        ):
            ValidatorAgent().execute(ctx2)
        cand = ctx2["patch_candidates"][0]
        assert cand["validation_details"]["validated_by"] == "ci_runner"
        assert cand["validation_details"]["static_only"] is False
        assert cand["validation_details"]["sandbox"] == CI_SANDBOX
        assert cand["test_results"] == CI_TESTS
        assert cand["validation_score"] >= 0.9

    def test_capture_skipped_when_ci_disabled(self, monkeypatch):
        monkeypatch.setattr(config.app.ci_runner, "enabled", False)
        ctx = self._context(test_file_path=str(self._test_path))
        with (
            patch.object(Sandbox, "run", return_value=dict(UNAVAILABLE_RUN)),
            patch.object(Sandbox, "run_tests", return_value=dict(UNAVAILABLE_TESTS)),
        ):
            ValidatorAgent().execute(ctx)
        assert get_pending_validations_for_commit("alice/app", "abc123") == []
        cand = ctx["patch_candidates"][0]
        assert cand["validation_details"]["static_only"] is True


class TestCiValidationEndpoints:
    def setup_method(self):
        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()
        self._tmp_db = _TmpDb()
        self._tmp_db.__enter__()

    def teardown_method(self):
        self._tmp_db.__exit__(None, None, None)

    def _seed_job(self, monkeypatch):
        _enable_ci(monkeypatch)
        jid = record_pending_validation(
            repo_full_name="alice/app", pr_number=1, commit_sha="abc123",
            source_filename="main.py", candidate_id="baseline_ast",
            patched_code=SAFE_CODE, test_filename="test_main.py",
            test_content="def test_add(): pass", scan_mode="docker_only",
        )
        return jid

    def test_get_job_requires_secret(self, monkeypatch):
        jid = self._seed_job(monkeypatch)
        assert self.client.get(f"/api/ci-validation/jobs/{jid}").status_code == 401
        bad = {"X-CI-Validation-Secret": "wrong"}
        assert self.client.get(f"/api/ci-validation/jobs/{jid}", headers=bad).status_code == 401
        good = {"X-CI-Validation-Secret": "s3cret"}
        resp = self.client.get(f"/api/ci-validation/jobs/{jid}", headers=good)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["patched_code"] == SAFE_CODE
        assert body["scan_mode"] == "docker_only"
        assert body["test_content"].startswith("def test_add")

    def test_get_job_unknown(self, monkeypatch):
        _enable_ci(monkeypatch)
        good = {"X-CI-Validation-Secret": "s3cret"}
        assert self.client.get("/api/ci-validation/jobs/9999", headers=good).status_code == 404

    def test_post_results_stores_and_triggers_revalidation(self, monkeypatch):
        jid = self._seed_job(monkeypatch)
        scan_id = _seed_repo_and_scan()
        udb.mark_scan_validation_pending(scan_id)
        with patch.object(app_module, "_revalidate_pending_scan") as mock_reval:
            resp = self.client.post(
                "/api/ci-validation/results",
                json={"job_id": jid, "status": "completed", "sandbox_res": CI_SANDBOX, "test_results": CI_TESTS},
                headers={"X-CI-Validation-Secret": "s3cret"},
            )
        assert resp.status_code == 200
        assert count_ci_results_available("alice/app", "abc123") == 1
        assert mock_reval.call_count == 1
        called = mock_reval.call_args[0][0]
        assert called["id"] == scan_id

    def test_post_results_requires_secret(self, monkeypatch):
        jid = self._seed_job(monkeypatch)
        assert self.client.post(
            "/api/ci-validation/results", json={"job_id": jid}
        ).status_code == 401
        assert count_ci_results_available("alice/app", "abc123") == 0

    def test_post_results_unknown_and_missing_job(self, monkeypatch):
        _enable_ci(monkeypatch)
        good = {"X-CI-Validation-Secret": "s3cret"}
        resp = self.client.post("/api/ci-validation/results", json={}, headers=good)
        assert resp.status_code == 400
        resp = self.client.post(
            "/api/ci-validation/results", json={"job_id": 9999}, headers=good
        )
        assert resp.status_code == 404


class TestCiDispatch:
    def test_dispatch_sends_repository_dispatch(self, monkeypatch):
        monkeypatch.setattr(config.app.ci_runner, "enabled", True)
        monkeypatch.setattr(config.app.ci_runner, "workflow_repo", "acme/arg-worker")
        monkeypatch.setattr(config.app.ci_runner, "event_type", "ai-risk-guard-validate")
        monkeypatch.setenv(config.app.ci_runner.token_env, "ghp_worker")
        monkeypatch.setenv(config.app.ci_runner.secret_env, "s3cret")
        monkeypatch.setenv("CI_VALIDATION_BASE_URL", "https://arg.example")
        sent = {}

        class _FakeResponse:
            status_code = 204

        def fake_post(url, json=None, headers=None, timeout=30):
            sent["url"] = url
            sent["json"] = json
            return _FakeResponse()

        monkeypatch.setattr(ci_dispatch.requests, "post", fake_post)
        assert ci_dispatch.dispatch_validation_jobs("alice/app", 1, "abc123", [7, 8]) is True
        assert sent["url"] == "https://api.github.com/repos/acme/arg-worker/dispatches"
        payload = sent["json"]
        assert payload["event_type"] == "ai-risk-guard-validate"
        assert payload["client_payload"]["job_ids"] == [7, 8]
        assert payload["client_payload"]["repo"] == "alice/app"
        assert payload["client_payload"]["ref"] == "abc123"
        assert payload["client_payload"]["base_url"] == "https://arg.example"

    def test_dispatch_skips_when_not_configured(self, monkeypatch):
        monkeypatch.setattr(config.app.ci_runner, "enabled", False)
        assert ci_dispatch.dispatch_validation_jobs("alice/app", 1, "abc123", [7]) is False

    def test_app_dispatch_hook_marks_jobs_dispatched(self, monkeypatch):
        with _TmpDb():
            _enable_ci(monkeypatch)
            jid = record_pending_validation(
                repo_full_name="alice/app", pr_number=1, commit_sha="abc123",
                source_filename="main.py", candidate_id="baseline_ast",
                patched_code=SAFE_CODE,
            )
            with (
                patch.object(ci_dispatch, "ci_validation_configured", return_value=True),
                patch.object(ci_dispatch, "dispatch_validation_jobs", return_value=True),
            ):
                app_module.dispatch_pending_ci_validation("alice/app", 1, "abc123")
            assert get_pending_validation(jid)["status"] == "dispatched"

    def test_app_dispatch_skips_without_commit(self, monkeypatch):
        with _TmpDb():
            _enable_ci(monkeypatch)
            with patch.object(ci_dispatch, "dispatch_validation_jobs") as mock_dispatch:
                app_module.dispatch_pending_ci_validation("alice/app", 1, "")
            mock_dispatch.assert_not_called()


class TestHarness:
    def test_parse_job_ids(self):
        from ci.validate import _parse_job_ids
        assert _parse_job_ids("[1, 2, 3]") == [1, 2, 3]
        assert _parse_job_ids("1 2 3") == [1, 2, 3]
        assert _parse_job_ids("4,5") == [4, 5]
        assert _parse_job_ids("") == []
        assert _parse_job_ids("7") == [7]
