"""
tests/test_codeql_provisioner.py

Phase 4.3 — CodeQL provisioning: unit tests for the provisioner and webhook
integration (installation.created / installation_repositories.added).
"""

import base64
import hashlib
import hmac
import json
import uuid
from unittest.mock import MagicMock, Mock, patch

from app import app as app_module
from app.app import app as flask_app
from services.github import codeql_provisioner as prov

app_module.GITHUB_WEBHOOK_SECRET = "test-secret"


def _sign(payload: bytes, secret: str = "test-secret") -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def _resp(status_code, json_data=None, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data
    r.text = text
    return r


# ---------------------------------------------------------------
# workflow_exists
# ---------------------------------------------------------------

class TestWorkflowExists:
    def test_returns_true_when_workflow_present(self):
        with patch.object(prov.requests, "get", return_value=_resp(200)) as mock_get:
            assert prov.workflow_exists("owner/repo", "token") is True
        assert "contents/.github/workflows/codeql.yml" in mock_get.call_args[0][0]

    def test_returns_false_when_workflow_missing(self):
        with patch.object(prov.requests, "get", return_value=_resp(404)):
            assert prov.workflow_exists("owner/repo", "token") is False

    def test_returns_false_on_api_error(self):
        with patch.object(prov.requests, "get", return_value=_resp(403, text="forbidden")):
            assert prov.workflow_exists("owner/repo", "token") is False

    def test_returns_false_on_exception(self):
        with patch.object(prov.requests, "get", side_effect=Exception("boom")):
            assert prov.workflow_exists("owner/repo", "token") is False


# ---------------------------------------------------------------
# provisioning_pr_open
# ---------------------------------------------------------------

class TestProvisioningPrOpen:
    def test_true_when_pr_exists(self):
        with patch.object(
            prov.requests, "get", return_value=_resp(200, json_data=[{"number": 1}])
        ) as mock_get:
            assert prov.provisioning_pr_open("owner/repo", "token") is True
        assert mock_get.call_args[1]["params"]["head"].startswith("owner:")

    def test_false_when_no_pr(self):
        with patch.object(prov.requests, "get", return_value=_resp(200, json_data=[])):
            assert prov.provisioning_pr_open("owner/repo", "token") is False

    def test_false_on_error(self):
        with patch.object(prov.requests, "get", return_value=_resp(500, text="nope")):
            assert prov.provisioning_pr_open("owner/repo", "token") is False


# ---------------------------------------------------------------
# create_codeql_pr
# ---------------------------------------------------------------

class TestCreateCodeqlPr:
    def test_skips_when_workflow_exists(self):
        with patch.object(prov, "workflow_exists", return_value=True), patch.object(
            prov, "provisioning_pr_open", return_value=False
        ):
            assert prov.create_codeql_pr("owner/repo", "token") is None

    def test_skips_when_pr_open(self):
        with patch.object(prov, "workflow_exists", return_value=False), patch.object(
            prov, "provisioning_pr_open", return_value=True
        ):
            assert prov.create_codeql_pr("owner/repo", "token") is None

    def test_skips_when_disabled(self):
        with patch.object(prov.config.app.codeql, "enabled", False), patch.object(
            prov, "workflow_exists", return_value=False
        ):
            assert prov.create_codeql_pr("owner/repo", "token") is None

    def test_success_creates_branch_files_and_pr(self):
        def fake_get(url, **kwargs):
            if "git/ref/heads" in url:
                return _resp(200, json_data={"object": {"sha": "base-sha-1"}})
            return _resp(404)

        with (
            patch.object(prov.requests, "get", side_effect=fake_get),
            patch.object(prov.requests, "post") as mock_post,
            patch.object(prov.requests, "put") as mock_put,
        ):
            mock_post.return_value = _resp(201, json_data={"html_url": "https://github.com/owner/repo/pull/9"})
            mock_put.return_value = _resp(201, json_data={})
            result = prov.create_codeql_pr("owner/repo", "token", default_branch="main")

        assert result == "https://github.com/owner/repo/pull/9"

        posts = [c for c in mock_post.call_args_list]
        refs_call = posts[0]
        assert refs_call[0][0].endswith("/git/refs")
        assert refs_call[1]["json"]["ref"] == "refs/heads/ai-risk-guard/codeql-setup"
        assert refs_call[1]["json"]["sha"] == "base-sha-1"

        pr_call = posts[1]
        assert pr_call[0][0].endswith("/pulls")
        assert pr_call[1]["json"]["title"] == "Enable GitHub CodeQL analysis (via AI Risk Guard)"
        assert pr_call[1]["json"]["head"] == "ai-risk-guard/codeql-setup"
        assert pr_call[1]["json"]["base"] == "main"

        put_paths = [c[0][0] for c in mock_put.call_args_list]
        assert any(p.endswith(".github/workflows/codeql.yml") for p in put_paths)
        assert any(p.endswith(".github/codeql/codeql-config.yml") for p in put_paths)
        for c in mock_put.call_args_list:
            assert c[1]["json"]["branch"] == "ai-risk-guard/codeql-setup"
            assert "sha" not in c[1]["json"]

        wf_put = next(
            c for c in mock_put.call_args_list
            if c[0][0].endswith("/codeql.yml")
        )
        workflow = base64.b64decode(wf_put[1]["json"]["content"]).decode()
        assert "branches: [main]" in workflow
        assert "language: [python, javascript]" in workflow

    def test_renders_resolved_branch_and_single_language_matrix(self):
        def fake_get(url, **kwargs):
            if url.endswith("/repos/owner/repo"):
                return _resp(200, json_data={"default_branch": "master"})
            if "git/ref/heads" in url:
                return _resp(200, json_data={"object": {"sha": "base-sha-1"}})
            return _resp(404)

        with (
            patch.object(prov.requests, "get", side_effect=fake_get),
            patch.object(
                prov.requests, "post",
                return_value=_resp(201, json_data={"html_url": "https://github.com/owner/repo/pull/1"}),
            ) as mock_post,
            patch.object(prov.requests, "put", return_value=_resp(201, json_data={})) as mock_put,
        ):
            result = prov.create_codeql_pr("owner/repo", "token", language="Python")

        assert result == "https://github.com/owner/repo/pull/1"
        pr_call = next(c for c in mock_post.call_args_list if c[0][0].endswith("/pulls"))
        assert pr_call[1]["json"]["base"] == "master"
        assert pr_call[1]["json"]["head"] == "ai-risk-guard/codeql-setup"
        wf_put = next(
            c for c in mock_put.call_args_list
            if c[0][0].endswith("/codeql.yml")
        )
        workflow = base64.b64decode(wf_put[1]["json"]["content"]).decode()
        assert "branches: [master]" in workflow
        assert "language: [python]" in workflow
        pr_body = pr_call[1]["json"]["body"]
        assert "for **python**" in pr_body

    def test_put_file_includes_sha_when_file_exists(self):
        def fake_get(url, **kwargs):
            if "/contents/" in url:
                return _resp(200, json_data={"sha": "abc123"})
            return _resp(404)

        with (
            patch.object(prov.requests, "get", side_effect=fake_get),
            patch.object(prov.requests, "put") as mock_put,
        ):
            mock_put.return_value = _resp(201, json_data={})
            ok = prov._put_file(
                "owner/repo", "token", ".github/workflows/codeql.yml", "yaml", "ai-risk-guard/codeql-setup"
            )
        assert ok is True
        assert mock_put.call_args[1]["json"]["sha"] == "abc123"

    def test_swallows_branch_creation_failure(self):
        with (
            patch.object(prov.requests, "get", return_value=_resp(200, json_data={"object": {"sha": "s"}})),
            patch.object(prov.requests, "post", return_value=_resp(422, text="branch exists")),
            patch.object(prov.requests, "put", return_value=_resp(201, json_data={})),
        ):
            assert prov.create_codeql_pr("owner/repo", "token") is None

    def test_swallows_exceptions(self):
        with patch.object(prov.requests, "get", side_effect=Exception("boom")):
            assert prov.create_codeql_pr("owner/repo", "token") is None


# ---------------------------------------------------------------
# _provision_codeql_for_repos (app wiring)
# ---------------------------------------------------------------

class TestProvisionForRepos:
    def test_calls_create_codeql_pr_per_repo(self):
        repos = [
            {"full_name": "owner/one", "default_branch": "main"},
            {"full_name": "owner/two", "default_branch": "dev"},
        ]
        with patch.object(app_module, "get_cached_token", return_value="token"), patch.object(
            app_module, "create_codeql_pr"
        ) as mock_pr:
            app_module._provision_codeql_for_repos(repos, 5)
        assert mock_pr.call_count == 2
        mock_pr.assert_any_call("owner/one", "token", default_branch="main", language=None)
        mock_pr.assert_any_call("owner/two", "token", default_branch="dev", language=None)

    def test_skips_when_disabled(self):
        with patch.object(app_module.config.app.codeql, "enabled", False), patch.object(
            app_module, "get_cached_token", return_value="token"
        ), patch.object(app_module, "create_codeql_pr") as mock_pr:
            app_module._provision_codeql_for_repos([{"full_name": "o/r"}], 5)
        mock_pr.assert_not_called()

    def test_noop_without_repos(self):
        with patch.object(app_module, "get_cached_token", return_value="token"), patch.object(
            app_module, "create_codeql_pr"
        ) as mock_pr:
            app_module._provision_codeql_for_repos([], 5)
        mock_pr.assert_not_called()

    def test_handles_token_failure(self):
        with patch.object(app_module, "get_cached_token", side_effect=Exception("no token")), patch.object(
            app_module, "create_codeql_pr"
        ) as mock_pr:
            app_module._provision_codeql_for_repos([{"full_name": "o/r"}], 5)
        mock_pr.assert_not_called()


# ---------------------------------------------------------------
# webhook integration
# ---------------------------------------------------------------

def _install_headers(payload: bytes, event: str) -> dict:
    return {
        "X-GitHub-Event": event,
        "X-Hub-Signature-256": _sign(payload),
        "X-GitHub-Delivery": f"deliv-{uuid.uuid4().hex}",
        "Content-Type": "application/json",
    }


class TestWebhookProvisioning:
    def setup_method(self):
        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()

    def test_installation_created_triggers_provisioning(self):
        payload = json.dumps({
            "action": "created",
            "installation": {"id": 42},
            "repositories": [{"full_name": "owner/repo", "default_branch": "main"}],
        }).encode()
        with patch.object(app_module, "executor", Mock()) as fake_exec:
            resp = self.client.post(
                "/webhook", data=payload, headers=_install_headers(payload, "installation")
            )
        assert resp.status_code == 200
        assert fake_exec.submit.call_count == 1
        args = fake_exec.submit.call_args[0]
        assert args[0] == app_module._provision_codeql_for_repos
        assert args[1] == [{"full_name": "owner/repo", "default_branch": "main"}]
        assert args[2] == 42

    def test_installation_deleted_does_not_provision(self):
        payload = json.dumps({
            "action": "deleted",
            "installation": {"id": 7},
            "repositories": [{"full_name": "owner/repo"}],
        }).encode()
        with patch.object(app_module, "executor", Mock()) as fake_exec:
            resp = self.client.post(
                "/webhook", data=payload, headers=_install_headers(payload, "installation")
            )
        assert resp.status_code == 200
        fake_exec.submit.assert_not_called()

    def test_installation_repositories_added_triggers_provisioning(self):
        payload = json.dumps({
            "installation": {"id": 9},
            "repositories_added": [{"full_name": "owner/added", "default_branch": "main"}],
            "repositories_removed": [],
        }).encode()
        with patch.object(app_module, "executor", Mock()) as fake_exec:
            resp = self.client.post(
                "/webhook", data=payload, headers=_install_headers(payload, "installation_repositories")
            )
        assert resp.status_code == 200
        assert fake_exec.submit.call_count == 1
        assert fake_exec.submit.call_args[0][0] == app_module._provision_codeql_for_repos
        assert fake_exec.submit.call_args[0][1] == [{"full_name": "owner/added", "default_branch": "main"}]
