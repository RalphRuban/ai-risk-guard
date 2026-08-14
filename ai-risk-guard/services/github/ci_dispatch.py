"""
services/github/ci_dispatch.py

CI-runner fallback validation — GitHub dispatch (Phase E).

When the App's Docker daemon is unavailable, candidates that failed closed are
captured as ``pending_validations`` rows. This module dispatches them to the
workflow repo's ``repository_dispatch`` event so a GitHub-hosted runner executes
the sandbox validation and posts results back.

Best-effort by design: every failure is logged and swallowed, never raised
(mirrors the graceful-degradation pattern in reporter.py).
"""

import os

import requests

from core.config import config
from utils.logger import logger

API_BASE = "https://api.github.com"


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def ci_secret() -> str:
    """Shared secret used to authenticate runner <-> app calls."""
    return os.getenv(config.app.ci_runner.secret_env, "") or ""


def ci_base_url() -> str:
    """Public base URL the runner uses to fetch jobs and post results."""
    return (
        config.app.ci_runner.base_url
        or os.getenv("CI_VALIDATION_BASE_URL")
        or ""
    ).strip().rstrip("/")


def workflow_repo() -> str:
    """Repo that hosts the ai-risk-guard-validate workflow (owner/name)."""
    if config.app.ci_runner.workflow_repo:
        return config.app.ci_runner.workflow_repo
    return os.getenv("GITHUB_REPOSITORY", "") or ""


def ci_validation_configured() -> bool:
    """True when CI fallback can capture, dispatch and receive results."""
    return bool(
        config.app.ci_runner.enabled
        and workflow_repo()
        and ci_base_url()
        and ci_secret()
    )


def _dispatch_token(repo_full_name: str) -> str:
    """Token allowed to dispatch repository_dispatch to the workflow repo.

    Prefers CI_VALIDATION_TOKEN; otherwise falls back to the PR repo's
    installation token (works when the App is also installed on the workflow
    repo, which is the case when the workflow repo is the App's own repo).
    """
    explicit = os.getenv(config.app.ci_runner.token_env, "") or ""
    if explicit:
        return explicit
    try:
        from app.app import get_cached_token
        from utils.db import get_install_id_for_repo
        install_id = get_install_id_for_repo(repo_full_name)
        if install_id:
            return get_cached_token(install_id) or ""
    except Exception as e:
        logger.warning(f"CI dispatch token fallback failed: {e}", "CI_VALIDATION")
    return ""


def dispatch_validation_jobs(
    repo_full_name: str,
    pr_number: int,
    commit_sha: str,
    job_ids: list[int],
) -> bool:
    """Dispatch pending validation jobs to the workflow repo's runner.

    Returns True when the repository_dispatch call succeeded. Never raises.
    """
    if not ci_validation_configured():
        logger.info(
            "CI-runner validation not configured — skipping dispatch "
            "(enable ci_runner + set CI_VALIDATION_* env vars)",
            "CI_VALIDATION",
        )
        return False
    if not job_ids:
        return False

    token = _dispatch_token(repo_full_name)
    if not token:
        logger.warning(
            f"No token available to dispatch CI validation for {repo_full_name} — "
            "set CI_VALIDATION_TOKEN or install the App on the workflow repo",
            "CI_VALIDATION",
        )
        return False

    wf_repo = workflow_repo()
    url = f"{API_BASE}/repos/{wf_repo}/dispatches"
    payload = {
        "event_type": config.app.ci_runner.event_type,
        "client_payload": {
            "job_ids": job_ids,
            "repo": repo_full_name,
            "ref": commit_sha,
            "pr_number": pr_number,
            "base_url": ci_base_url(),
        },
    }
    try:
        response = requests.post(url, json=payload, headers=_headers(token), timeout=30)
        if response.status_code in (200, 201, 204):
            logger.info(
                f"Dispatched {len(job_ids)} CI validation job(s) for {repo_full_name} "
                f"PR #{pr_number} to {wf_repo}",
                "CI_VALIDATION",
            )
            return True
        logger.warning(
            f"CI dispatch returned {response.status_code}: {response.text[:300]}",
            "CI_VALIDATION",
        )
    except Exception as e:
        logger.error(f"CI dispatch failed for {repo_full_name}: {e}", "CI_VALIDATION")
    return False