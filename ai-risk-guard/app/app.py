"""
app.py

AI Risk Guard
Phase 2 GitHub Webhook & Analytics Server
Professional Enterprise Edition
"""

import ast
import base64
import functools
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import requests
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.middleware.proxy_fix import ProxyFix

from app.main import AIRiskGuard
from core.cache.test_file_cache import TestFileCache
from core.config import config
from core.exceptions import InputValidationError
from core.patch.llm_patcher import is_rate_limited, reset_rate_limit_state
from core.scanner.diff_engine import (
    DiffAwareScanner,
)
from core.scanner.test_file_fetcher import (
    discover_and_fetch_test_file,
    fetch_test_dependencies,
)
from core.triage.llm_triage import LLMTriage
from core.utils.validation import safe_repo_path
from services.github.auth import (
    generate_jwt,
    get_installation_token,
)
from services.github.codeql_provisioner import create_codeql_pr
from services.github.reaction_sync import sync_reaction_feedback
from services.github.reporter import (
    check_all_alerts_dismissed,
    create_check_run,
    find_existing_bot_comment,
    post_pr_comment,
    update_pr_comment,
    upload_sarif_to_code_scanning,
)
from utils.db import (
    complete_pending_validation,
    count_ci_results_available,
    db_health,
    delete_repo_by_full_name,
    delete_repos_by_install,
    finding_belongs_to_user,
    get_all_findings,
    get_all_scans,
    get_dashboard,
    get_pending_scans_for_commit,
    get_pending_validation,
    get_pending_validation_scans,
    get_pending_validations_for_commit,
    get_pr_findings,
    get_repo,
    get_repo_findings,
    get_repo_scans,
    get_repos,
    get_scan,
    get_scan_findings,
    get_user,
    get_user_settings,
    has_inflight_ci_validation,
    increment_dashboard,
    init_db,
    is_repo_codeql_provisioned,
    mark_repo_codeql_provisioned,
    mark_scan_validated,
    mark_scan_validation_pending,
    record_feedback,
    record_finding,
    record_pr_finding,
    record_scan,
    resolve_open_findings_for_pr,
    sync_user_installations,
    update_finding_status,
    update_pending_validation_status,
    update_user_settings,
    upsert_repo,
    upsert_user,
)
from utils.logger import logger

# =========================================================
# INITIALIZATION
# =========================================================

# Load environment variables safely
load_dotenv(os.environ.get("PROJ_ENV", ".env"))

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    app.secret_key = secrets.token_hex(32)
    logger.warning(
        "FLASK_SECRET_KEY not set — generated a random key. "
        "All sessions will be invalidated on the next restart. "
        "Set FLASK_SECRET_KEY in your .env for production.",
        "AUTH",
    )
app.config["MAX_CONTENT_LENGTH"] = config.app.webhook.max_request_size_bytes

# Session cookie hardening. Secure defaults on; set SESSION_COOKIE_SECURE=false
# for plain-HTTP local development.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() in ("1", "true", "yes")

# Trust X-Forwarded-Proto / X-Forwarded-Host from the first hop. Constraint
# (accepted): the reverse proxy MUST be the only local client of this process,
# otherwise a client could spoof the forwarded headers. Nginx on 127.0.0.1 is
# the sole upstream, so trusting the first hop is safe here.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # type: ignore[method-assign]


def login_required(view):
    """Require an authenticated GitHub session for dashboard data endpoints."""
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user") and not session.get("github_id"):
            return jsonify({"error": "Unauthorized"}), 401
        return view(*args, **kwargs)
    return wrapped


def _current_github_id():
    """Return the authenticated user's github_id, or None."""
    user = session.get("user")
    if user:
        return user.get("github_id")
    return session.get("github_id")


# ---------------------------------------------------------------------------
# CSRF protection (double-submit cookie). SameSite=Strict is the primary
# defense; this header check is defense-in-depth for browsers that ignore it.
# ---------------------------------------------------------------------------
@app.before_request
def csrf_protect():
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        # The webhook is authenticated by the signed X-Hub-Signature-256 header,
        # not by the session cookie.
        if request.path.startswith("/webhook"):
            return None
        # CI-runner validation endpoints are machine-to-machine and
        # authenticated by the X-CI-Validation-Secret shared-secret header.
        if request.path.startswith("/api/ci-validation/"):
            return None
        header_token = request.headers.get("X-CSRF-Token", "")
        cookie_token = request.cookies.get("csrf_token", "")
        if not header_token or not cookie_token or not secrets.compare_digest(header_token, cookie_token):
            return jsonify({"error": "CSRF token missing or invalid"}), 403
    return None


@app.after_request
def add_csrf_cookie(response):
    if not request.cookies.get("csrf_token"):
        response.set_cookie(
            "csrf_token",
            secrets.token_urlsafe(32),
            max_age=7 * 24 * 3600,
            secure=app.config.get("SESSION_COOKIE_SECURE", True),
            samesite=app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
            httponly=False,
        )
    return response

# Initialize security engines
orchestrator = AIRiskGuard()
diff_engine = DiffAwareScanner()

# Path to React-built frontend
import os as _os

_static_dir = _os.path.join(_os.path.dirname(__file__), '..', 'static', 'frontend')


# =========================================================
# SECURITY HEADERS
# =========================================================

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # CORS headers are only needed when the frontend is served from a different origin
    # (e.g., the Vite dev server). In production the SPA is served from the same origin,
    # so the headers are omitted unless FRONTEND_ORIGIN is explicitly configured.
    if FRONTEND_ORIGIN:
        response.headers["Access-Control-Allow-Origin"] = FRONTEND_ORIGIN
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    origin = f" {FRONTEND_ORIGIN}" if FRONTEND_ORIGIN else ""
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'{origin}; "
        f"script-src 'self'{origin}; "
        f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        f"font-src https://fonts.gstatic.com; "
        f"img-src 'self' data: https://avatars.githubusercontent.com"
    )
    return response


# =========================================================
# FEEDBACK RATE LIMITER
# =========================================================

_feedback_rate: dict = {}
_feedback_lock = threading.Lock()


def _check_feedback_rate_limit(ip: str) -> bool:
    now = time.time()
    window = 60
    with _feedback_lock:
        _feedback_rate[ip] = [t for t in _feedback_rate.get(ip, []) if now - t < window]
        if len(_feedback_rate[ip]) >= 10:
            return True
        _feedback_rate[ip].append(now)
        return False


# =========================================================
# AUTH RATE LIMITER
# =========================================================

_auth_rate: dict = {}
_auth_lock = threading.Lock()


def _check_auth_rate_limit(ip: str) -> bool:
    now = time.time()
    window = 60
    with _auth_lock:
        _auth_rate[ip] = [t for t in _auth_rate.get(ip, []) if now - t < window]
        if len(_auth_rate[ip]) >= 6:
            return True
        _auth_rate[ip].append(now)
        return False


# =========================================================
# WEBHOOK DEDUPLICATION (TTL + bounded deque)
# =========================================================

_dedup_window = 300
_delivered_webhooks: deque = deque(maxlen=1000)
_dedup_lock = threading.Lock()


def _is_delivery_duplicate(delivery_id: str) -> bool:
    with _dedup_lock:
        now = time.time()
        while _delivered_webhooks and now - _delivered_webhooks[0][1] > _dedup_window:
            _delivered_webhooks.popleft()
        for did, _ in _delivered_webhooks:
            if did == delivery_id:
                return True
        _delivered_webhooks.append((delivery_id, now))
        return False

# =========================================================
# GLOBAL STATE & WORKERS
# =========================================================

# 1. Bounded Concurrency (Fix A)
executor = ThreadPoolExecutor(max_workers=config.app.webhook.max_concurrent_analyses)

# 2. Analysis capacity gate — limits the executor's internal queue so a webhook
#    flood cannot grow memory without bound. A permit is acquired on submit and
#    released once the worker starts (see _run_analysis_slot).
_analysis_slot = threading.BoundedSemaphore(config.app.webhook.max_concurrent_analyses)


def _run_analysis_slot(*args):
    """Release the capacity permit acquired at submit time, then run the analysis."""
    try:
        _analysis_slot.release()
    except ValueError:
        pass
    run_async_analysis(*args)


# 2b. GitHub API fetch with retry/backoff for transient network failures
_RETRIABLE_NETWORK_ERRORS = (
    requests.ConnectionError,
    requests.Timeout,
)


def _github_get_with_retry(url, headers, timeout=15, attempts=3, base_delay=1.0):
    """GET a GitHub API URL, retrying transient network errors and 5xx/429.

    Retries on connection resets (``RemoteDisconnected``), timeouts, HTTP 429
    (rate limit), and HTTP 5xx with exponential backoff. Non-retriable statuses
    are returned immediately. Returns the response object, or None when all
    attempts are exhausted.
    """
    for attempt in range(attempts):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
        except _RETRIABLE_NETWORK_ERRORS as e:
            logger.warning(
                f"Transient GitHub API error on attempt {attempt + 1}/{attempts}: {e}",
                "WEBHOOK",
            )
            if attempt < attempts - 1:
                time.sleep(base_delay * (2 ** attempt))
                continue
            return None
        if response.status_code in (429,) or response.status_code >= 500:
            logger.warning(
                f"Retriable GitHub API status {response.status_code} on attempt {attempt + 1}/{attempts}",
                "WEBHOOK",
            )
            if attempt < attempts - 1:
                time.sleep(base_delay * (2 ** attempt))
                continue
        return response
    return None


# 2. Token Cache (Fix C) — keyed by installation_id for multi-tenant isolation
token_cache: dict[str, dict] = {}
_token_lock = threading.Lock()

IGNORED_DIRS = set(config.app.webhook.ignored_dirs)

def is_ignored_path(file_path: str) -> bool:
    """Helper to check if file resides in an ignored vendor or virtual environment directory."""
    parts = file_path.replace("\\", "/").split("/")
    return any(part in IGNORED_DIRS for part in parts)

# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
GITHUB_APP_ID = os.environ.get("GITHUB_APP_ID", "")
GITHUB_PRIVATE_KEY = os.environ.get("GITHUB_PRIVATE_KEY", "")
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "").rstrip("/")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_APP_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_APP_CLIENT_SECRET", "")

# =========================================================
# STARTUP INITIALIZATION (WSGI-safe)
# =========================================================

_REQUIRED_ENV = {
    "GITHUB_WEBHOOK_SECRET": "webhook signature verification",
    "GITHUB_APP_ID": "GitHub App JWT authentication",
    "GITHUB_PRIVATE_KEY": "GitHub App JWT signing",
    "GITHUB_APP_CLIENT_ID": "GitHub OAuth login",
    "GITHUB_APP_CLIENT_SECRET": "GitHub OAuth token exchange",
}


def _production() -> bool:
    """Whether the app is running in production mode (APP_ENV=production)."""
    return os.environ.get("APP_ENV", "").strip().lower() == "production"


def _check_required_env():
    missing_required = [var for var in _REQUIRED_ENV if not os.environ.get(var)]
    for var in missing_required:
        logger.warning(f"Missing env var {var} — required for {_REQUIRED_ENV[var]}", "STARTUP")
    if not os.environ.get("FLASK_SECRET_KEY"):
        logger.warning(
            "Missing env var FLASK_SECRET_KEY — sessions will be invalidated on every restart",
            "STARTUP",
        )
    for var, note in (
        ("GEMINI_API_KEY", "LLM patch generation will fail"),
        ("GITHUB_APP_SLUG", "the install-app banner link will be hidden"),
    ):
        if not os.environ.get(var):
            logger.warning(f"Missing env var {var} — {note}", "STARTUP")

    if not _production():
        return
    missing = list(missing_required)
    if not os.environ.get("FLASK_SECRET_KEY"):
        missing.append("FLASK_SECRET_KEY")
    if missing:
        raise RuntimeError(
            "Startup aborted: APP_ENV=production requires the following environment "
            f"variables to be set: {', '.join(missing)}. "
            "Configure them and restart the service."
        )


init_db()
try:
    from app.metrics import init_app_info
    init_app_info()
except Exception as e:
    logger.warning(f"Failed to initialize app metrics: {e}", "STARTUP")
_check_required_env()


def _reaction_poller_loop():
    """Daemon loop: harvest 🚀/👎 reactions on bot PR comments on an interval.

    Polls the Reactions REST API because GitHub Apps have no ``reaction``
    webhook event. The install-token cache is shared with webhook analysis.
    """
    interval = config.app.feedback.poll_interval_seconds
    while True:
        time.sleep(interval)
        try:
            sync_reaction_feedback(get_cached_token)
        except Exception as e:
            logger.error(f"Reaction poll cycle failed: {e}", "FEEDBACK")


if config.app.feedback.enabled:
    threading.Thread(target=_reaction_poller_loop, daemon=True, name="reaction-poller").start()
    logger.info(
        f"Reaction feedback poller started (every {config.app.feedback.poll_interval_seconds}s)",
        "STARTUP",
    )


def _docker_validation_available() -> bool:
    """Lightweight (non-provisioning) Docker + sandbox image availability check."""
    try:
        from core.validator.sandbox import Sandbox
        sandbox = Sandbox()
        return sandbox._is_docker_available() and sandbox.docker_image_available()
    except Exception:
        return False


# Scans currently being re-validated (dedup across worker cycles).
_revalidation_inflight: set[int] = set()


def _revalidate_pending_scan(pending: dict):
    """Re-submit a pending scan for full re-analysis (updates comment/check).

    Runs the analysis on the executor (respecting the analysis capacity slot)
    and marks the scan validated only after the re-run completes.
    """
    scan_id = pending.get("id")
    if not scan_id or scan_id in _revalidation_inflight:
        return
    repo_id = pending.get("repo_id")
    pr_number = pending.get("pr_number")
    repo_name = pending.get("repo_full_name")
    install_id = pending.get("install_id")
    pr_title = pending.get("pr_title") or ""
    branch = pending.get("branch") or ""
    commit_sha = pending.get("commit_sha") or ""
    if not (repo_id and pr_number and repo_name and install_id):
        logger.warning(f"Skipping re-validation for scan {scan_id}: missing repo/pr/install info", "VALIDATION")
        return

    def _job():
        try:
            run_async_analysis(repo_name, repo_id, pr_number, pr_title, install_id, branch, commit_sha)
            mark_scan_validated(scan_id)
            logger.info(f"Re-validation completed for PR #{pr_number} in {repo_name} (scan {scan_id})", "VALIDATION")
        except Exception as e:
            logger.error(f"Re-validation failed for scan {scan_id}: {e}", "VALIDATION")
        finally:
            _analysis_slot.release()
            _revalidation_inflight.discard(scan_id)

    if not _analysis_slot.acquire(blocking=False):
        logger.warning(f"Re-validation skipped — analysis capacity reached (scan {scan_id})", "VALIDATION")
        return
    _revalidation_inflight.add(scan_id)
    try:
        executor.submit(_job)
    except Exception:
        _analysis_slot.release()
        _revalidation_inflight.discard(scan_id)
        raise


def _validation_worker_loop():
    """Periodically re-validate scans that failed closed because Docker was down.

    Once Docker + the sandbox image are available again, each pending scan is
    re-run end-to-end so the existing PR comment/check pick up runtime evidence.
    """
    interval = config.app.validation.poll_interval_seconds
    while True:
        time.sleep(interval)
        try:
            if not config.app.validation.enabled:
                continue
            if not _docker_validation_available():
                continue
            pending = get_pending_validation_scans(config.app.validation.max_revalidations_per_cycle)
            for scan in pending:
                # If CI-runner validation jobs are queued/in flight for this
                # commit, wait for their results instead of re-running here
                # (the local Docker is still down; the CI results substitute).
                if has_inflight_ci_validation(scan["repo_full_name"], scan["commit_sha"]):
                    continue
                _revalidate_pending_scan(scan)
        except Exception as e:
            logger.error(f"Validation poll cycle failed: {e}", "VALIDATION")


if config.app.validation.enabled:
    threading.Thread(target=_validation_worker_loop, daemon=True, name="validation-poller").start()
    logger.info(
        f"Deferred re-validation worker started (every {config.app.validation.poll_interval_seconds}s)",
        "STARTUP",
    )


def dispatch_pending_ci_validation(repo_full_name: str, pr_number: int, commit_sha: str):
    """Dispatch captured candidates to the CI runner (best-effort).

    Called once per scan completion. Jobs captured for this commit while the
    sandbox failed closed are sent to the workflow repo via
    ``repository_dispatch`` and marked ``dispatched``. Never raises.
    """
    if not commit_sha:
        return
    try:
        from services.github.ci_dispatch import (
            ci_validation_configured,
            dispatch_validation_jobs,
        )
        if not ci_validation_configured():
            return
        jobs = get_pending_validations_for_commit(
            repo_full_name, commit_sha, statuses=["pending"]
        )
        if not jobs:
            return
        job_ids = [j["id"] for j in jobs]
        if dispatch_validation_jobs(repo_full_name, pr_number, commit_sha, job_ids):
            for job_id in job_ids:
                update_pending_validation_status(job_id, "dispatched")
    except Exception as e:
        logger.error(f"CI validation dispatch failed: {e}", "WEBHOOK")

# =========================================================
# HELPERS
# =========================================================

def verify_signature(payload, signature):
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET not set — rejecting request", "AUTH")
        return False
    expected_signature = (
        "sha256=" +
        hmac.new(
            GITHUB_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
    )
    return hmac.compare_digest(expected_signature, signature)


# =========================================================
# TEST / SOURCE IMPORT COMPATIBILITY DIAGNOSTIC
# =========================================================

_KNOWN_TEST_IMPORTS = frozenset({
    "pytest", "hypothesis", "requests", "flask", "sqlalchemy",
    "bcrypt", "cryptography", "pydantic", "urllib3", "certifi",
    "jinja2", "markupsafe", "werkzeug", "six", "dotenv", "mock",
})


def _test_import_roots(test_content: str) -> set:
    """Return the top-level import roots found in a test file."""
    try:
        tree = ast.parse(test_content)
    except (SyntaxError, TypeError):
        return set()
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _log_test_import_mismatch(test_content: str, source_filename: str, repo_root: str | None = None) -> None:
    """Warn when a fetched test file imports modules that cannot resolve
    against the scanned source file (e.g. imports from a ``tests`` package
    that does not exist in the PR).

    Only flags imports that are not standard library, not a known third-party
    package, not the module under test, and not a repo-local package staged
    alongside the scanned source.
    """
    stdlib: frozenset[str] = getattr(sys, "stdlib_module_names", frozenset())
    roots = _test_import_roots(test_content)
    if not roots:
        return
    source_stem = os.path.splitext(os.path.basename(source_filename))[0].lower()
    unresolved = sorted(
        root for root in roots
        if root.lower() != source_stem
        and root not in stdlib
        and root not in _KNOWN_TEST_IMPORTS
        and not _root_is_repo_local(root, source_filename, repo_root)
    )
    if unresolved:
        logger.warning(
            f"Test file imports {', '.join(unresolved)} which cannot be resolved against "
            f"scanned source {source_filename} — regression tests may fail to run",
            "WEBHOOK",
        )


def _root_is_repo_local(root: str, source_filename: str, repo_root: str | None) -> bool:
    """Return True when ``root`` resolves to a package/module stored in the
    scanned repo mirror rather than an external import.

    Mirrors the dependency fetcher's notion of a module-under-test / sibling
    package so we don't emit a false-positive warning for imports the runtime
    rebinding is expected to handle.
    """
    from core.scanner.test_file_fetcher import _module_file_candidates

    source_dir = os.path.dirname(source_filename) if repo_root is None else os.path.join(
        repo_root, os.path.dirname(source_filename) or "."
    )
    search_root = source_dir or "."
    for module in (f"{root}.__init__", root):
        for rel_path in _module_file_candidates(module):
            if os.path.exists(os.path.join(search_root, rel_path)):
                return True
    return False


def get_cached_token(installation_id):
    """Retrieve or refresh the installation token with caching (Fix C)."""
    with _token_lock:
        now = datetime.now(UTC)
        entry = token_cache.get(installation_id)
        if entry and entry["token"]:
            expiry = entry["expiry"]
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=UTC)
            if expiry > now:
                return entry["token"]

        logger.info("Refreshing GitHub installation token", "AUTH")
        jwt_token = generate_jwt(GITHUB_APP_ID, GITHUB_PRIVATE_KEY)
        new_token = get_installation_token(jwt_token, installation_id)

        token_cache[installation_id] = {
            "token": new_token,
            "expiry": now + timedelta(minutes=55),
        }
        return new_token

# =========================================================
# BACKGROUND WORKER
# =========================================================

def run_async_analysis(repo_name, repo_id, pr_number, pr_title, installation_id, branch_name, commit_sha=None):
    """
    Zero-Cost Lightweight Ingestion Engine (Phase 2).
    Fetches modified PR files directly in memory via GitHub API without disk git clone.
    """
    import time
    scan_start = time.time()
    access_token = None
    reset_rate_limit_state()

    try:
        from app.metrics import (
            active_analyses,
            scan_total,
            vulnerabilities_active,
            vulnerabilities_total,
        )
        active_analyses.inc()
    except ImportError:
        active_analyses = scan_total = vulnerabilities_total = vulnerabilities_active = None

    try:
        access_token = get_cached_token(installation_id)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json"
        }

        # 1. Fetch list of modified files in PR via GitHub API (paginated)
        pr_files = []
        page = 1
        max_pages = 10  # safety limit (1000 files)
        while page <= max_pages:
            files_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}/files?per_page=100&page={page}"
            response = _github_get_with_retry(files_url, headers)

            if response is None:
                logger.error("Failed to fetch PR files after retries", "WEBHOOK")
                if scan_total:
                    scan_total.labels(status="failure").inc()
                return

            if response.status_code != 200:
                logger.error(f"Failed to fetch PR files: {response.text}", "WEBHOOK")
                if scan_total:
                    scan_total.labels(status="failure").inc()
                return

            page_files = response.json()
            if not page_files:
                break
            pr_files.extend(page_files)
            page += 1

        logger.info(f"Retrieved {len(pr_files)} modified files from GitHub PR API", "WEBHOOK")

        findings = []
        findings_lock = threading.Lock()
        timeout = getattr(config.app.webhook, "analysis_timeout_seconds", 300)

        def _is_test_file(path: str) -> bool:
            normalized = path.lower()
            basename = normalized.rsplit("/", 1)[-1]
            return (
                basename.startswith("test_")
                or basename.endswith("_test.py")
                or "/tests/" in normalized
                or "\\tests\\" in normalized
            )

        def _scan_single_file(file_info):
            filename = file_info.get("filename", "")
            status = file_info.get("status", "")
            patch_diff = file_info.get("patch", "")

            if time.time() - scan_start > timeout:
                return

            if not filename.endswith(".py") or status == "removed" or is_ignored_path(filename):
                return

            if _is_test_file(filename):
                logger.info(f"Skipping test file: {filename}", "WEBHOOK")
                return

            logger.info(f"Scanning modified file: {filename}", "WEBHOOK")

            contents_url = f"https://api.github.com/repos/{repo_name}/contents/{filename}?ref={branch_name}"
            content_res = requests.get(contents_url, headers=headers, timeout=15)
            if content_res.status_code != 200:
                logger.warning(f"Could not fetch content for {filename}: {content_res.text}", "WEBHOOK")
                return

            file_data = content_res.json()
            raw_content = base64.b64decode(file_data.get("content", "")).decode("utf-8", errors="ignore")

            try:
                temp_file_path = safe_repo_path(temp_dir, filename)
            except InputValidationError as e:
                logger.warning(f"Skipping file with unsafe path '{filename}': {e}", "WEBHOOK")
                return
            os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
            with open(temp_file_path, "w", encoding="utf-8") as f:
                f.write(raw_content)

            if not _is_test_file(filename):
                test_cache = TestFileCache()
                test_content, test_path = discover_and_fetch_test_file(
                    repo_name=repo_name,
                    branch=branch_name,
                    source_file=filename,
                    access_token=access_token,
                    cache=test_cache,
                    commit_sha=commit_sha or "",
                )
                if test_content and test_path:
                    try:
                        test_temp_path = safe_repo_path(temp_dir, test_path)
                    except InputValidationError as e:
                        logger.warning(f"Skipping test file with unsafe path '{test_path}': {e}", "WEBHOOK")
                        test_content = None
                        test_path = None
                if test_content and test_path:
                    os.makedirs(os.path.dirname(test_temp_path), exist_ok=True)
                    logger.info(f"Saved test file: {test_temp_path}", "WEBHOOK")
                    with open(test_temp_path, "w", encoding="utf-8") as tf:
                        tf.write(test_content)
                    _log_test_import_mismatch(test_content, filename, repo_root=temp_dir)
                    test_deps = fetch_test_dependencies(
                        repo_name=repo_name,
                        branch=branch_name,
                        source_file=filename,
                        test_content=test_content,
                        access_token=access_token,
                        cache=test_cache,
                        known_packages=_KNOWN_TEST_IMPORTS,
                        commit_sha=commit_sha or "",
                    )
                    for dep in test_deps:
                        try:
                            dep_path = safe_repo_path(temp_dir, dep["path"])
                        except InputValidationError as e:
                            logger.warning(f"Skipping test dependency with unsafe path '{dep['path']}': {e}", "WEBHOOK")
                            continue
                        os.makedirs(os.path.dirname(dep_path), exist_ok=True)
                        with open(dep_path, "w", encoding="utf-8") as df:
                            df.write(dep["content"])
                    if test_deps:
                        logger.info(f"Staged {len(test_deps)} test dependency files", "WEBHOOK")
                        file_context = dict(pr_context, test_file_path=test_temp_path, test_deps=test_deps)
                    else:
                        file_context = dict(pr_context, test_file_path=test_temp_path)
                else:
                    file_context = pr_context

            result = orchestrator.analyze_file(
                file_path=temp_file_path,
                repo_root=temp_dir,
                pr_context=file_context,
                diff_data=patch_diff
            )

            for r in result:
                if "vulnerability" in r:
                    r["vulnerability"]["file"] = filename
                    r["vulnerability"]["file_rel"] = filename

            with findings_lock:
                findings.extend(result)

        pr_context = {
            "repo_name": repo_name,
            "pr_number": pr_number,
            "access_token": access_token,
            "commit_sha": commit_sha,
        }

        # Resolve the owning user's scan settings once per scan (repo is
        # already upserted by the webhook handler, so user_id is available).
        # Unattributed repos fall back to system defaults.
        try:
            repo_row = get_repo(repo_id)
            owner_uid = repo_row.get("user_id") if repo_row else None
            scan_settings = get_user_settings(owner_uid)
        except Exception as e:
            logger.warning(f"Could not resolve scan settings for repo {repo_id}: {e}", "WEBHOOK")
            scan_settings = get_user_settings()
        pr_context["scan_settings"] = scan_settings

        with tempfile.TemporaryDirectory() as temp_dir:
            file_workers = min(len(pr_files), 3)
            with ThreadPoolExecutor(max_workers=file_workers) as pool:
                futures = [pool.submit(_scan_single_file, fi) for fi in pr_files]
                for future in as_completed(futures):
                    try:
                        exc = future.exception()
                        if exc:
                            logger.error(f"File scan failed: {exc}", "WEBHOOK")
                    except Exception as e:
                        logger.error(f"Unexpected file scan error: {e}", "WEBHOOK")

        if findings:
            elapsed = time.time() - scan_start
            orch_context = orchestrator.run_orchestrator(results=findings, pr_context=pr_context)
            orch_context["scan_duration"] = elapsed
            executive_decision = orch_context.get("executive_decision", "COMMENT")

            def _post_comment():
                llm_summary = None
                if getattr(config.app.summary, "enabled", True) and findings:
                    try:
                        llm_summary = LLMTriage().summarize_analysis(findings)
                    except Exception as e:
                        logger.warning(f"LLM summary generation failed: {e}", "WEBHOOK")
                post_pr_comment(
                    repository=repo_name,
                    pr_number=pr_number,
                    results=findings,
                    access_token=access_token,
                    rate_limited=is_rate_limited(),
                    action=executive_decision,
                    scan_start=scan_start,
                    commit_sha=commit_sha,
                    scan_mode=(scan_settings or {}).get("scan_mode"),
                    llm_summary=llm_summary,
                )

            def _upload_sarif():
                sarif_output = orch_context.get("sarif_output")
                sarif_commit_sha = orch_context.get("sarif_commit_sha")
                if sarif_output and sarif_commit_sha:
                    if getattr(config.app.sarif, "skip_if_all_dismissed", False):
                        try:
                            if check_all_alerts_dismissed(repo_name, access_token, sarif_output, pr_number):
                                return
                        except Exception as e:
                            logger.warning(f"Dismissed-alert check failed: {e}, proceeding with upload", "WEBHOOK")
                    upload_sarif_to_code_scanning(
                        repo_name, pr_number, access_token, sarif_output, sarif_commit_sha
                    )

            def _create_check():
                if not getattr(config.app.checks, "create_check", True):
                    return
                if not commit_sha:
                    logger.warning("No commit SHA available — skipping Check Run", "WEBHOOK")
                    return
                create_check_run(
                    repo_name, pr_number, access_token, findings, commit_sha
                )

            with ThreadPoolExecutor(max_workers=3) as parallel_pool:
                comment_future = parallel_pool.submit(_post_comment)
                sarif_future = parallel_pool.submit(_upload_sarif)
                check_future = parallel_pool.submit(_create_check)
                for f in (comment_future, sarif_future, check_future):
                    try:
                        f.result()
                    except Exception as e:
                        logger.error(f"Post-PR task failed: {e}", "WEBHOOK")
            
            # Metrics update
            max_severity = "LOW"
            for f in findings:
                sev = f["vulnerability"].get("severity", "LOW")
                vuln_type = f["vulnerability"].get("type")
                
                # Record finding for merge tracking (Phase 3)
                record_pr_finding(pr_number, vuln_type)

                # Record Prometheus vulnerability metrics
                if vulnerabilities_total:
                    vulnerabilities_total.labels(type=vuln_type or "UNKNOWN", severity=sev).inc()
                if vulnerabilities_active:
                    vulnerabilities_active.labels(severity=sev).inc()

                if sev == "HIGH": max_severity = "HIGH"
                if sev == "MEDIUM" and max_severity != "HIGH": max_severity = "MEDIUM"
            
            increment_dashboard(total_vulns=len(findings), risk_level=max_severity)
            logger.info("PR report posted and dashboard updated", "WEBHOOK")

            # Persist scan and findings
            action_risks = [f.get("risk", 0) for f in findings if not f.get("is_silent")]
            scan_id = record_scan(
                repo_id=repo_id, pr_number=pr_number, pr_title=pr_title,
                branch=branch_name, commit_sha=commit_sha or "",
                findings_count=len(findings),
                max_risk=max(action_risks, default=0),
                duration_ms=int((time.time() - scan_start) * 1000),
            )
            # Deferred re-validation: if Docker was unavailable during this scan
            # the sandbox stages failed closed, so queue the scan for a re-run
            # once Docker is available again — unless CI-runner validation has
            # already supplied runtime evidence for this commit.
            if not _docker_validation_available():
                if count_ci_results_available(repo_name, commit_sha or "") > 0:
                    mark_scan_validated(scan_id)
                else:
                    mark_scan_validation_pending(scan_id)
            for f in findings:
                v = f.get("vulnerability", {})
                record_finding(
                    scan_id=scan_id,
                    vuln_type=v.get("type", "UNKNOWN"),
                    severity=v.get("severity", "MEDIUM"),
                    risk_score=f.get("risk", 0),
                    file_path=v.get("file", ""),
line_number=v.get("line", 0),
                    is_new=1 if v.get("is_new") else 0,
                )
        else:
            logger.info("No vulnerabilities found — SARIF upload skipped", "WEBHOOK")
            scan_id = record_scan(
                repo_id=repo_id, pr_number=pr_number, pr_title=pr_title,
                branch=branch_name, commit_sha=commit_sha or "",
                findings_count=0, max_risk=0,
                duration_ms=int((time.time() - scan_start) * 1000),
            )
            if not _docker_validation_available():
                if count_ci_results_available(repo_name, commit_sha or "") > 0:
                    mark_scan_validated(scan_id)
                else:
                    mark_scan_validation_pending(scan_id)

        # CI-runner fallback (Phase E): dispatch any candidates captured while
        # the sandbox failed closed to the GitHub-hosted validation runner.
        dispatch_pending_ci_validation(repo_name, pr_number, commit_sha or "")

        # Record scan success and duration
        if scan_total:
            scan_total.labels(status="success").inc()
        import app.metrics as _m
        if _m.scan_duration:
            _m.scan_duration.observe(time.time() - scan_start)

    except Exception as e:
        logger.error(f"Background analysis failed: {e}", "WEBHOOK")
        try:
            if scan_total:
                scan_total.labels(status="failure").inc()
            import app.metrics as _m
            if _m.scan_duration:
                _m.scan_duration.observe(time.time() - scan_start)
        except Exception:
            pass

        # Post error comment and failed check run on PR
        try:
            if not access_token:
                access_token = get_cached_token(installation_id)
            if not access_token:
                return

            prev_scan_number = 0
            existing = None
            if getattr(config.app.sarif, "comment_on_pr", True):
                if getattr(config.app.sarif, "update_existing_comment", True):
                    existing = find_existing_bot_comment(repo_name, pr_number, access_token)
                if existing is not None:
                    prev_scan_number = existing[1]

            error_body = (
                "# 🔐 AI Risk Guard — Analysis Failed\n\n"
                f"> **Error**: Analysis failed — see logs for details\n"
                f"> **PR**: #{pr_number}\n\n"
                "The scan could not complete. Common causes:\n"
                "- Analysis exceeded timeout (configurable via `analysis_timeout_seconds`)\n"
                "- GitHub API rate limit exceeded\n"
                "- Gemini API unavailable\n\n"
                "Please push a new commit to re-trigger analysis.\n"
                f"<!-- ai-risk-guard scan:{prev_scan_number} -->\n"
            )

            if existing is not None:
                comment_id = existing[0]
                update_pr_comment(repo_name, comment_id, access_token, error_body)
            else:
                comment_url = (
                    f"https://api.github.com/repos/"
                    f"{repo_name}/issues/{pr_number}/comments"
                )
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                }
                requests.post(comment_url, json={"body": error_body}, headers=headers, timeout=15)

        except Exception as inner:
            logger.error(f"Error reporting failed: {inner}", "WEBHOOK")

    finally:
        try:
            if active_analyses:
                active_analyses.dec()
        except Exception:
            pass

# =========================================================
# ROUTES
# =========================================================

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "AI Risk Guard Active",
        "endpoints": {
            "/webhook": "POST - GitHub Webhook Receiver",
            "/api/feedback": "POST - Record patch feedback (ACCEPTED/REJECTED)",
            "/feedback": "POST - Legacy alias for patch feedback",
            "/dashboard": "GET - Visual Analytics Dashboard",
            "/api/metrics": "GET - JSON Metrics for Dashboard",
            "/api/policy": "GET - Current Security Policy",
            "/auth/login": "GET - GitHub OAuth Login",
            "/auth/logout": "GET - Logout",
            "/api/me": "GET - Current user info"
        }
})


@app.route("/api/health/ready", methods=["GET"])
def health_ready():
    """Readiness probe for platform health checks (Nginx, uptime monitors).

    Unauthenticated. Returns 200 only when the SQLite database is writable;
    503 otherwise. Sandbox/GitHub availability is reported for observability
    but does not gate readiness — the app fails closed (or uses the CI-runner
    fallback) when the sandbox is unavailable.
    """
    from core.validator.sandbox import Sandbox
    db_ok = db_health()
    sandbox = Sandbox()
    docker_available = sandbox._is_docker_available()
    payload = {
        "status": "ready" if db_ok else "not_ready",
        "db_writable": db_ok,
        "sandbox_available": docker_available and sandbox.docker_image_available(),
        "github_configured": bool(
            GITHUB_WEBHOOK_SECRET and GITHUB_APP_ID and GITHUB_PRIVATE_KEY
        ),
    }
    return jsonify(payload), 200 if db_ok else 503


@app.route("/auth/login", methods=["GET"])
def auth_login():
    if not GITHUB_CLIENT_ID:
        return jsonify({"error": "GitHub OAuth not configured"}), 503

    ip = request.remote_addr or "unknown"
    if _check_auth_rate_limit(ip):
        logger.warning(f"Auth rate limit exceeded for {ip}", "AUTH")
        return jsonify({"error": "Too many requests"}), 429

    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    logger.info(f"OAuth callback URL: {url_for('auth_callback', _external=True)}", "AUTH")
    redirect_uri = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&state={state}"
        f"&scope=read:user"
    )
    return redirect(redirect_uri)


@app.route("/auth/callback", methods=["GET"])
def auth_callback():
    state = request.args.get("state")
    expected_state = session.pop("oauth_state", None)
    if not state or not expected_state or not secrets.compare_digest(state, expected_state):
        return redirect("/?error=login_failed&reason=state_mismatch")

    code = request.args.get("code")
    if not code:
        return redirect("/?error=login_failed&reason=missing_code")

    try:
        token_resp = requests.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
    except requests.RequestException:
        logger.exception("Token exchange request failed")
        return redirect("/?error=login_failed&reason=token_exchange")

    if token_resp.status_code != 200:
        return redirect("/?error=login_failed&reason=token_exchange_status")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return redirect("/?error=login_failed&reason=no_token")

    try:
        user_resp = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=10,
        )
    except requests.RequestException:
        logger.exception("User fetch request failed")
        return redirect("/?error=login_failed&reason=user_fetch")

    if user_resp.status_code != 200:
        return redirect("/?error=login_failed&reason=user_fetch_status")

    user_data = user_resp.json()
    github_id = user_data.get("id")
    if not github_id:
        return redirect("/?error=login_failed&reason=no_github_id")

    login = user_data.get("login", "")
    name = user_data.get("name") or login
    avatar_url = user_data.get("avatar_url", "")

    upsert_user(github_id, login, name, avatar_url)

    # If the GitHub App is not installed on any repository, don't create a
    # session. Return to the login page with a graceful notice instead of
    # sending the user to an empty dashboard.
    installations = _get_installation_count(github_id, access_token)
    if installations == 0:
        redirect_target = "/login?error=no_installations"
        install_url = _github_app_install_url()
        if install_url:
            redirect_target += f"&install_url={quote(install_url, safe='')}"
        return redirect(redirect_target)

    session["user"] = {
        "github_id": github_id,
        "login": login,
        "name": name,
        "avatar_url": avatar_url,
    }
    session["github_id"] = github_id
    session["github_access_token"] = _encrypt_token(access_token)
    if token_data.get("expires_in"):
        session["github_token_expires_at"] = time.time() + token_data["expires_in"]
    if token_data.get("refresh_token"):
        session["github_refresh_token"] = _encrypt_token(token_data["refresh_token"])

    # Record which installations this user can access and their repos so the
    # dashboard and scan attribution are per-user from the first request.
    _sync_repos_from_github(github_id, access_token)

    return redirect("/dashboard")


@app.route("/auth/logout", methods=["GET"])
def auth_logout():
    session.pop("user", None)
    session.pop("github_id", None)
    _clear_session_token()
    return redirect("/")


@app.route("/api/me", methods=["GET"])
def api_me():
    user = session.get("user")
    if user:
        token = _get_valid_access_token()
        return jsonify({
            "authenticated": True,
            "user": user,
            "installations": _get_installation_count(user.get("github_id"), token),
            "install_url": _github_app_install_url(),
        })

    github_id = session.get("github_id")
    if github_id:
        db_user = get_user(github_id)
        if db_user:
            session["user"] = {
                "github_id": db_user["github_id"],
                "login": db_user["login"],
                "name": db_user["name"],
                "avatar_url": db_user["avatar_url"],
            }
            token = _get_valid_access_token()
            return jsonify({
                "authenticated": True,
                "user": session["user"],
                "installations": _get_installation_count(db_user["github_id"], token),
                "install_url": _github_app_install_url(),
            })

    return jsonify({"authenticated": False, "user": None, "installations": -1, "install_url": ""})


@app.route("/api/repos", methods=["GET"])
@login_required
def api_repos():
    repos = get_repos(_current_github_id())
    return jsonify({"repos": repos})


@app.route("/api/repos/<int:repo_id>", methods=["GET"])
@login_required
def api_repo(repo_id):
    repo = get_repo(repo_id, _current_github_id())
    if not repo:
        return jsonify({"error": "Repo not found"}), 404
    return jsonify(repo)


@app.route("/api/repos/<int:repo_id>/scans", methods=["GET"])
@login_required
def api_repo_scans(repo_id):
    scans = get_repo_scans(repo_id, _current_github_id())
    return jsonify({"scans": scans})


@app.route("/api/scans/<int:scan_id>", methods=["GET"])
@login_required
def api_scan(scan_id):
    """Return a single scan record."""
    scan = get_scan(scan_id, _current_github_id())
    if not scan:
        return jsonify({"error": "Scan not found"}), 404
    return jsonify({"scan": scan})


@app.route("/api/scans/<int:scan_id>/revalidate", methods=["POST"])
@login_required
def api_scan_revalidate(scan_id):
    """Queue a scan for re-validation (e.g. it failed closed because Docker was down).

    Marks the scan pending so the background worker re-runs it once Docker is
    available, then kicks an immediate pass of the worker logic.
    """
    if not config.app.validation.enabled:
        return jsonify({"error": "Deferred re-validation is disabled"}), 400
    scan = get_scan(scan_id, _current_github_id())
    if not scan:
        return jsonify({"error": "Scan not found"}), 404
    mark_scan_validation_pending(scan_id)
    try:
        _revalidate_pending_scan(scan)
    except Exception as e:
        logger.error(f"Revalidate endpoint failed for scan {scan_id}: {e}", "VALIDATION")
    return jsonify({"status": "queued", "message": "Scan queued for re-validation"}), 202


def _ci_validation_auth_ok() -> bool:
    """Validate the shared secret header on CI-runner endpoints."""
    from services.github.ci_dispatch import ci_secret
    secret = ci_secret()
    if not secret:
        return False
    provided = request.headers.get("X-CI-Validation-Secret") or ""
    return hmac.compare_digest(provided, secret)


@app.route("/api/ci-validation/jobs/<int:job_id>", methods=["GET"])
def ci_validation_job(job_id):
    """Serve a pending-validation job payload to the GitHub-hosted runner.

    Auth: ``X-CI-Validation-Secret`` header (shared secret, machine-to-machine).
    """
    if not _ci_validation_auth_ok():
        return jsonify({"error": "unauthorized"}), 401
    row = get_pending_validation(job_id)
    if not row:
        return jsonify({"error": "unknown job"}), 404
    try:
        extra_files = json.loads(row.get("extra_files") or "[]")
    except (ValueError, TypeError):
        extra_files = []
    return jsonify({
        "job_id": row["id"],
        "repo_full_name": row["repo_full_name"],
        "pr_number": row["pr_number"],
        "commit_sha": row["commit_sha"],
        "source_filename": row["source_filename"],
        "candidate_id": row["candidate_id"],
        "patched_code": row["patched_code"],
        "test_filename": row["test_filename"],
        "test_content": row["test_content"],
        "extra_files": extra_files,
        "scan_mode": row["scan_mode"],
        "sandbox_network": row["sandbox_network"],
        "status": row["status"],
    })


@app.route("/api/ci-validation/results", methods=["POST"])
def ci_validation_results():
    """Receive CI-runner validation results and re-validate affected scans.

    Body: ``{job_id, status?, sandbox_res?, test_results?}``. A completed
    result triggers a re-analysis of any pending scan for the same commit so
    the PR comment/check pick up the runtime evidence even while Docker is down.
    """
    if not _ci_validation_auth_ok():
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id required"}), 400
    row = get_pending_validation(int(job_id))
    if not row:
        return jsonify({"error": "unknown job"}), 404
    status = data.get("status") or "completed"
    try:
        from core.ci.validation import build_result_json
        result_json = build_result_json(
            data.get("sandbox_res") or {},
            data.get("test_results") or {},
            row.get("patched_code") or "",
        )
    except Exception as e:
        logger.error(f"CI results serialization failed for job {job_id}: {e}", "CI_VALIDATION")
        result_json = ""
    complete_pending_validation(int(job_id), result_json, status=status)
    logger.info(
        f"CI validation result received for job {job_id} ({status}) in "
        f"{row['repo_full_name']}@{row['commit_sha']}",
        "CI_VALIDATION",
    )
    if status == "completed":
        pending_scans = get_pending_scans_for_commit(row["repo_full_name"], row["commit_sha"])
        for scan in pending_scans:
            try:
                _revalidate_pending_scan(scan)
            except Exception as e:
                logger.error(
                    f"CI-triggered re-validation failed for scan {scan.get('id')}: {e}",
                    "CI_VALIDATION",
                )
    return jsonify({"ok": True})


@app.route("/api/scans/<int:scan_id>/findings", methods=["GET"])
@login_required
def api_scan_findings(scan_id):
    """Return findings for a single scan record."""
    uid = _current_github_id()
    # Ensure scan exists and is visible to this user before fetching findings
    if not get_scan(scan_id, uid):
        return jsonify({"error": "Scan not found"}), 404
    findings = get_scan_findings(scan_id, uid)
    return jsonify({"findings": findings})


@app.route("/api/repos/<int:repo_id>/findings", methods=["GET"])
@login_required
def api_repo_findings(repo_id):
    findings = get_repo_findings(repo_id, _current_github_id())
    return jsonify({"findings": findings})


@app.route("/api/findings", methods=["GET"])
@login_required
def api_all_findings():
    """Findings across all of the user's repos, optionally filtered."""
    uid = _current_github_id()
    if uid is None:
        return jsonify({"error": "Unauthorized"}), 401
    args = request.args
    try:
        repo_id = int(args.get("repo_id")) if args.get("repo_id") else None
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid repo_id"}), 400
    status = args.get("status") or None
    if status and status not in {"open", "resolved", "dismissed"}:
        return jsonify({"error": "Invalid status"}), 400
    severity = args.get("severity") or None
    if severity and severity.upper() not in {"LOW", "MEDIUM", "HIGH"}:
        return jsonify({"error": "Invalid severity"}), 400
    vuln_type = args.get("type") or None
    q = args.get("q") or None
    try:
        limit = int(args.get("limit", 200))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid limit"}), 400
    findings = get_all_findings(
        uid, repo_id=repo_id, severity=severity, vuln_type=vuln_type,
        status=status, q=q, limit=min(max(limit, 1), 500),
    )
    return jsonify({"findings": findings})


@app.route("/api/repos/<int:repo_id>/codeql", methods=["POST"])
@login_required
def api_repo_enable_codeql(repo_id):
    """Manually open (or find) the CodeQL setup PR for a repository.

    Also clears the lazy-provisioning guard so a later PR scan can retry.
    Returns the setup PR URL when one exists or was created.
    """
    repo = get_repo(repo_id, _current_github_id())
    if not repo:
        return jsonify({"error": "Repo not found"}), 404
    if not getattr(config.app.codeql, "enabled", True):
        return jsonify({"error": "CodeQL provisioning is disabled by config"}), 400
    if not _codeql_enabled_for_owner(repo_id):
        return jsonify({"error": "CodeQL feature is disabled in Settings"}), 400

    full_name = repo.get("full_name")
    install_id = repo.get("install_id")
    if not full_name or not install_id:
        return jsonify({"error": "Repository has no GitHub installation association"}), 400

    try:
        access_token = get_cached_token(install_id)
    except Exception as e:
        logger.error(f"CodeQL enable: could not get installation token: {e}", "CODEQL")
        return jsonify({"error": "Failed to get GitHub installation token"}), 500

    try:
        pr_url = create_codeql_pr(
            full_name,
            access_token,
            default_branch=repo.get("default_branch"),
            language=repo.get("language"),
        )
        if pr_url:
            mark_repo_codeql_provisioned(full_name)
        _clear_codeql_attempted(full_name)
    except Exception as e:
        logger.error(f"CodeQL enable failed for {full_name}: {e}", "CODEQL")
        return jsonify({"error": f"CodeQL provisioning failed: {e}"}), 500

    if pr_url:
        return jsonify({"success": True, "pr_url": pr_url})
    return jsonify({"success": False, "message": "No CodeQL setup PR opened — the workflow is likely already present or a setup PR is already open."})


@app.route("/api/scans", methods=["GET"])
@login_required
def api_all_scans():
    """Scans across all of the user's repos, optionally filtered."""
    uid = _current_github_id()
    if uid is None:
        return jsonify({"error": "Unauthorized"}), 401
    args = request.args
    try:
        repo_id = int(args.get("repo_id")) if args.get("repo_id") else None
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid repo_id"}), 400
    status = args.get("status") or None
    try:
        limit = int(args.get("limit", 200))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid limit"}), 400
    scans = get_all_scans(
        uid, repo_id=repo_id, status=status, limit=min(max(limit, 1), 500),
    )
    return jsonify({"scans": scans})


@app.route("/api/findings/<int:finding_id>/status", methods=["POST"])
@login_required
def api_finding_status(finding_id):
    """Resolve, dismiss, or reopen a finding."""
    uid = _current_github_id()
    if uid is None or not finding_belongs_to_user(finding_id, uid):
        return jsonify({"error": "Finding not found"}), 404
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip().lower()
    if status not in {"open", "resolved", "dismissed"}:
        return jsonify({"error": "Invalid status"}), 400
    update_finding_status(finding_id, status)
    return jsonify({"success": True, "id": finding_id, "status": status})


_INSTALL_CACHE_TTL = 300
_install_cache: dict[int, tuple[int, float]] = {}
_install_cache_lock = threading.Lock()


def _clear_install_cache():
    """Invalidate all cached installation counts (e.g. after an install event)."""
    with _install_cache_lock:
        _install_cache.clear()


_codeql_lazy_attempted: set[str] = set()
_codeql_lazy_lock = threading.Lock()


def _mark_codeql_attempted(full_name: str) -> bool:
    """Atomically claim a repo for lazy CodeQL provisioning.

    Returns True when this caller is the first to claim the repo (i.e. the
    provisioning should actually run), False if already claimed this session.
    """
    with _codeql_lazy_lock:
        if full_name in _codeql_lazy_attempted:
            return False
        _codeql_lazy_attempted.add(full_name)
        return True


def _codeql_enabled_for_owner(repo_id: int) -> bool:
    """Whether the repo's owning user has the CodeQL feature enabled.

    Unattributed repos (no user_id) fall back to the system default (True).
    """
    try:
        repo_row = get_repo(repo_id)
        owner_uid = repo_row.get("user_id") if repo_row else None
        return bool(get_user_settings(owner_uid).get("codeql_enabled", True))
    except Exception as e:
        logger.warning(f"Could not resolve CodeQL preference for repo {repo_id}: {e}", "CODEQL")
        return True


def _clear_codeql_attempted(full_name: str):
    """Allow a retry for a repo (e.g. from the dashboard enable button)."""
    with _codeql_lazy_lock:
        _codeql_lazy_attempted.discard(full_name)


def _provision_codeql_for_repos(repos, installation_id, require_auto_provision: bool = True):
    """Best-effort: open a CodeQL setup PR for each newly-added repository.

    Runs on the background executor so the webhook ack is never delayed.
    Skips silently when CodeQL provisioning is disabled; logs and continues
    per-repo on errors (create_codeql_pr never raises).

    ``require_auto_provision`` is True for fresh-install events but False for
    the lazy first-PR-scan path (a repo installed before the feature existed
    still deserves provisioning even when the install-time toggle is off).
    """
    if not getattr(config.app.codeql, "enabled", True):
        logger.info("CodeQL provisioning disabled by config — skipping", "CODEQL")
        return
    if require_auto_provision and not getattr(config.app.codeql, "auto_provision", True):
        logger.info("CodeQL auto-provisioning disabled — skipping", "CODEQL")
        return

    if not repos:
        return

    try:
        access_token = get_cached_token(installation_id)
    except Exception as e:
        logger.error(f"CodeQL provisioning: could not get installation token: {e}", "CODEQL")
        return

    for repo in repos:
        full_name = repo.get("full_name", "")
        if not full_name:
            continue
        try:
            pr_url = create_codeql_pr(
                full_name,
                access_token,
                default_branch=repo.get("default_branch"),
                language=repo.get("language"),
            )
            if pr_url:
                mark_repo_codeql_provisioned(full_name)
        except Exception as e:
            logger.error(f"CodeQL provisioning failed for {full_name}: {e}", "CODEQL")


_token_fernet = None


def _get_token_fernet() -> Fernet:
    """Return a Fernet instance keyed off FLASK_SECRET_KEY (stable across restarts)."""
    global _token_fernet
    if _token_fernet is None:
        secret = app.secret_key
        if not secret:
            raise RuntimeError("FLASK_SECRET_KEY not configured")
        key_material = secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)
        key = hashlib.sha256(key_material).digest()
        _token_fernet = Fernet(base64.urlsafe_b64encode(key))
    return _token_fernet


def _encrypt_token(value: str) -> str:
    return _get_token_fernet().encrypt(value.encode("utf-8")).decode("ascii")


def _decrypt_token(value) -> str | None:
    """Decrypt a session token; returns None when absent or tampered."""
    if not value:
        return None
    try:
        return _get_token_fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return None


def _clear_session_token():
    """Drop OAuth token state so the user is forced to re-authenticate."""
    session.pop("github_access_token", None)
    session.pop("github_refresh_token", None)
    session.pop("github_token_expires_at", None)


def _refresh_github_token(refresh_token):
    """Exchange a GitHub user-access refresh token for a new access token."""
    try:
        resp = requests.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("access_token"):
                return data
        logger.warning(f"GitHub token refresh returned {resp.status_code}")
    except requests.RequestException as e:
        logger.warning(f"GitHub token refresh request failed: {e}")
    return None


def _get_valid_access_token():
    """Return a usable GitHub user access token, refreshing when possible.

    GitHub App user tokens expire (~8h by default) only when the app has token
    expiration enabled; this is a no-op otherwise. Tokens are stored encrypted
    in the session (see _encrypt_token/_decrypt_token).
    """
    token = _decrypt_token(session.get("github_access_token"))
    if not token:
        return None

    expires_at = session.get("github_token_expires_at")
    refresh_token = _decrypt_token(session.get("github_refresh_token"))
    if expires_at is not None and time.time() >= expires_at:
        if refresh_token:
            refreshed = _refresh_github_token(refresh_token)
            if refreshed:
                token = refreshed["access_token"]
                session["github_access_token"] = _encrypt_token(token)
                session["github_token_expires_at"] = time.time() + refreshed.get("expires_in", 28800)
                if refreshed.get("refresh_token"):
                    session["github_refresh_token"] = _encrypt_token(refreshed["refresh_token"])
                return token
        _clear_session_token()
        logger.warning("GitHub token expired and could not be refreshed — cleared session token", "AUTH")
        return None
    return token


def _get_installation_count(github_id, access_token):
    """Return the number of GitHub App installations for a user, cached with a TTL.

    Returns -1 when the count is unknown (no token or GitHub API failure) so the
    frontend never shows a misleading "install the app" banner.
    """
    if not access_token:
        return -1

    now = time.time()
    with _install_cache_lock:
        cached = _install_cache.get(github_id)
        if cached and now - cached[1] < _INSTALL_CACHE_TTL:
            return cached[0]

    try:
        resp = requests.get(
            "https://api.github.com/user/installations",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if resp.status_code == 401:
            _clear_session_token()
            logger.warning("GitHub token expired or revoked — cleared session token", "AUTH")
            return -1
        if resp.status_code != 200:
            logger.warning(f"GitHub installations API returned {resp.status_code}")
            return -1
        count = len(resp.json().get("installations", []))
        with _install_cache_lock:
            _install_cache[github_id] = (count, now)
        return count
    except Exception as e:
        logger.warning(f"Failed to fetch installation count from GitHub: {e}")
        return -1


def _github_app_install_url():
    """Return the GitHub App installation URL, or '' when GITHUB_APP_SLUG is not set."""
    slug = os.environ.get("GITHUB_APP_SLUG", "").strip()
    if not slug:
        return ""
    return f"https://github.com/apps/{slug}/installations/new"


def _sync_repos_from_github(github_id, access_token):
    """Fetch installation repos + the install->user mapping for a user.

    Records which installations the user can access (user_installations) and
    upserts their repos so the dashboard and scan attribution are per-user.
    """
    try:
        resp = requests.get(
            "https://api.github.com/user/installations",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if resp.status_code == 401:
            _clear_session_token()
            logger.warning("GitHub token expired or revoked — cleared session token", "AUTH")
            return
        if resp.status_code != 200:
            logger.warning(f"GitHub installations API returned {resp.status_code}")
            return

        installations = resp.json().get("installations", [])
        sync_user_installations(github_id, installations)
        for inst in installations:
            inst_id = inst.get("id")
            if not inst_id:
                continue

            repos_resp = requests.get(
                f"https://api.github.com/user/installations/{inst_id}/repositories",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
                timeout=10,
            )
            if repos_resp.status_code != 200:
                logger.warning(f"Installation repos API returned {repos_resp.status_code} for install {inst_id}")
                continue

            for repo in repos_resp.json().get("repositories", []):
                upsert_repo({
                    "id": repo.get("id", 0),
                    "full_name": repo.get("full_name", ""),
                    "owner": (repo.get("owner") or {}).get("login", ""),
                    "name": repo.get("name", ""),
                    "description": repo.get("description") or "",
                    "language": repo.get("language") or "",
                    "private": 1 if repo.get("private") else 0,
                    "default_branch": repo.get("default_branch", "main"),
                    "install_id": inst_id,
                })
    except Exception as e:
        logger.warning(f"Failed to sync repos from GitHub: {e}")


@app.route("/api/metrics", methods=["GET"])
@login_required
def metrics():
    """Returns JSON metrics for the dashboard (scoped to the logged-in user)."""
    return jsonify(get_dashboard(_current_github_id()))


@app.route("/api/dashboard", methods=["GET"])
@login_required
def api_dashboard():
    """Alias for /api/metrics — returns JSON dashboard data (per-user)."""
    uid = _current_github_id()
    repos = get_repos(uid)
    if not repos:
        token = _get_valid_access_token()
        if token and uid is not None:
            _sync_repos_from_github(uid, token)
    return jsonify(get_dashboard(uid))


@app.route("/api/metrics/prometheus", methods=["GET"])
def prometheus_metrics():
    """Returns Prometheus metrics in exposition format.

    When METRICS_SCRAPE_TOKEN is set, Prometheus can scrape this path without a
    browser session using `Authorization: Bearer <token>` (constant-time
    comparison). When it is unset, the endpoint keeps requiring a normal
    authenticated dashboard session.
    """
    scrape_token = os.environ.get("METRICS_SCRAPE_TOKEN", "").strip()
    if scrape_token:
        expected = f"Bearer {scrape_token}"
        if not secrets.compare_digest(request.headers.get("Authorization", ""), expected):
            return jsonify({"error": "Unauthorized"}), 401
    elif not session.get("user") and not session.get("github_id"):
        return jsonify({"error": "Unauthorized"}), 401
    from app.metrics import get_content_type, get_metrics
    return get_metrics(), 200, {'Content-Type': get_content_type()}


@app.route("/api/policy", methods=["GET"])
@login_required
def get_policy_api():
    """Returns the current security policy."""
    from core.policy.policy_engine import PolicyEngine
    engine = PolicyEngine()
    return jsonify(engine.policy)


@app.route("/api/health/gemini", methods=["GET"])
@login_required
def gemini_health():
    """Lightweight Gemini connectivity check (env var only — no API call)."""
    configured = bool(os.environ.get("GEMINI_API_KEY"))
    return jsonify({
        "status": "online" if configured else "offline",
        "configured": configured
    })


@app.route("/api/health/db", methods=["GET"])
@login_required
def health_db():
    """Writable SQLite connectivity check — useful for platform health checks."""
    ok = db_health()
    return jsonify({"status": "ok" if ok else "error"}), (200 if ok else 500)


@app.route("/api/settings", methods=["GET"])
@login_required
def get_settings_api():
    """Return the logged-in user's effective scan settings and available options."""
    from core.validator.sandbox import Sandbox
    from utils.db import SANDBOX_NETWORKS, SCAN_MODES, get_user_settings
    uid = _current_github_id()
    settings = get_user_settings(uid)
    sandbox = Sandbox()
    docker_available = sandbox._is_docker_available()
    return jsonify({
        "settings": settings,
        "options": {
            "scan_modes": list(SCAN_MODES),
            "networks": list(SANDBOX_NETWORKS),
            "docker_available": docker_available,
        },
    })


@app.route("/api/settings", methods=["POST"])
@login_required
def update_settings_api():
    """Persist the logged-in user's scan settings."""
    uid = _current_github_id()
    if uid is None:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    scan_mode = data.get("scan_mode")
    sandbox_network = data.get("sandbox_network")
    codeql_enabled = data.get("codeql_enabled")
    if scan_mode is None and sandbox_network is None and codeql_enabled is None:
        return jsonify({"error": "Provide scan_mode, sandbox_network and/or codeql_enabled"}), 400
    if codeql_enabled is not None and not isinstance(codeql_enabled, bool):
        return jsonify({"error": "codeql_enabled must be a boolean"}), 400
    try:
        settings = update_user_settings(
            uid, scan_mode=scan_mode, sandbox_network=sandbox_network, codeql_enabled=codeql_enabled,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"settings": settings, "saved": True})


@app.route("/api/health/sandbox", methods=["GET"])
@login_required
def health_sandbox():
    """Sandbox execution mode and Docker status (non-provisioning check)."""
    from core.validator.sandbox import Sandbox
    sandbox = Sandbox()
    docker_available = sandbox._is_docker_available()
    image_ready = sandbox.docker_image_available() if docker_available else False
    return jsonify({
        "docker_available": docker_available,
        "image_ready": image_ready,
        "mode": "docker" if docker_available and image_ready else "unavailable",
    })


@app.route("/dashboard", methods=["GET"])
def dashboard():
    """Serves the React SPA dashboard."""
    if _os.path.exists(_os.path.join(_static_dir, "index.html")):
        return send_from_directory(_static_dir, "index.html")
    return jsonify({"error": "Frontend not built. Run: cd frontend && npm run build"}), 404


@app.route("/api/feedback", methods=["POST"])
@app.route("/feedback", methods=["POST"])
@login_required
def feedback():
    """Record developer feedback (ACCEPTED/REJECTED) with optional user attribution."""
    try:
        data = request.json
        vuln_type = data.get("vuln_type")
        outcome = data.get("outcome")
        if not vuln_type or outcome not in ("ACCEPTED", "REJECTED"):
            return jsonify({"error": "Invalid feedback data"}), 400
        user_id = data.get("user_id", "")
        display_name = data.get("display_name", "")
        # Attribute feedback to the logged-in user when no explicit identity is
        # sent, so the existing (vuln_type, user_id) upsert dedupes re-votes
        # instead of accumulating anonymous duplicate rows.
        if not user_id:
            u = session.get("user")
            if u:
                user_id = u.get("login", "") or ""
                if not display_name:
                    display_name = (u.get("name") or u.get("login") or "") or ""

        # Optional scan context so feedback is tied to a repo/PR.
        repo_id = data.get("repo_id")
        pr_number = data.get("pr_number")
        scan_id = data.get("scan_id")
        for name, val in (("repo_id", repo_id), ("pr_number", pr_number), ("scan_id", scan_id)):
            if val is not None and not isinstance(val, int):
                return jsonify({"error": f"{name} must be an integer"}), 400
            if val is not None and val <= 0:
                return jsonify({"error": f"{name} must be positive"}), 400

        # Input validation
        valid_types = {"COMMAND_INJECTION", "CODE_INJECTION", "HARDCODED_SECRET", "SQL_INJECTION", "PATH_TRAVERSAL", "SSRF", "WEAK_CRYPTOGRAPHY", "INSECURE_DESERIALIZATION"}
        if vuln_type not in valid_types:
            return jsonify({"error": "Invalid vulnerability type"}), 400
        if len(user_id) > 100:
            user_id = user_id[:100]
        if len(display_name) > 100:
            display_name = display_name[:100]

        # Rate limiting
        ip = request.remote_addr or "unknown"
        if _check_feedback_rate_limit(ip):
            logger.warning(f"Feedback rate limit exceeded for {ip}", "FEEDBACK")
            return jsonify({"error": "Too many requests"}), 429

        record_feedback(vuln_type, outcome, user_id=user_id, display_name=display_name,
                        repo_id=repo_id, pr_number=pr_number, scan_id=scan_id)
        logger.info(f"Feedback recorded: {vuln_type} -> {outcome}", "FEEDBACK")
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Feedback failure: {e}", "FEEDBACK")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/webhook", methods=["POST"])
def github_webhook():
    try:
        signature = request.headers.get("X-Hub-Signature-256", "")
        payload = request.data
        
        event = request.headers.get("X-GitHub-Event")
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid or missing JSON body"}), 400

        if not verify_signature(payload, signature):
            logger.error("Invalid webhook signature", "WEBHOOK")
            return jsonify({"error": "Invalid signature"}), 403

        # Webhook deduplication (Phase 3)
        delivery_id = request.headers.get("X-GitHub-Delivery", "")
        if delivery_id and _is_delivery_duplicate(delivery_id):
            logger.info(f"Duplicate webhook delivery {delivery_id} skipped", "WEBHOOK")
            return jsonify({"status": "duplicate"})

        # INSTALLATION LIFECYCLE — update local repo/installation state
        if event == "installation":
            action = data.get("action", "")
            install_id = data.get("installation", {}).get("id", 0)
            if action == "deleted":
                if install_id:
                    delete_repos_by_install(install_id)
                logger.info(f"GitHub App uninstalled (install {install_id}) — repos removed", "WEBHOOK")
            elif action == "created" and install_id:
                repos = data.get("repositories", [])
                logger.info(f"GitHub App installed (install {install_id}) — {len(repos)} repos", "WEBHOOK")
                try:
                    executor.submit(_provision_codeql_for_repos, repos, install_id)
                except Exception as e:
                    logger.error(f"Failed to queue CodeQL provisioning: {e}", "WEBHOOK")
            _clear_install_cache()
            return jsonify({"status": "installation_processed"})

        if event == "installation_repositories":
            for repo in data.get("repositories_removed", []):
                full_name = repo.get("full_name", "")
                if full_name:
                    delete_repo_by_full_name(full_name)
            install_id = data.get("installation", {}).get("id", 0)
            added = data.get("repositories_added", [])
            if install_id and added:
                try:
                    executor.submit(_provision_codeql_for_repos, added, install_id)
                except Exception as e:
                    logger.error(f"Failed to queue CodeQL provisioning: {e}", "WEBHOOK")
            _clear_install_cache()
            return jsonify({"status": "installation_repos_processed"})

        if event == "pull_request":
            action = data.get("action")
            
            # PHASE 3: AUTOMATED FEEDBACK (MERGES)
            if action == "closed" and data["pull_request"].get("merged"):
                pr_number = data["pull_request"]["number"]
                merged_by = data["pull_request"].get("merged_by", {}).get("login", "unknown")
                findings = get_pr_findings(pr_number)
                for vuln_type in findings:
                    record_feedback(vuln_type, "ACCEPTED", user_id=merged_by, display_name=merged_by)
                    logger.info(f"Auto-Feedback: {vuln_type} accepted via Merge (PR #{pr_number}) by {merged_by}", "FEEDBACK")
                resolved = resolve_open_findings_for_pr(pr_number)
                if resolved:
                    logger.info(f"Resolved {resolved} open finding(s) for merged PR #{pr_number}", "WEBHOOK")
                return jsonify({"status": "merge_feedback_processed"})

            if action not in ("opened", "synchronize", "reopened"):
                return jsonify({"status": "ignored"})

            repo_name = data.get("repository", {}).get("full_name", "")
            pr_number = data.get("pull_request", {}).get("number", 0)
            installation_id = data.get("installation", {}).get("id", 0)
            branch_name = data.get("pull_request", {}).get("head", {}).get("ref", "")
            commit_sha = data.get("pull_request", {}).get("head", {}).get("sha", "")
            pr_title = data.get("pull_request", {}).get("title", "")

            if not repo_name or not pr_number or not installation_id:
                logger.error(f"Missing required webhook fields: repo={repo_name} pr={pr_number} install={installation_id}", "WEBHOOK")
                return jsonify({"error": "Missing required fields"}), 400

            # Skip the App's own CodeQL provisioning PR: it only adds workflow
            # YAML (no .py code to scan) and its scan would otherwise fail
            # pointlessly / spam "Analysis Failed" comments.
            provisioning_branch = getattr(config.app.codeql, "workflow_branch", "ai-risk-guard/codeql-setup")
            if branch_name == provisioning_branch:
                logger.info(f"Skipping analysis for CodeQL provisioning PR #{pr_number} (branch {branch_name})", "WEBHOOK")
                return jsonify({"status": "ignored"})

            # Persist repo info from webhook payload
            repo_payload = data.get("repository", {})
            upsert_repo({
                "id": repo_payload.get("id", 0),
                "full_name": repo_name,
                "owner": (repo_payload.get("owner") or {}).get("login", ""),
                "name": repo_payload.get("name", ""),
                "description": repo_payload.get("description") or "",
                "language": repo_payload.get("language") or "",
                "private": 1 if repo_payload.get("private") else 0,
                "default_branch": repo_payload.get("default_branch", "main"),
                "install_id": installation_id,
            })

            repo_id = repo_payload.get("id", 0)
            logger.info(f"Accepted PR #{pr_number} for background processing", "WEBHOOK")

            # Lazy CodeQL provisioning (Phase 4.3 follow-up): repos installed
            # before the feature existed never received a setup PR. Provision on
            # the first PR scan instead, once per repo (persisted in DB) per session (in-memory).
            # Broadened to include synchronize/reopened so any PR action triggers provisioning,
            # not just "opened".
            if (
                action in ("opened", "synchronize", "reopened")
                and repo_name
                and getattr(config.app.codeql, "enabled", True)
                and _codeql_enabled_for_owner(repo_id)  # per-user Settings toggle
                and not is_repo_codeql_provisioned(repo_name)  # DB-persisted guard
                and _mark_codeql_attempted(repo_name)  # in-memory session dedup
            ):
                try:
                    executor.submit(_provision_codeql_for_repos, [repo_payload], installation_id, False)
                    logger.info(f"Queued lazy CodeQL provisioning for {repo_name}", "CODEQL")
                except Exception as e:
                    logger.error(f"Failed to queue lazy CodeQL provisioning for {repo_name}: {e}", "CODEQL")

            if not _analysis_slot.acquire(blocking=False):
                logger.warning(f"Analysis capacity reached — rejecting PR #{pr_number}", "WEBHOOK")
                return jsonify({"error": "Analysis capacity reached, try again shortly"}), 429

            try:
                executor.submit(_run_analysis_slot, repo_name, repo_id, pr_number, pr_title, installation_id, branch_name, commit_sha)
            except Exception:
                _analysis_slot.release()
                raise

            return jsonify({"status": "accepted", "message": "Analysis started in background"}), 202

        return jsonify({"status": "ignored"})
    except Exception as error:
        logger.error(f"Webhook reception failed: {error}", "WEBHOOK")
        return jsonify({"error": "Internal server error"}), 500


# =========================================================
# REACT FRONTEND — Serve SPA for all non-API routes
# =========================================================


@app.route("/api/<path:path>")
def api_not_found(path):
    """Unknown /api/... paths return JSON 404 instead of the SPA."""
    return jsonify({"error": f"API endpoint not found: /api/{path}"}), 404


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    index_path = _os.path.join(_static_dir, "index.html")
    if _os.path.exists(index_path):
        return send_from_directory(_static_dir, "index.html")
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Unhandled server error: {e}", "SERVER", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path and _os.path.exists(_os.path.join(_static_dir, path)):
        return send_from_directory(_static_dir, path)
    index_path = _os.path.join(_static_dir, "index.html")
    if _os.path.exists(index_path):
        return send_from_directory(_static_dir, "index.html")
    return jsonify({"error": "Frontend not built. Run: cd frontend && npm run build"}), 404


if __name__ == "__main__":
    # Docker availability check for sandbox debugging
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.info("Docker: available (sandbox will use containers)", "STARTUP")
            sandbox_image = config.sandbox.docker.image
            try:
                img_result = subprocess.run(
                    ["docker", "image", "inspect", sandbox_image],
                    capture_output=True,
                    timeout=5,
                )
                if img_result.returncode != 0:
                    # Pre-warm the sandbox image in the background so the first
                    # scan does not pay the pull/build cost (or fail closed if
                    # provisioning is slow).
                    logger.info(
                        f"Docker: daemon up but sandbox image '{sandbox_image}' not found — "
                        "pre-building in the background",
                        "STARTUP",
                    )

                    def _prebuild_image():
                        from core.validator.sandbox import Sandbox
                        try:
                            sandbox = Sandbox()
                            sandbox._ensure_image_available()
                            if sandbox.image_unavailable:
                                logger.warning(
                                    f"Docker: could not pre-build sandbox image '{sandbox_image}' — "
                                    "scans will fail closed until it is available",
                                    "STARTUP",
                                )
                            else:
                                logger.info(
                                    f"Docker: sandbox image '{sandbox_image}' pre-built",
                                    "STARTUP",
                                )
                        except Exception as e:
                            logger.warning(f"Docker: pre-build failed - {e}", "STARTUP")

                    try:
                        executor.submit(_prebuild_image)
                    except Exception as e:
                        logger.warning(f"Docker: could not queue pre-build - {e}", "STARTUP")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                logger.warning(
                    "Docker: could not verify sandbox image presence", "STARTUP"
                )
            except Exception as e:
                logger.warning(f"Docker: image check failed - {e}", "STARTUP")
        else:
            logger.warning("Docker: installed but not running (scans will fail closed until Docker is available)", "STARTUP")
    except FileNotFoundError:
        logger.warning("Docker: not installed (scans will fail closed until Docker is available)", "STARTUP")
    except subprocess.TimeoutExpired:
        logger.warning("Docker: detected but unresponsive (scans will fail closed until Docker is available)", "STARTUP")
    except Exception as e:
        logger.warning(f"Docker: check failed - {e} (scans will fail closed until Docker is available)", "STARTUP")

    sc = config.app.server
    port = int(os.environ.get("PORT", sc.port))
    print(f"\n  AI Risk Guard running at http://{sc.host}:{port}")
    print(f"  Dashboard:              http://{sc.host}:{port}/dashboard\n")
    from waitress import serve
    serve(app, host=sc.host, port=port, threads=sc.workers)

