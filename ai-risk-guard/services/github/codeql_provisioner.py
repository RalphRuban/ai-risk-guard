"""
services/github/codeql_provisioner.py

Phase 4.3 — CodeQL provisioning for installed repos.

When the App is installed on (or added to) a repository, this module opens a
pull request that adds the standard GitHub CodeQL workflow so GitHub's own
hosted runners execute the analysis (zero App-side compute). Alerts appear
natively in the repository's Code Scanning, alongside ai-risk-guard's SARIF.

Best-effort by design: every failure is logged and swallowed, never raised
(mirrors the graceful-degradation pattern in reporter.py).
"""

import base64
from pathlib import Path

import requests

from core.config import config
from utils.logger import logger

API_BASE = "https://api.github.com"

WORKFLOW_PATH = ".github/workflows/codeql.yml"
CONFIG_PATH = ".github/codeql/codeql-config.yml"

_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "codeql"


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def _read_template(filename):
    """Load a provisioning template from templates/codeql/."""
    path = _TEMPLATE_DIR / filename
    return path.read_text(encoding="utf-8")


def workflow_exists(repository, token):
    """Return True when the target repo already has a CodeQL workflow file."""
    try:
        url = f"{API_BASE}/repos/{repository}/contents/{WORKFLOW_PATH}"
        response = requests.get(url, headers=_headers(token), timeout=30)
        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False
        logger.warning(
            f"CodeQL workflow check returned {response.status_code}: {response.text[:200]}",
            "CODEQL",
        )
        return False
    except Exception as e:
        logger.warning(f"CodeQL workflow check failed: {e}", "CODEQL")
        return False


def _open_provisioning_pr(repository, token):
    """Return the open provisioning PR dict for this repo, or None."""
    try:
        owner = repository.split("/")[0]
        head = f"{owner}:{config.app.codeql.workflow_branch}"
        url = f"{API_BASE}/repos/{repository}/pulls"
        response = requests.get(
            url,
            headers=_headers(token),
            params={"state": "open", "head": head},
            timeout=30,
        )
        if response.status_code != 200:
            logger.warning(
                f"CodeQL PR lookup returned {response.status_code}: {response.text[:200]}",
                "CODEQL",
            )
            return None
        pulls = response.json()
        return pulls[0] if pulls else None
    except Exception as e:
        logger.warning(f"CodeQL PR lookup failed: {e}", "CODEQL")
        return None


def provisioning_pr_open(repository, token):
    """Return True when a provisioning PR is already open for this repo."""
    return _open_provisioning_pr(repository, token) is not None


def _resolve_default_branch(repository, token, default_branch=None):
    """Return the repo's real default branch.

    Installation webhook payloads omit ``default_branch``, so the repo details
    API is queried when it is not supplied. Falls back to ``main`` only when
    the API call itself fails (never raises).
    """
    if default_branch:
        return default_branch
    try:
        url = f"{API_BASE}/repos/{repository}"
        response = requests.get(url, headers=_headers(token), timeout=30)
        if response.status_code == 200:
            return response.json().get("default_branch") or "main"
        logger.warning(
            f"CodeQL repo lookup returned {response.status_code}: {response.text[:200]}",
            "CODEQL",
        )
    except Exception as e:
        logger.warning(f"CodeQL repo lookup failed: {e}", "CODEQL")
    return "main"


def _get_default_branch_sha(repository, token, default_branch):
    """Return the head commit SHA of the default branch."""
    url = f"{API_BASE}/repos/{repository}/git/ref/heads/{default_branch}"
    response = requests.get(url, headers=_headers(token), timeout=30)
    if response.status_code != 200:
        logger.error(
            f"CodeQL default-branch lookup failed: {response.status_code} {response.text[:200]}",
            "CODEQL",
        )
        return None
    return response.json().get("object", {}).get("sha")


def _create_branch(repository, token, sha):
    """Create the provisioning branch at the given commit SHA."""
    branch = config.app.codeql.workflow_branch
    url = f"{API_BASE}/repos/{repository}/git/refs"
    payload = {"ref": f"refs/heads/{branch}", "sha": sha}
    response = requests.post(url, json=payload, headers=_headers(token), timeout=30)
    if response.status_code not in (201, 422):
        logger.error(
            f"CodeQL branch creation failed: {response.status_code} {response.text[:200]}",
            "CODEQL",
        )
        return False
    return True


def _get_file_sha(repository, token, path, branch):
    """Return the sha of an existing file on a branch, or None when missing."""
    try:
        url = f"{API_BASE}/repos/{repository}/contents/{path}"
        response = requests.get(
            url, headers=_headers(token), params={"ref": branch}, timeout=30
        )
        if response.status_code == 200:
            return response.json().get("sha")
    except Exception as e:
        logger.warning(f"CodeQL file sha lookup failed for {path}: {e}", "CODEQL")
    return None


def _put_file(repository, token, path, content, branch):
    """Create/update a single file on the provisioning branch.

    When the file already exists on the branch (e.g. an aborted earlier setup),
    its ``sha`` is included so the PUT updates in place instead of 422'ing.
    """
    url = f"{API_BASE}/repos/{repository}/contents/{path}"
    payload = {
        "message": f"Add {path} for CodeQL analysis",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    file_sha = _get_file_sha(repository, token, path, branch)
    if file_sha:
        payload["sha"] = file_sha
    response = requests.put(url, json=payload, headers=_headers(token), timeout=30)
    if response.status_code not in (200, 201):
        logger.error(
            f"CodeQL file push failed for {path}: {response.status_code} {response.text[:200]}",
            "CODEQL",
        )
        return False
    return True


def _map_language_name(name):
    """Map a single GitHub language name to its CodeQL language (or None).

    Unsupported or unknown languages return None so the caller can decide how
    to proceed instead of blindly enabling languages with no matching code.
    """
    if not name:
        return None
    lang = str(name).lower()
    if "python" in lang:
        return "python"
    if "javascript" in lang or "typescript" in lang or "node" in lang:
        return "javascript"
    if "java" in lang or "kotlin" in lang:
        return "java"
    if "c#" in lang or "csharp" in lang:
        return "csharp"
    if "c++" in lang or "cpp" in lang:
        return "cpp"
    if "go" in lang or "golang" in lang:
        return "go"
    if "ruby" in lang:
        return "ruby"
    if "swift" in lang:
        return "swift"
    return None


def _map_languages(language):
    """Map a GitHub language hint to a CodeQL language matrix.

    A known hint maps to a single CodeQL language; an unknown or missing hint
    returns an empty list so the caller falls back to the repo's actual code
    composition (never the full [python, javascript] guess that produced
    failing matrix jobs on single-language repos).
    """
    codeql = _map_language_name(language)
    return [codeql] if codeql else []


def _detect_repo_languages(repository, token):
    """Detect CodeQL languages from the repo's actual code composition.

    Queries the repository's language breakdown and maps each language to its
    CodeQL equivalent. Returns an empty list on any error (caller decides the
    fallback). Never raises.
    """
    try:
        url = f"{API_BASE}/repos/{repository}/languages"
        response = requests.get(url, headers=_headers(token), timeout=30)
        if response.status_code != 200:
            logger.warning(
                f"CodeQL language detection returned {response.status_code}: {response.text[:200]}",
                "CODEQL",
            )
            return []
        breakdown = response.json() or {}
        languages = []
        for name in sorted(breakdown, key=breakdown.get, reverse=True):
            codeql = _map_language_name(name)
            if codeql and codeql not in languages:
                languages.append(codeql)
        return languages
    except Exception as e:
        logger.warning(f"CodeQL language detection failed: {e}", "CODEQL")
        return []


def _build_pr_body(languages):
    """Render the CodeQL setup PR description for the target language matrix."""
    human = ", ".join(languages)
    return f"""This pull request enables [GitHub CodeQL](https://codeql.github.com/) for this repository.

What it does:
- Adds the standard CodeQL workflow (init → autobuild → analyze) for **{human}**.
- Adds a CodeQL config that skips test files (`tests/**`, `**/test_*.py`).
- Analysis runs on **GitHub's hosted runners** — no extra infrastructure required.

Once merged, CodeQL results appear under **Security → Code scanning** on every push and pull request to the default branch, alongside AI Risk Guard's findings.

Notes:
- Free on public repositories. Private repositories require a GitHub Code Security entitlement to view Code Scanning alerts.
- Opened automatically by the **AI Risk Guard** GitHub App.
"""


def create_codeql_pr(repository, token, default_branch=None, language=None):
    """Open a CodeQL setup PR for the given repo, or return None when skipped.

    The ``default_branch`` and ``language`` hints come from the webhook/DB
    payload; when the default branch is not supplied it is resolved from the
    repo details API. Returns the PR HTML URL on success, None when skipped or
    on any error. Never raises.
    """
    if not getattr(config.app.codeql, "enabled", True):
        logger.info(f"CodeQL provisioning disabled by config — skipping {repository}", "CODEQL")
        return None

    if workflow_exists(repository, token):
        logger.info(f"CodeQL already enabled on {repository} — skipping", "CODEQL")
        return None

    # If a provisioning PR is already open, refresh its files in place so the
    # PR self-heals when templates change (e.g. CodeQL action version bumps).
    existing_pr = _open_provisioning_pr(repository, token)

    default_branch = _resolve_default_branch(repository, token, default_branch)
    languages = _map_languages(language)
    if not languages:
        # Unknown hint — fall back to the repo's actual code composition.
        detected = _detect_repo_languages(repository, token)
        if detected:
            languages = detected
    if not languages:
        logger.warning(f"No detectable languages for {repository} — skipping CodeQL provisioning", "CODEQL")
        return None
    branch = config.app.codeql.workflow_branch
    try:
        if existing_pr is None:
            base_sha = _get_default_branch_sha(repository, token, default_branch)
            if not base_sha:
                return None

            if not _create_branch(repository, token, base_sha):
                return None

        workflow_yaml = _read_template("codeql.yml")
        workflow_yaml = (
            workflow_yaml.replace("__DEFAULT_BRANCH__", default_branch)
            .replace("__LANGUAGES__", ", ".join(languages))
        )
        config_yaml = _read_template("codeql-config.yml")
        if not _put_file(repository, token, WORKFLOW_PATH, workflow_yaml, branch):
            return None
        if not _put_file(repository, token, CONFIG_PATH, config_yaml, branch):
            return None

        if existing_pr is not None:
            pr_url = existing_pr.get("html_url") or ""
            logger.info(f"CodeQL provisioning PR refreshed for {repository}: {pr_url}", "CODEQL")
            return pr_url or None

        url = f"{API_BASE}/repos/{repository}/pulls"
        payload = {
            "title": config.app.codeql.pr_title,
            "head": branch,
            "base": default_branch,
            "body": _build_pr_body(languages),
        }
        response = requests.post(url, json=payload, headers=_headers(token), timeout=30)
        if response.status_code not in (200, 201):
            logger.error(
                f"CodeQL provisioning PR failed: {response.status_code} {response.text[:200]}",
                "CODEQL",
            )
            return None
        pr_url = response.json().get("html_url", "")
        logger.info(f"CodeQL provisioning PR opened for {repository}: {pr_url}", "CODEQL")
        return pr_url or None
    except Exception as e:
        logger.error(f"CodeQL provisioning failed for {repository}: {e}", "CODEQL")
        return None
