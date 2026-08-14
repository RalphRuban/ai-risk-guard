"""
core/ci/validation.py

CI-runner fallback validation (Phase E).

When the App's own Docker daemon is unavailable, the sandbox execution and
regression-test stages fail closed. For scans whose PR metadata carries a repo
and commit, the affected candidates are:

  1. captured as pending jobs (idempotent — see the DB UNIQUE key),
  2. dispatched to a GitHub Actions runner via ``repository_dispatch``,
  3. and, when a completed result arrives, re-injected into a re-analysis pass
     so the PR comment/check pick up genuine runtime evidence.

The runner only supplies runtime evidence (sandbox + regression tests). All
static stages (syntax, re-scan, policy, SSRF validator) are still performed by
the App.
"""

import hashlib
import json
import os
from typing import Any

from core.config import config

_CODE_HASH_KEY = "patched_code_sha256"


def _ci_secret() -> str:
    return os.getenv(config.app.ci_runner.secret_env, "") or ""


def _ci_base_url() -> str:
    return (
        config.app.ci_runner.base_url
        or os.getenv("CI_VALIDATION_BASE_URL")
        or ""
    ).strip().rstrip("/")


def ci_validation_configured() -> bool:
    """True when CI fallback is enabled AND the runner can authenticate."""
    return bool(config.app.ci_runner.enabled and _ci_base_url() and _ci_secret())


def ci_validation_enabled(context: dict[str, Any]) -> bool:
    """True when CI fallback should capture/inject for this scan context."""
    if not ci_validation_configured():
        return False
    pr_context = context.get("pr_context") or {}
    return bool(pr_context.get("repo_name") and pr_context.get("commit_sha"))


def _code_sha(code: str) -> str:
    return hashlib.sha256((code or "").encode("utf-8")).hexdigest()


def record_pending_validation_job(
    context: dict[str, Any],
    candidate: dict[str, Any],
    source_filename: str | None,
    patched_code: str,
    test_file_path: str | None,
    extra_files: list | None,
    scan_mode: str | None,
    network: str | None,
) -> int:
    """Persist a candidate awaiting CI-runner validation (idempotent).

    Returns the job id, or 0 when the context has no repo/commit metadata or the
    DB write fails (best-effort by design — never raises into the scan).
    """
    pr_context = context.get("pr_context") or {}
    repo_full_name = pr_context.get("repo_name") or ""
    commit_sha = pr_context.get("commit_sha") or ""
    pr_number = int(pr_context.get("pr_number") or 0)
    if not (repo_full_name and commit_sha):
        return 0

    test_filename = ""
    test_content = ""
    if test_file_path and os.path.exists(test_file_path):
        try:
            with open(test_file_path, "r", encoding="utf-8", errors="ignore") as f:
                test_content = f.read()
            test_filename = os.path.basename(test_file_path)
        except OSError:
            pass

    try:
        from utils.db import record_pending_validation
        return record_pending_validation(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            commit_sha=commit_sha,
            source_filename=source_filename or "",
            candidate_id=candidate.get("id") or "",
            patched_code=patched_code or "",
            test_filename=test_filename,
            test_content=test_content,
            extra_files=extra_files or [],
            scan_mode=scan_mode or "",
            sandbox_network=network or "",
        )
    except Exception:
        return 0


def get_ci_validation_result(
    context: dict[str, Any],
    candidate: dict[str, Any],
    source_filename: str | None,
    patched_code: str,
) -> dict[str, Any] | None:
    """Return ``{sandbox, test_results}`` from a completed CI validation, or None.

    The stored patched-code hash is compared so stale results (from a code
    variant that no longer matches) are never re-injected.
    """
    pr_context = context.get("pr_context") or {}
    repo_full_name = pr_context.get("repo_name") or ""
    commit_sha = pr_context.get("commit_sha") or ""
    candidate_id = candidate.get("id") or ""
    if not (repo_full_name and commit_sha and candidate_id):
        return None
    try:
        from utils.db import get_ci_result
        row = get_ci_result(repo_full_name, commit_sha, source_filename or "", candidate_id)
    except Exception:
        return None
    if not row or not row.get("result_json"):
        return None
    try:
        result = json.loads(row["result_json"])
    except (ValueError, TypeError):
        return None
    if result.get(_CODE_HASH_KEY) != _code_sha(patched_code):
        return None
    sandbox_res = result.get("sandbox")
    if not isinstance(sandbox_res, dict):
        return None
    test_results = result.get("test_results")
    if not isinstance(test_results, dict):
        test_results = {
            "success": False,
            "skipped": True,
            "output": "",
            "error": "No CI test results",
        }
    return {"sandbox": sandbox_res, "test_results": test_results}


def build_result_json(sandbox_res: dict[str, Any], test_results: dict[str, Any], patched_code: str) -> str:
    """Serialize CI-runner results for storage (includes the code hash)."""
    return json.dumps({
        "sandbox": sandbox_res,
        "test_results": test_results,
        _CODE_HASH_KEY: _code_sha(patched_code),
        "validated_by": "ci_runner",
    }, ensure_ascii=False)