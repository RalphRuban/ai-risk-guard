"""
tests/test_codeql_provisioner.py

Phase 4.3 — CodeQL provisioning: unit tests for the provisioner and webhook
integration (installation.created / installation_repositories.added).
"""

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


def _csrf_headers(client):
    client.get("/api/me")
    cookie = client.get_cookie("csrf_token")
    return {"X-CSRF-Token": cookie.value} if cookie else {}


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

    def test_refreshes_files_when_pr_open(self):
        """An open provisioning PR is updated in place, not skipped."""
        existing = {"html_url": "https://github.com/owner/repo/pull/20"}
        with (
            patch.object(prov, "workflow_exists", return_value=False),
            patch.object(prov, "_open_provisioning_pr", return_value=existing),
            patch.object(prov, "_resolve_default_branch", return_value="main"),
            patch.object(prov, "_put_file", return_value=True) as mock_put,
            patch.object(prov, "_create_branch", return_value=True) as mock_branch,
            patch.object(prov, "_get_default_branch_sha", return_value="sha") as mock_sha,
            patch.object(prov.requests, "post") as mock_post,
        ):
            result = prov.create_codeql_pr("owner/repo", "token", language="Python")

        assert result == "https://github.com/owner/repo/pull/20"
        assert mock_put.call_count == 2
        mock_branch.assert_not_called()
        mock_sha.assert_not_called()
        mock_post.assert_not_called()

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
            result = prov.create_codeql_pr("owner/repo", "token", default_branch="main", language="Python")

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

    def test_swallows_branch_creation_failure(self):
        with (
            patch.object(prov.requests, "get", return_value=_resp(200, json_data={"object": {"sha": "s"}})),
            patch.object(prov.requests, "post", return_value=_resp(422, text="branch exists")),
        ):
            assert prov.create_codeql_pr("owner/repo", "token", language="Python") is None

    def test_swallows_exceptions(self):
        with patch.object(prov.requests, "get", side_effect=Exception("boom")):
            assert prov.create_codeql_pr("owner/repo", "token") is None


# ---------------------------------------------------------------
# Templates (CodeQL workflow / config content)
# ---------------------------------------------------------------

class TestCodeqlTemplates:
    def test_workflow_uses_codeql_action_v4(self):
        yaml = prov._read_template("codeql.yml")
        assert "github/codeql-action/init@v4" in yaml
        assert "github/codeql-action/autobuild@v4" in yaml
        assert "github/codeql-action/analyze@v4" in yaml
        assert "@v3" not in yaml

    def test_workflow_uses_checkout_v5(self):
        yaml = prov._read_template("codeql.yml")
        assert "actions/checkout@v5" in yaml
        assert "checkout@v4" not in yaml

    def test_config_does_not_ignore_demo_files(self):
        yaml = prov._read_template("codeql-config.yml")
        assert "tests/**" in yaml
        assert "**/test_*.py" in yaml
        assert "demo" not in yaml


# ---------------------------------------------------------------
# _map_languages / _detect_repo_languages
# ---------------------------------------------------------------

class TestMapLanguages:
    def test_python_hint(self):
        assert prov._map_languages("Python") == ["python"]

    def test_javascript_hint(self):
        assert prov._map_languages("JavaScript") == ["javascript"]
        assert prov._map_languages("TypeScript") == ["javascript"]
        assert prov._map_languages("Node") == ["javascript"]

    def test_unknown_hint_is_empty_not_fallback(self):
        assert prov._map_languages("Rust") == []
        assert prov._map_languages("") == []
        assert prov._map_languages(None) == []

    def test_language_name_mapping(self):
        assert prov._map_language_name("Python") == "python"
        assert prov._map_language_name("JavaScript") == "javascript"
        assert prov._map_language_name("Java") == "java"
        assert prov._map_language_name("C++") == "cpp"
        assert prov._map_language_name("C#") == "csharp"
        assert prov._map_language_name("Swift") == "swift"
        assert prov._map_language_name("Nothing") is None
        assert prov._map_language_name(None) is None


class TestDetectRepoLanguages:
    def test_maps_detected_breakdown(self):
        with patch.object(
            prov.requests,
            "get",
            return_value=_resp(200, json_data={"JavaScript": 500, "Python": 300, "HTML": 100}),
        ) as mock_get:
            assert prov._detect_repo_languages("owner/repo", "token") == ["javascript", "python"]
        assert mock_get.call_args[0][0].endswith("/languages")

    def test_empty_on_api_error(self):
        with patch.object(prov.requests, "get", return_value=_resp(500, text="boom")):
            assert prov._detect_repo_languages("owner/repo", "token") == []

    def test_empty_on_exception(self):
        with patch.object(prov.requests, "get", side_effect=Exception("network")):
            assert prov._detect_repo_languages("owner/repo", "token") == []

    def test_no_languages_when_detection_empty(self):
        """No hint + empty detection -> provisioning is skipped, not guessed."""
        with patch.object(prov, "workflow_exists", return_value=False), patch.object(
            prov, "_open_provisioning_pr", return_value=None
        ), patch.object(prov, "_detect_repo_languages", return_value=[]):
            assert prov.create_codeql_pr("owner/repo", "token") is None

    def test_detection_fallback_when_hint_missing(self):
        """No hint + detected JS -> JavaScript matrix is provisioned."""
        with patch.object(prov, "workflow_exists", return_value=False), patch.object(
            prov, "_open_provisioning_pr", return_value=None
        ), patch.object(prov, "_detect_repo_languages", return_value=["javascript"]), patch.object(
            prov, "_resolve_default_branch", return_value="main"
        ), patch.object(prov, "_get_default_branch_sha", return_value="sha"), patch.object(
            prov, "_create_branch", return_value=True
        ), patch.object(prov, "_put_file", return_value=True), patch.object(
            prov.requests, "post", return_value=_resp(201, json_data={"html_url": "https://github.com/o/r/pull/5"})
        ):
            result = prov.create_codeql_pr("owner/repo", "token")
        assert result == "https://github.com/o/r/pull/5"


# ---------------------------------------------------------------
# _provision_codeql_for_repos (app wiring)
# ---------------------------------------------------------------

class TestProvisionForRepos:
    def test_calls_create_codeql_pr_per_repo(self):
        repos = [
            {"full_name": "owner/one", "default_branch": "main", "language": "Python"},
            {"full_name": "owner/two", "default_branch": "dev", "language": "JavaScript"},
        ]
        with patch.object(app_module, "get_cached_token", return_value="token"), patch.object(
            app_module, "create_codeql_pr"
        ) as mock_pr:
            app_module._provision_codeql_for_repos(repos, 5)
        assert mock_pr.call_count == 2
        mock_pr.assert_any_call("owner/one", "token", default_branch="main", language="Python")
        mock_pr.assert_any_call("owner/two", "token", default_branch="dev", language="JavaScript")

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
# _codeql_enabled_for_owner (per-user Settings toggle)
# ---------------------------------------------------------------

class TestCodeqlEnabledForOwner:
    def test_defaults_true_when_repo_missing(self):
        with patch.object(app_module, "get_repo", return_value=None):
            assert app_module._codeql_enabled_for_owner(1) is True

    def test_defaults_true_when_repo_unattributed(self):
        with patch.object(app_module, "get_repo", return_value={"user_id": None}):
            assert app_module._codeql_enabled_for_owner(1) is True

    def test_respects_user_toggle(self):
        with patch.object(app_module, "get_repo", return_value={"user_id": 7}), patch.object(
            app_module, "get_user_settings", return_value={"codeql_enabled": False}
        ):
            assert app_module._codeql_enabled_for_owner(1) is False

    def test_defaults_true_on_lookup_error(self):
        with patch.object(app_module, "get_repo", side_effect=Exception("boom")):
            assert app_module._codeql_enabled_for_owner(1) is True


# ---------------------------------------------------------------
# POST /api/repos/<id>/codeql gating
# ---------------------------------------------------------------

class TestEnableCodeqlApi:
    def setup_method(self):
        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()

    def test_blocked_when_codeql_toggle_off(self):
        with self.client.session_transaction() as sess:
            sess["user"] = {"github_id": "111", "login": "alice"}
        with patch.object(app_module, "get_repo", return_value={"full_name": "o/r", "install_id": 1}), patch.object(
            app_module, "_codeql_enabled_for_owner", return_value=False
        ), patch.object(app_module, "create_codeql_pr") as mock_pr:
            resp = self.client.post("/api/repos/1/codeql", headers=_csrf_headers(self.client))
        assert resp.status_code == 400
        assert "disabled in Settings" in resp.get_json()["error"]
        mock_pr.assert_not_called()

    def test_allowed_when_codeql_toggle_on(self):
        with self.client.session_transaction() as sess:
            sess["user"] = {"github_id": "111", "login": "alice"}
        with patch.object(app_module, "get_repo", return_value={"full_name": "o/r", "install_id": 1}), patch.object(
            app_module, "_codeql_enabled_for_owner", return_value=True
        ), patch.object(app_module, "get_cached_token", return_value="token"), patch.object(
            app_module, "create_codeql_pr", return_value="https://github.com/o/r/pull/1"
        ) as mock_pr, patch.object(app_module, "mark_repo_codeql_provisioned") as mock_mark, patch.object(
            app_module, "_clear_codeql_attempted"
        ) as mock_clear:
            resp = self.client.post("/api/repos/1/codeql", headers=_csrf_headers(self.client))
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True
        mock_pr.assert_called_once()
        mock_mark.assert_called_once_with("o/r")
        mock_clear.assert_called_once_with("o/r")


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
