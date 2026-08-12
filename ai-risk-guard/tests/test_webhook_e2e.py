"""
tests/test_webhook_e2e.py
End-to-end webhook tests: HMAC signature verification, dispatch/dedup, and
the full webhook → staging → sandbox pipeline (Docker-optional).

GitHub API, PR comment/SARIF posting, and the sandbox are stubbed so the
tests run offline. The pipeline test verifies commit-SHA threading and that
the staged test dependencies (conftest/helpers) reach the sandbox ``run_tests``
call — the regression behind scan #5.
"""

import base64
import hashlib
import hmac
import json
import re
import subprocess
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from app import app as app_module
from app.app import app as flask_app
from utils.db import get_repo_scans, upsert_repo

app_module.GITHUB_WEBHOOK_SECRET = "test-secret"

SOURCE = "import os\nos.system('ls')\n"
TEST_CONTENT = "from demo1 import fetch_url\n\ndef test_f():\n    assert fetch_url()\n"
SANDBOX_OK = {"success": True, "skipped": False, "mode": "local", "output": "1 passed", "error": ""}


def _sign(payload: bytes, secret: str = "test-secret") -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def _b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        return self._json


class FakeGitHub:
    """In-memory GitHub Contents/Pulls API stand-in."""

    def __init__(self):
        self.files = {
            "demo1.py": SOURCE,
            "tests/test_demo1.py": TEST_CONTENT,
            "conftest.py": "import pytest\n",
        }
        self.get_urls = []

    def get(self, url, **kwargs):
        self.get_urls.append(url)
        if re.search(r"/pulls/\d+/files", url):
            return FakeResponse(200, [{
                "filename": "demo1.py",
                "status": "modified",
                "patch": "@@ -1,2 +1,2 @@\n-import os\n+import subprocess\n",
            }])
        m = re.search(r"/contents/(.+?)\?", url)
        if m:
            content = self.files.get(m.group(1))
            if content is None:
                return FakeResponse(404, text="Not Found")
            return FakeResponse(200, {"content": _b64(content)})
        return FakeResponse(404, text="Not Found")

    def post(self, url, **kwargs):
        return FakeResponse(200, {})


def _webhook_headers(payload: bytes, delivery_id: str) -> dict:
    return {
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": _sign(payload),
        "X-GitHub-Delivery": delivery_id,
        "Content-Type": "application/json",
    }


def _pr_payload(pr_number: int, delivery_id: str, head_sha: str, action: str = "opened") -> bytes:
    data = {
        "action": action,
        "installation": {"id": 90001},
        "repository": {
            "full_name": "acme/demo",
            "id": 1,
            "name": "demo",
            "owner": {"login": "acme"},
            "description": "",
            "language": "Python",
            "private": False,
            "default_branch": "main",
        },
        "pull_request": {
            "number": pr_number,
            "title": "e2e",
            "head": {"ref": "feature-branch", "sha": head_sha},
            "merged": False,
        },
    }
    return json.dumps(data).encode()


class TestWebhookRoute:
    def setup_method(self):
        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()

    def test_rejects_bad_signature(self):
        body = _pr_payload(1001, f"deliv-{uuid.uuid4().hex}", "sha-bad")
        headers = _webhook_headers(body, f"deliv-{uuid.uuid4().hex}")
        headers["X-Hub-Signature-256"] = "sha256=deadbeef"
        resp = self.client.post("/webhook", data=body, headers=headers)
        assert resp.status_code == 403

    def test_rejects_when_secret_missing(self):
        body = _pr_payload(1002, f"deliv-{uuid.uuid4().hex}", "sha-x")
        headers = _webhook_headers(body, f"deliv-{uuid.uuid4().hex}")
        original = app_module.GITHUB_WEBHOOK_SECRET
        app_module.GITHUB_WEBHOOK_SECRET = ""
        try:
            resp = self.client.post("/webhook", data=body, headers=headers)
        finally:
            app_module.GITHUB_WEBHOOK_SECRET = original
        assert resp.status_code == 403

    def test_accepts_signed_pull_request(self):
        delivery = f"deliv-{uuid.uuid4().hex}"
        body = _pr_payload(1003, delivery, "sha-accept")
        with patch.object(app_module, "executor", Mock()) as fake_exec:
            resp = self.client.post("/webhook", data=body, headers=_webhook_headers(body, delivery))
        try:
            app_module._analysis_slot.release()
        except ValueError:
            pass
        assert resp.status_code == 202
        fake_exec.submit.assert_called_once()

    def test_duplicate_delivery_skipped(self):
        delivery = f"deliv-{uuid.uuid4().hex}"
        body = _pr_payload(1004, delivery, "sha-dup")
        with patch.object(app_module, "executor", Mock()):
            first = self.client.post("/webhook", data=body, headers=_webhook_headers(body, delivery))
            second = self.client.post("/webhook", data=body, headers=_webhook_headers(body, delivery))
        try:
            app_module._analysis_slot.release()
        except ValueError:
            pass
        assert first.status_code == 202
        assert second.status_code == 200
        assert b"duplicate" in second.data

    def test_ignores_unknown_event(self):
        body = _pr_payload(1005, f"deliv-{uuid.uuid4().hex}", "sha-ign")
        headers = _webhook_headers(body, f"deliv-{uuid.uuid4().hex}")
        headers["X-GitHub-Event"] = "ping"
        resp = self.client.post("/webhook", data=body, headers=headers)
        assert resp.status_code == 200


class TestWebhookPipeline:
    def _run(self, sandbox_run=True):
        install_id = 90200
        pr_number = 500000 + uuid.uuid4().int % 100000
        head_sha = "e2e" + uuid.uuid4().hex[:12]
        repo = f"acme/demo-{uuid.uuid4().hex[:8]}"
        repo_id = 900000 + uuid.uuid4().int % 10000
        gh = FakeGitHub()
        upsert_repo({
            "id": repo_id,
            "full_name": repo,
            "owner": "acme",
            "name": repo.split("/")[1],
            "description": "",
            "language": "Python",
            "private": 0,
            "default_branch": "main",
            "install_id": install_id,
        })
        app_module.token_cache[install_id] = {
            "token": "fake-token",
            "expiry": datetime.now() + timedelta(hours=1),  # noqa: DTZ005
        }
        labeled = {
            "requests.get": patch("requests.get", side_effect=gh.get),
            "requests.post": patch("requests.post", side_effect=gh.post),
            "post_pr_comment": patch("app.app.post_pr_comment"),
            "find_existing_comment": patch("app.app.find_existing_bot_comment"),
            "upload_sarif": patch("app.app.upload_sarif_to_code_scanning"),
            "check_dismissed": patch("app.app.check_all_alerts_dismissed", return_value=False),
            "set_pr_labels": patch("core.agents.orchestrator_agent.set_pr_labels"),
        }
        if sandbox_run:
            labeled["sandbox_run"] = patch(
                "core.validator.sandbox.Sandbox.run",
                return_value={"success": True, "output": "ok"},
            )
            labeled["sandbox_run_tests"] = patch(
                "core.validator.sandbox.Sandbox.run_tests",
                return_value=SANDBOX_OK,
            )
        mocks = {name: p.start() for name, p in labeled.items()}
        try:
            app_module.run_async_analysis(repo, repo_id, pr_number, "e2e", install_id, "feature-branch", head_sha)
        finally:
            for p in labeled.values():
                p.stop()
        return gh, mocks, pr_number, head_sha, repo_id

    def test_pipeline_threads_commit_sha_into_fetch(self):
        gh, _mocks, _pr, head_sha, _rid = self._run()
        assert any(f"ref={head_sha}" in url for url in gh.get_urls)

    def test_pipeline_stages_deps_into_sandbox(self):
        _gh, mocks, _pr, _sha, _rid = self._run()
        run_tests = mocks["sandbox_run_tests"]
        assert run_tests.call_count > 0
        extra_files = run_tests.call_args_list[0].kwargs.get("extra_files") or []
        dep_paths = {d["path"] for d in extra_files}
        assert "conftest.py" in dep_paths

    def test_pipeline_records_scan(self):
        _gh, _mocks, pr, _sha, repo_id = self._run()
        scans = get_repo_scans(repo_id)
        assert any(s["pr_number"] == pr for s in scans)


def _docker_available() -> bool:
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=10, check=False)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


@pytest.mark.skipif(not _docker_available(), reason="Docker daemon not running")
class TestDockerPipeline:
    def test_pipeline_runs_with_real_sandbox(self):
        _gh, _mocks, pr, _sha, repo_id = TestWebhookPipeline()._run(sandbox_run=False)
        scans = get_repo_scans(repo_id)
        assert any(s["pr_number"] == pr for s in scans)

    def test_container_mount_is_read_only(self):
        """The workspace is bind-mounted read-only: writes to /app must fail."""
        from core.validator.sandbox import Sandbox
        code = (
            "try:\n"
            "    with open('smoke_write.txt', 'w') as f:\n"
            "        f.write('x')\n"
            "    print('WRITE_OK')\n"
            "except OSError as e:\n"
            "    print('WRITE_BLOCKED:' + type(e).__name__)\n"
        )
        result = Sandbox().run(code, source_filename="smoke.py")
        assert result.get("success") is True
        assert "WRITE_BLOCKED" in result.get("output", "")

    def test_container_network_is_blocked(self):
        """The container runs with --network=none: external sockets must fail."""
        from core.validator.sandbox import Sandbox
        code = (
            "import socket\n"
            "try:\n"
            "    socket.create_connection(('1.1.1.1', 53), timeout=3)\n"
            "    print('NET_OK')\n"
            "except OSError:\n"
            "    print('NET_BLOCKED')\n"
        )
        result = Sandbox().run(code, source_filename="smoke.py")
        assert result.get("success") is True
        assert "NET_BLOCKED" in result.get("output", "")
