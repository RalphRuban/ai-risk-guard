"""
utils/db.py
Persistent SQLite-backed dashboard storage.
Replaces the in-memory analysis_data dict in main.py.
"""

import json
import os
import sqlite3
from pathlib import Path

# Resolve the DB path against the repo root so the app works no matter which
# working directory it is launched from (systemd, cron, tests, WSGI). Absolute
# paths from DB_PATH are used as-is.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DB_PATH = _REPO_ROOT / "data" / "dashboard.db"
DB_PATH = Path(os.getenv("DB_PATH", str(_DEFAULT_DB_PATH)))
if not DB_PATH.is_absolute():
    DB_PATH = (_REPO_ROOT / DB_PATH).resolve()

# ---------------------------------------------------------------------------
# Scan configuration constants (Phase 4.1). Kept here so both the API and the
# webhook path can import them from a single place.
# ---------------------------------------------------------------------------
DEFAULT_SCAN_MODE = "docker_only"
DEFAULT_SANDBOX_NETWORK = "none"
SCAN_MODES = frozenset({
    DEFAULT_SCAN_MODE,
    # Legacy value from before the fail-closed change; still accepted for
    # existing saved settings but behaves identically to docker_only.
    "sandbox_with_local_fallback",
})
SANDBOX_NETWORKS = frozenset({
    DEFAULT_SANDBOX_NETWORK,
    "bridge",
})


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _cleanup_orphans(conn: sqlite3.Connection):
    """Remove rows referencing non-existent parents before enabling FK constraints."""
    conn.execute("DELETE FROM findings WHERE scan_id NOT IN (SELECT id FROM scans)")
    conn.execute("DELETE FROM scans WHERE repo_id NOT IN (SELECT id FROM repos)")


def _migrate_fk_constraints():
    """Add FOREIGN KEY ... ON DELETE CASCADE to scans/findings (SQLite table rebuild).

    Idempotent: skips when the constraints already exist. Runs on its own
    autocommit connection because PRAGMA foreign_keys is a no-op inside a
    transaction.
    """
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0, isolation_level=None)
    try:
        if conn.execute("PRAGMA foreign_key_list(scans)").fetchall():
            return

        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN")

        conn.execute("""
            CREATE TABLE scans_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
                pr_number INTEGER NOT NULL,
                pr_title TEXT DEFAULT '',
                branch TEXT DEFAULT '',
                commit_sha TEXT DEFAULT '',
                status TEXT DEFAULT 'completed',
                findings_count INTEGER DEFAULT 0,
                max_risk REAL DEFAULT 0.0,
                duration_ms INTEGER DEFAULT 0,
                user_id INTEGER,
                scanned_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            INSERT INTO scans_new (id, repo_id, pr_number, pr_title, branch, commit_sha,
                                   status, findings_count, max_risk, duration_ms, user_id, scanned_at)
            SELECT id, repo_id, pr_number, pr_title, branch, commit_sha,
                   status, findings_count, max_risk, duration_ms, user_id, scanned_at
            FROM scans
        """)
        conn.execute("DROP TABLE scans")
        conn.execute("ALTER TABLE scans_new RENAME TO scans")

        conn.execute("""
            CREATE TABLE findings_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
                vuln_type TEXT NOT NULL,
                severity TEXT DEFAULT 'MEDIUM',
                risk_score REAL DEFAULT 0.0,
                file_path TEXT DEFAULT '',
                line_number INTEGER DEFAULT 0,
                is_new INTEGER DEFAULT 0,
                status TEXT DEFAULT 'open',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            INSERT INTO findings_new (id, scan_id, vuln_type, severity, risk_score,
                                      file_path, line_number, is_new, status, created_at)
            SELECT id, scan_id, vuln_type, severity, risk_score,
                   file_path, line_number, is_new, status, created_at
            FROM findings
        """)
        conn.execute("DROP TABLE findings")
        conn.execute("ALTER TABLE findings_new RENAME TO findings")

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.close()


def _migrate_validation_status():
    """Add the ``validation_status`` column to scans (deferred re-validation).

    Idempotent: skips when the column already exists. Uses a plain ALTER TABLE
    because the new column is a simple TEXT default with no constraints.
    """
    with _connect() as conn:
        cols = [row["name"] for row in conn.execute("PRAGMA table_info(scans)").fetchall()]
        if "validation_status" not in cols:
            conn.execute(
                "ALTER TABLE scans ADD COLUMN validation_status TEXT DEFAULT 'ok'"
            )
            conn.commit()


def init_db():
    """Create tables if they do not exist. Call once at startup."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dashboard (
                key   TEXT PRIMARY KEY,
                value INTEGER NOT NULL DEFAULT 0
            )
        """)

        # Feedback table with multi-user support
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patch_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vuln_type TEXT NOT NULL,
                outcome TEXT NOT NULL,
                user_id TEXT DEFAULT '',
                display_name TEXT DEFAULT '',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration: add user_id column to existing tables
        cursor = conn.execute("PRAGMA table_info(patch_feedback)")
        existing_cols = [row["name"] for row in cursor.fetchall()]
        if "user_id" not in existing_cols:
            conn.execute("ALTER TABLE patch_feedback ADD COLUMN user_id TEXT DEFAULT ''")
        if "display_name" not in existing_cols:
            conn.execute("ALTER TABLE patch_feedback ADD COLUMN display_name TEXT DEFAULT ''")
        # Migration: add repo/PR/scan context so feedback is attributable to a
        # specific repository and pull request (Phase 4.2).
        if "repo_id" not in existing_cols:
            conn.execute("ALTER TABLE patch_feedback ADD COLUMN repo_id INTEGER")
        if "pr_number" not in existing_cols:
            conn.execute("ALTER TABLE patch_feedback ADD COLUMN pr_number INTEGER")
        if "scan_id" not in existing_cols:
            conn.execute("ALTER TABLE patch_feedback ADD COLUMN scan_id INTEGER")

        # Unique index: one vote per user per vuln type (skip when user_id is empty)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_feedback_user_vuln
            ON patch_feedback (vuln_type, user_id)
            WHERE user_id != ''
        """)

        # New table to track findings per PR for automated merge-feedback (Phase 3)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pr_findings (
                pr_number INTEGER,
                vuln_type TEXT,
                PRIMARY KEY (pr_number, vuln_type)
            )
        """)

        # Bot PR comments tracked so the reaction poller knows which comments to
        # query for rocket/plus-one feedback (replaces the non-existent `reaction` webhook).
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_comments (
                comment_id INTEGER PRIMARY KEY,
                repo TEXT NOT NULL,
                pr_number INTEGER NOT NULL,
                posted_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Already-harvested reactions (dedup for the poller). A reaction that is
        # removed upstream is intentionally not rolled back once processed.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_reactions (
                reaction_id INTEGER PRIMARY KEY,
                comment_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                processed_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Scan cache: per-file, per-commit-hash scan results
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_cache (
                cache_key TEXT PRIMARY KEY,
                file_path TEXT NOT NULL DEFAULT '',
                results TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ttl_seconds INTEGER DEFAULT 3600
            )
        """)
        # Migration: older scan_cache tables lacked the file_path column that
        # ScanCache writes; add it in place so writes never fail silently.
        try:
            scan_cols = {r["name"] for r in conn.execute("PRAGMA table_info(scan_cache)")}
            if "file_path" not in scan_cols:
                conn.execute("ALTER TABLE scan_cache ADD COLUMN file_path TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass

        # AST/CST parse cache (tree stores pickled AST bytes -> BLOB affinity)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ast_cache (
                cache_key TEXT PRIMARY KEY,
                file_path TEXT NOT NULL DEFAULT '',
                tree BLOB NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ttl_seconds INTEGER DEFAULT 86400
            )
        """)

        # Migration: ast_cache.tree must have BLOB affinity. Tables created with
        # TEXT affinity can corrupt pickled AST bytes, so drop and recreate the
        # disposable parse cache when the affinity is wrong.
        ast_cols = {r["name"]: (r["type"] or "").upper()
                    for r in conn.execute("PRAGMA table_info(ast_cache)").fetchall()}
        if ast_cols.get("tree") != "BLOB":
            conn.execute("DROP TABLE IF EXISTS ast_cache")
            conn.execute("""
                CREATE TABLE ast_cache (
                    cache_key TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL DEFAULT '',
                    tree BLOB NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ttl_seconds INTEGER DEFAULT 86400
                )
            """)

        # Gemini response cache (keyed by prompt hash)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gemini_cache (
                cache_key TEXT PRIMARY KEY,
                response TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ttl_seconds INTEGER DEFAULT 86400
            )
        """)

        # Users table for GitHub OAuth login
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                github_id INTEGER PRIMARY KEY,
                login TEXT NOT NULL,
                name TEXT DEFAULT '',
                avatar_url TEXT DEFAULT ''
            )
        """)

        # Mapping of GitHub App installations to the users who can access them.
        # Synced from /user/installations at login. Drives per-user dashboards
        # and scan attribution (works for both user-level and org installs).
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_installations (
                github_id INTEGER NOT NULL REFERENCES users(github_id) ON DELETE CASCADE,
                install_id INTEGER NOT NULL,
                account_type TEXT DEFAULT 'User',
                account_login TEXT DEFAULT '',
                synced_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (github_id, install_id)
            )
        """)

        # Per-user scan configuration (Phase 4.1). NULL value columns mean
        # "use the system default" for that user.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                github_id INTEGER PRIMARY KEY REFERENCES users(github_id) ON DELETE CASCADE,
                scan_mode TEXT,
                sandbox_network TEXT,
                codeql_enabled INTEGER DEFAULT 1,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Migration: add codeql_enabled to user_settings tables created before
        # the CodeQL enable toggle shipped (existing on-disk DBs).
        us_cols = [r["name"] for r in conn.execute("PRAGMA table_info(user_settings)").fetchall()]
        if "codeql_enabled" not in us_cols:
            conn.execute("ALTER TABLE user_settings ADD COLUMN codeql_enabled INTEGER DEFAULT 1")

        # Repos discovered from webhooks
        conn.execute("""
            CREATE TABLE IF NOT EXISTS repos (
                id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                owner TEXT DEFAULT '',
                name TEXT DEFAULT '',
                description TEXT DEFAULT '',
                language TEXT DEFAULT '',
                private INTEGER DEFAULT 0,
                default_branch TEXT DEFAULT 'main',
                install_id INTEGER DEFAULT 0,
                user_id INTEGER,
                first_seen_at TEXT,
                last_scanned_at TEXT,
                codeql_provisioned INTEGER DEFAULT 0
            )
        """)

        # Migration: add codeql_provisioned to repos tables created before the
        # CodeQL provisioning feature shipped (existing on-disk DBs).
        repo_cols = [r["name"] for r in conn.execute("PRAGMA table_info(repos)").fetchall()]
        if "codeql_provisioned" not in repo_cols:
            conn.execute("ALTER TABLE repos ADD COLUMN codeql_provisioned INTEGER DEFAULT 0")

        # Per-PR scan records
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL,
                pr_number INTEGER NOT NULL,
                pr_title TEXT DEFAULT '',
                branch TEXT DEFAULT '',
                commit_sha TEXT DEFAULT '',
                status TEXT DEFAULT 'completed',
                validation_status TEXT DEFAULT 'ok',
                findings_count INTEGER DEFAULT 0,
                max_risk REAL DEFAULT 0.0,
                duration_ms INTEGER DEFAULT 0,
                user_id INTEGER,
                scanned_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Individual vulnerability findings from scans
        conn.execute("""
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL,
                vuln_type TEXT NOT NULL,
                severity TEXT DEFAULT 'MEDIUM',
                risk_score REAL DEFAULT 0.0,
                file_path TEXT DEFAULT '',
                line_number INTEGER DEFAULT 0,
                is_new INTEGER DEFAULT 0,
                status TEXT DEFAULT 'open',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # CI-runner fallback validation jobs (Phase E). When the App's Docker
        # daemon is unavailable the sandbox + regression-test evidence for a
        # candidate is captured here, dispatched to a GitHub Actions runner via
        # repository_dispatch, and the completed results re-injected into a
        # re-analysis pass so the PR comment/check pick up runtime evidence.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_full_name TEXT NOT NULL,
                pr_number INTEGER NOT NULL DEFAULT 0,
                commit_sha TEXT DEFAULT '',
                source_filename TEXT DEFAULT '',
                candidate_id TEXT DEFAULT '',
                patched_code TEXT NOT NULL,
                test_filename TEXT DEFAULT '',
                test_content TEXT DEFAULT '',
                extra_files TEXT DEFAULT '[]',
                scan_mode TEXT DEFAULT '',
                sandbox_network TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                result_json TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE (repo_full_name, commit_sha, source_filename, candidate_id)
            )
        """)

        # Seed rows so UPDATE always finds a row
        for key in ("total_prs", "total_vulnerabilities",
                    "risk_LOW", "risk_MEDIUM", "risk_HIGH",
                    "cache_hits", "cache_misses"):
            conn.execute(
                "INSERT OR IGNORE INTO dashboard (key, value) VALUES (?, 0)",
                (key,),
            )

        # Remove rows that reference missing parents before FK constraints are
        # enabled on the freshly built scans/findings tables.
        _cleanup_orphans(conn)

        conn.commit()

    # Idempotent schema upgrade: add ON DELETE CASCADE foreign keys.
    _migrate_fk_constraints()
    # Idempotent schema upgrade: validation_status column for deferred re-validation.
    _migrate_validation_status()
    # Query-planning indexes for the most frequent access patterns.
    _create_indexes()
    # Best-effort housekeeping (expired cache rows, VACUUM).
    with _connect() as conn:
        _purge_expired_cache_rows(conn)
    _maybe_vacuum()


def _create_indexes():
    """Create indexes for the most frequent query patterns."""
    with _connect() as conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_repo_scanned ON scans (repo_id, scanned_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_findings_scan ON findings (scan_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_findings_status ON findings (status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_findings_severity_status ON findings (severity, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_vuln_ts ON patch_feedback (vuln_type, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_ts ON patch_feedback (timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_repos_install ON repos (install_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_install_user ON user_installations (github_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_install_install ON user_installations (install_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pending_validation_commit ON pending_validations (repo_full_name, commit_sha)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_gemini_cache_created ON gemini_cache (created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ast_cache_created ON ast_cache (created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_cache_created ON scan_cache (created_at)")
        has_tfc = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_file_cache'"
        ).fetchone()
        if has_tfc:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_test_file_cache_created ON test_file_cache (created_at)")


def _purge_expired_cache_rows(conn: sqlite3.Connection):
    """Delete expired cache rows."""
    tables = ("scan_cache", "ast_cache", "gemini_cache", "test_file_cache")
    for table in tables:
        try:
            sql = (
                f"DELETE FROM {table} WHERE "
                f"(strftime('%s', 'now') - strftime('%s', created_at)) >= ttl_seconds"
            )
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass
    conn.commit()


def _maybe_vacuum(threshold_mb: int = 5):
    """VACUUM reclaims free pages; only worth it once the DB is large."""
    try:
        if DB_PATH.exists() and DB_PATH.stat().st_size > threshold_mb * 1024 * 1024:
            with _connect() as conn:
                conn.execute("VACUUM")
    except sqlite3.OperationalError:
        pass


def db_health() -> bool:
    """Lightweight writable connectivity check for health endpoints."""
    try:
        with _connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def record_feedback(vuln_type: str, outcome: str, user_id: str = "", display_name: str = "",
                    repo_id: int | None = None, pr_number: int | None = None,
                    scan_id: int | None = None):
    """Record developer feedback (ACCEPTED/REJECTED) with optional user attribution.

    When user_id is provided, enforces one vote per user per vuln type (upsert).
    Optional repo_id/pr_number/scan_id attach the vote to a specific scan context
    so per-repository and per-PR feedback can be surfaced in the UI.
    """
    with _connect() as conn:
        if user_id:
            conn.execute("""
                INSERT OR REPLACE INTO patch_feedback (vuln_type, outcome, user_id, display_name, repo_id, pr_number, scan_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (vuln_type, outcome, user_id, display_name, repo_id, pr_number, scan_id))
        else:
            conn.execute(
                "INSERT INTO patch_feedback (vuln_type, outcome, repo_id, pr_number, scan_id) VALUES (?, ?, ?, ?, ?)",
                (vuln_type, outcome, repo_id, pr_number, scan_id)
            )
        conn.commit()


def get_feedback_stats(vuln_type: str) -> dict:
    """Get historical success rate for a vulnerability type."""
    with _connect() as conn:
        row = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'ACCEPTED' THEN 1 ELSE 0 END) as accepted
            FROM patch_feedback 
            WHERE vuln_type = ?
        """, (vuln_type,)).fetchone()

    return {
        "total": row["total"] or 0,
        "accepted": row["accepted"] or 0
    }


def get_feedback_records(vuln_type: str) -> list[dict]:
    """Get all feedback records for a vulnerability type with timestamps."""
    with _connect() as conn:
        rows = conn.execute("""
            SELECT outcome, timestamp FROM patch_feedback
            WHERE vuln_type = ?
            ORDER BY timestamp ASC
        """, (vuln_type,)).fetchall()
    return [dict(r) for r in rows]


def record_pr_finding(pr_number: int, vuln_type: str):
    """Record a vulnerability found in a PR (for automated feedback)."""
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO pr_findings (pr_number, vuln_type) VALUES (?, ?)",
            (pr_number, vuln_type)
        )
        conn.commit()


def get_pr_findings(pr_number: int) -> list:
    """Get all vulnerability types found in a specific PR."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT vuln_type FROM pr_findings WHERE pr_number = ?",
            (pr_number,)
        ).fetchall()
    return [row["vuln_type"] for row in rows]


def record_bot_comment(comment_id: int, repo: str, pr_number: int):
    """Upsert a bot PR comment so the reaction poller can find it later."""
    with _connect() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO bot_comments (comment_id, repo, pr_number)
            VALUES (?, ?, ?)
        """, (comment_id, repo, pr_number))
        conn.commit()


def get_pollable_bot_comments(limit: int = 50) -> list[dict]:
    """Return the most recently posted bot comments to check for reactions."""
    with _connect() as conn:
        rows = conn.execute("""
            SELECT comment_id, repo, pr_number
            FROM bot_comments
            ORDER BY posted_at DESC, comment_id DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_install_id_for_repo(repo_full_name: str) -> int | None:
    """Resolve the installation id owning a repository (for token retrieval)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT install_id FROM repos WHERE full_name = ? LIMIT 1",
            (repo_full_name,)
        ).fetchone()
    return row["install_id"] if row else None


def reaction_processed(reaction_id: int) -> bool:
    """Return True when the reaction has already been harvested."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_reactions WHERE reaction_id = ?",
            (reaction_id,)
        ).fetchone()
    return row is not None


def mark_reaction_processed(reaction_id: int, comment_id: int, user_id: str, content: str):
    """Persist a harvested reaction so it is not processed again."""
    with _connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO processed_reactions (reaction_id, comment_id, user_id, content)
            VALUES (?, ?, ?, ?)
        """, (reaction_id, comment_id, user_id, content))
        conn.commit()


def increment_dashboard(total_vulns: int, risk_level: str):
    """
    Atomically increment counters after processing one PR.
    risk_level must be 'LOW', 'MEDIUM', or 'HIGH'.
    """
    if risk_level not in ("LOW", "MEDIUM", "HIGH"):
        risk_level = "MEDIUM"

    with _connect() as conn:
        conn.execute(
            "UPDATE dashboard SET value = value + 1 WHERE key = 'total_prs'"
        )
        conn.execute(
            "UPDATE dashboard SET value = value + ? WHERE key = 'total_vulnerabilities'",
            (total_vulns,)
        )
        conn.execute(
            "UPDATE dashboard SET value = value + 1 WHERE key = ?",
            (f"risk_{risk_level}",)
        )
        conn.commit()


def get_dashboard(github_id: int | None = None) -> dict:
    """Return dashboard stats as a plain dict.

    When github_id is None the legacy global counters are returned (kept for
    backward compatibility). When github_id is provided the stats are computed
    per-user from that user's repos/scans/findings.
    """
    if github_id is not None:
        return _get_dashboard_per_user(github_id)

    with _connect() as conn:
        rows = conn.execute("SELECT key, value FROM dashboard").fetchall()

        data = {row["key"]: row["value"] for row in rows}

        trends = conn.execute("""
            SELECT date(timestamp) as day, COUNT(*) as count
            FROM patch_feedback
            GROUP BY day
            ORDER BY day DESC LIMIT 7
        """).fetchall()

        rows = conn.execute("""
            SELECT vuln_type, outcome, COUNT(*) as count, COUNT(DISTINCT user_id) as unique_users
            FROM patch_feedback
            WHERE outcome IN ('ACCEPTED', 'REJECTED')
            GROUP BY vuln_type, outcome
        """).fetchall()

    performance = _restructure_performance(rows)

    total_vulns = data.get("total_vulnerabilities", 0)
    risk_low = data.get("risk_LOW", 0)
    risk_med = data.get("risk_MEDIUM", 0)
    risk_high = data.get("risk_HIGH", 0)

    # Compute average risk score from severity midpoints
    avg_risk_score = 0.0
    if total_vulns > 0:
        total_weight = risk_low * 2.0 + risk_med * 5.0 + risk_high * 8.0
        avg_risk_score = round(total_weight / total_vulns, 1)

    # Compute remediation rate from patch_feedback
    remediation_rate = _remediation_rate(performance)

    # Compute cache hit rate
    cache_hits = data.get("cache_hits", 0)
    cache_misses = data.get("cache_misses", 0)
    cache_hit_rate = 0.0
    total_cache = cache_hits + cache_misses
    if total_cache > 0:
        cache_hit_rate = round(cache_hits / total_cache * 100, 1)

    repos = get_dashboard_repos()

    return {
        "total_prs":             data.get("total_prs", 0),
        "total_vulnerabilities": total_vulns,
        "risk_levels": {
            "LOW":    risk_low,
            "MEDIUM": risk_med,
            "HIGH":   risk_high,
        },
        "avg_risk_score":    avg_risk_score,
        "remediation_rate":  remediation_rate,
        "cache_hit_rate":    cache_hit_rate,
        "trends": [{"day": t["day"], "count": t["count"]} for t in trends],
        "performance": performance,
        "repos": repos,
    }


def _restructure_performance(rows) -> list:
    """Convert (vuln_type, outcome, count, unique_users) rows into per-type stats."""
    perf_map: dict[str, dict] = {}
    for r in rows:
        vt = r["vuln_type"]
        if vt not in perf_map:
            perf_map[vt] = {"type": vt, "accepted_count": 0, "accepted_users": 0,
                            "rejected_count": 0, "rejected_users": 0}
        if r["outcome"] == "ACCEPTED":
            perf_map[vt]["accepted_count"] = r["count"]
            perf_map[vt]["accepted_users"] = r["unique_users"]
        elif r["outcome"] == "REJECTED":
            perf_map[vt]["rejected_count"] = r["count"]
            perf_map[vt]["rejected_users"] = r["unique_users"]
    return list(perf_map.values())


def _remediation_rate(performance: list) -> float:
    total_accepted = sum(p["accepted_count"] for p in performance)
    total_rejected = sum(p["rejected_count"] for p in performance)
    total_feedback = total_accepted + total_rejected
    if total_feedback > 0:
        return round(total_accepted / total_feedback * 100, 1)
    return 0.0


def _get_dashboard_per_user(github_id: int) -> dict:
    """Compute dashboard stats scoped to a single user's installations.

    Re-scans of the same PR are collapsed to their LATEST scan per (repo, pr)
    so aggregates reflect the current state instead of being multiplied by every
    re-scan. Per-scan detail is preserved by ``get_repo_scans``. One feedback
    vote per PR per vuln-type (latest wins) is used for performance/remediation.
    """
    with _connect() as conn:
        totals = conn.execute("""
            SELECT COUNT(DISTINCT s.repo_id || ':' || s.pr_number) AS total_prs,
                   COALESCE(SUM(s.findings_count), 0) AS total_vulnerabilities
            FROM scans s
            JOIN repos r ON s.repo_id = r.id
            JOIN user_installations ui
              ON ui.install_id = r.install_id AND ui.github_id = ?
            WHERE s.id IN (SELECT MAX(id) FROM scans GROUP BY repo_id, pr_number)
        """, (github_id,)).fetchone()

        sev_rows = conn.execute("""
            SELECT f.severity, COUNT(*) AS c
            FROM findings f
            JOIN scans s ON f.scan_id = s.id
            JOIN repos r ON s.repo_id = r.id
            JOIN user_installations ui
              ON ui.install_id = r.install_id AND ui.github_id = ?
            WHERE f.status = 'open'
              AND f.scan_id IN (SELECT MAX(id) FROM scans GROUP BY repo_id, pr_number)
            GROUP BY f.severity
        """, (github_id,)).fetchall()

        avg_row = conn.execute("""
            SELECT AVG(f.risk_score) AS avg_risk
            FROM findings f
            JOIN scans s ON f.scan_id = s.id
            JOIN repos r ON s.repo_id = r.id
            JOIN user_installations ui
              ON ui.install_id = r.install_id AND ui.github_id = ?
            WHERE f.status = 'open'
              AND f.scan_id IN (SELECT MAX(id) FROM scans GROUP BY repo_id, pr_number)
        """, (github_id,)).fetchone()

        trends = conn.execute("""
            SELECT date(s.scanned_at) as day,
                   COUNT(DISTINCT s.repo_id || ':' || s.pr_number) as count
            FROM scans s
            JOIN repos r ON s.repo_id = r.id
            JOIN user_installations ui
              ON ui.install_id = r.install_id AND ui.github_id = ?
            GROUP BY day
            ORDER BY day DESC LIMIT 7
        """, (github_id,)).fetchall()

        feedback_rows = conn.execute("""
            WITH ranked AS (
                SELECT p.vuln_type, p.outcome, p.user_id,
                       ROW_NUMBER() OVER (
                           PARTITION BY COALESCE(p.repo_id, 0), COALESCE(p.pr_number, 0), p.vuln_type
                           ORDER BY p.timestamp DESC, p.id DESC
                       ) AS rn
                FROM patch_feedback p
                JOIN users u ON u.login = p.user_id AND u.github_id = ?
                WHERE p.outcome IN ('ACCEPTED', 'REJECTED')
            )
            SELECT vuln_type, outcome, COUNT(*) AS count,
                   COUNT(DISTINCT user_id) AS unique_users
            FROM ranked WHERE rn = 1
            GROUP BY vuln_type, outcome
        """, (github_id,)).fetchall()

        cache_row = conn.execute(
            "SELECT value FROM dashboard WHERE key = 'cache_hits'"
        ).fetchone()
        cache_miss_row = conn.execute(
            "SELECT value FROM dashboard WHERE key = 'cache_misses'"
        ).fetchone()

        attention = conn.execute("""
            SELECT f.id, f.vuln_type, f.severity, f.risk_score, f.file_path,
                   s.pr_number, s.pr_title, r.id AS repo_id, r.full_name AS repo_full_name,
                   s.id AS scan_id
            FROM findings f
            JOIN scans s ON f.scan_id = s.id
            JOIN repos r ON s.repo_id = r.id
            JOIN user_installations ui
              ON ui.install_id = r.install_id AND ui.github_id = ?
            WHERE f.status = 'open' AND f.severity = 'HIGH'
              AND f.scan_id IN (SELECT MAX(id) FROM scans GROUP BY repo_id, pr_number)
            ORDER BY f.risk_score DESC
            LIMIT 10
        """, (github_id,)).fetchall()

        scans_7d_row = conn.execute("""
            SELECT COUNT(DISTINCT s.repo_id || ':' || s.pr_number) AS c
            FROM scans s
            JOIN repos r ON s.repo_id = r.id
            JOIN user_installations ui
              ON ui.install_id = r.install_id AND ui.github_id = ?
            WHERE date(s.scanned_at) >= date('now', '-7 days')
        """, (github_id,)).fetchone()
        new_7d_row = conn.execute("""
            SELECT COUNT(*) AS c
            FROM findings f
            JOIN scans s ON f.scan_id = s.id
            JOIN repos r ON s.repo_id = r.id
            JOIN user_installations ui
              ON ui.install_id = r.install_id AND ui.github_id = ?
            WHERE f.status = 'open'
              AND date(f.created_at) >= date('now', '-7 days')
              AND f.scan_id IN (SELECT MAX(id) FROM scans GROUP BY repo_id, pr_number)
        """, (github_id,)).fetchone()

    risk_low = risk_med = risk_high = 0
    for r in sev_rows:
        if r["severity"] == "HIGH":
            risk_high = r["c"]
        elif r["severity"] == "MEDIUM":
            risk_med = r["c"]
        else:
            risk_low = r["c"]

    performance = _restructure_performance(feedback_rows)

    cache_hits = (cache_row["value"] if cache_row else 0) or 0
    cache_misses = (cache_miss_row["value"] if cache_miss_row else 0) or 0
    total_cache = cache_hits + cache_misses
    cache_hit_rate = round(cache_hits / total_cache * 100, 1) if total_cache > 0 else 0.0

    week_summary = {
        "scans_7d": (scans_7d_row["c"] if scans_7d_row else 0) or 0,
        "new_7d": (new_7d_row["c"] if new_7d_row else 0) or 0,
        "open_now": risk_low + risk_med + risk_high,
    }

    return {
        "total_prs":             totals["total_prs"] or 0,
        "total_vulnerabilities": totals["total_vulnerabilities"] or 0,
        "risk_levels": {
            "LOW":    risk_low,
            "MEDIUM": risk_med,
            "HIGH":   risk_high,
        },
        "avg_risk_score":    round(avg_row["avg_risk"] or 0.0, 1),
        "remediation_rate":  _remediation_rate(performance),
        "cache_hit_rate":    cache_hit_rate,
        "trends": [{"day": t["day"], "count": t["count"]} for t in trends],
        "performance": performance,
        "attention": [dict(a) for a in attention],
        "week_summary": week_summary,
        "repos": get_dashboard_repos(github_id),
    }


def upsert_user(github_id: int, login: str, name: str, avatar_url: str):
    with _connect() as conn:
        conn.execute("""
            INSERT INTO users (github_id, login, name, avatar_url)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(github_id) DO UPDATE SET
                login = excluded.login,
                name = excluded.name,
                avatar_url = excluded.avatar_url
        """, (github_id, login, name, avatar_url))
        conn.commit()


def get_user(github_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT github_id, login, name, avatar_url FROM users WHERE github_id = ?",
            (github_id,)
        ).fetchone()
    return dict(row) if row else None


def sync_user_installations(github_id: int, installations: list[dict]):
    """Replace the install->user mapping for a user with the latest from GitHub.

    Call after a successful OAuth login so webhook scans on the user's
    installations can be attributed to them. Each installation is an account
    (a user or an organisation) the authenticated user can access.
    """
    with _connect() as conn:
        conn.execute("DELETE FROM user_installations WHERE github_id = ?", (github_id,))
        for inst in installations:
            inst_id = inst.get("id")
            if not inst_id:
                continue
            account = inst.get("account") or {}
            conn.execute("""
                INSERT INTO user_installations (github_id, install_id, account_type, account_login)
                VALUES (?, ?, ?, ?)
            """, (github_id, inst_id, account.get("type", "User"), account.get("login", "")))
        conn.commit()


def resolve_scan_user(install_id: int, owner_login: str) -> int | None:
    """Resolve the github_id a scan/repo should be attributed to.

    Priority:
      1. The mapped user whose installation account login matches the repo owner
         (handles user-level installs deterministically).
      2. The single mapped user for that installation (org installs).
      3. Fallback: a users row whose login matches the repo owner.
    Returns None when no user can be resolved (visibility still works via the
    install mapping, so the owning user will see the data after they log in).
    """
    if install_id:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT github_id, account_login FROM user_installations "
                "WHERE install_id = ? ORDER BY synced_at DESC",
                (install_id,),
            ).fetchall()
        if rows:
            owner = (owner_login or "").lower()
            for r in rows:
                if r["account_login"] and r["account_login"].lower() == owner:
                    return r["github_id"]
            if len(rows) == 1:
                return rows[0]["github_id"]
            return None
    if owner_login:
        with _connect() as conn:
            row = conn.execute(
                "SELECT github_id FROM users WHERE lower(login) = lower(?) LIMIT 1",
                (owner_login,),
            ).fetchone()
        return row["github_id"] if row else None
    return None


def upsert_repo(repo_data: dict):
    repo_data = dict(repo_data)
    user_id = resolve_scan_user(
        repo_data.get("install_id") or 0,
        repo_data.get("owner") or "",
    )
    repo_data["user_id"] = user_id
    with _connect() as conn:
        conn.execute("""
            INSERT INTO repos (id, full_name, owner, name, description, language, private, default_branch, install_id, user_id, first_seen_at, last_scanned_at, codeql_provisioned)
            VALUES (:id, :full_name, :owner, :name, :description, :language, :private, :default_branch, :install_id, :user_id, datetime('now'), datetime('now'), 0)
            ON CONFLICT(id) DO UPDATE SET
                full_name = excluded.full_name,
                owner = excluded.owner,
                name = excluded.name,
                description = excluded.description,
                language = excluded.language,
                private = excluded.private,
                default_branch = excluded.default_branch,
                install_id = excluded.install_id,
                user_id = COALESCE(repos.user_id, excluded.user_id),
                last_scanned_at = datetime('now'),
                codeql_provisioned = COALESCE(repos.codeql_provisioned, excluded.codeql_provisioned)
        """, repo_data)
        conn.commit()


def is_repo_codeql_provisioned(full_name: str) -> bool:
    """Check if a repo has already been provisioned for CodeQL analysis.

    Returns True if the repo has codeql_provisioned=1 in the database,
    indicating the setup PR has been created and merged.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT codeql_provisioned FROM repos WHERE full_name = ?",
            (full_name,),
        ).fetchone()
        return row is not None and row[0] == 1


def mark_repo_codeql_provisioned(full_name: str):
    """Mark a repo as CodeQL-provisioned after a setup PR was opened."""
    with _connect() as conn:
        conn.execute(
            "UPDATE repos SET codeql_provisioned = 1 WHERE full_name = ?",
            (full_name,),
        )
        conn.commit()


def clear_codeql_provisioned(full_name: str):
    """Clear the provisioned flag (e.g. for re-provisioning after config change)."""
    with _connect() as conn:
        conn.execute(
            "UPDATE repos SET codeql_provisioned = 0 WHERE full_name = ?",
            (full_name,),
        )
        conn.commit()


def delete_repos_by_install(install_id: int):
    """Remove all repos belonging to an uninstalled GitHub App installation."""
    with _connect() as conn:
        conn.execute("DELETE FROM repos WHERE install_id = ?", (install_id,))
        conn.commit()


def delete_repo_by_full_name(full_name: str):
    """Remove a single repo (e.g. when it is removed from an installation)."""
    with _connect() as conn:
        conn.execute("DELETE FROM repos WHERE full_name = ?", (full_name,))
        conn.commit()


def get_repos(github_id: int | None = None) -> list:
    with _connect() as conn:
        if github_id is None:
            rows = conn.execute("""
                SELECT r.*,
                    COALESCE(s.scan_count, 0) AS total_scans,
                    COALESCE(s.last_scan, '') AS last_scan_at
                FROM repos r
                LEFT JOIN (
                    SELECT repo_id,
                        COUNT(*) AS scan_count,
                        MAX(scanned_at) AS last_scan
                    FROM scans
                    GROUP BY repo_id
                ) s ON r.id = s.repo_id
                ORDER BY COALESCE(s.last_scan, r.last_scanned_at) DESC
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT r.*,
                    COALESCE(s.scan_count, 0) AS total_scans,
                    COALESCE(s.last_scan, '') AS last_scan_at
                FROM repos r
                JOIN user_installations ui
                  ON ui.install_id = r.install_id AND ui.github_id = ?
                LEFT JOIN (
                    SELECT repo_id,
                        COUNT(*) AS scan_count,
                        MAX(scanned_at) AS last_scan
                    FROM scans
                    GROUP BY repo_id
                ) s ON r.id = s.repo_id
                ORDER BY COALESCE(s.last_scan, r.last_scanned_at) DESC
            """, (github_id,)).fetchall()
    return [dict(r) for r in rows]


def get_repo(repo_id: int, github_id: int | None = None) -> dict | None:
    with _connect() as conn:
        if github_id is None:
            row = conn.execute("""
                SELECT r.*,
                    COUNT(DISTINCT s.id) AS total_scans,
                    COALESCE(MAX(s.scanned_at), '') AS last_scan_at,
                    COALESCE(SUM(CASE WHEN f.status = 'open' THEN 1 ELSE 0 END), 0) AS open_findings
                FROM repos r
                LEFT JOIN scans s ON s.repo_id = r.id
                LEFT JOIN findings f ON f.scan_id = s.id
                WHERE r.id = ?
                GROUP BY r.id
            """, (repo_id,)).fetchone()
        else:
            row = conn.execute("""
                SELECT r.*,
                    COUNT(DISTINCT s.id) AS total_scans,
                    COALESCE(MAX(s.scanned_at), '') AS last_scan_at,
                    COALESCE(SUM(CASE WHEN f.status = 'open' THEN 1 ELSE 0 END), 0) AS open_findings
                FROM repos r
                JOIN user_installations ui
                  ON ui.install_id = r.install_id AND ui.github_id = ?
                LEFT JOIN scans s ON s.repo_id = r.id
                LEFT JOIN findings f ON f.scan_id = s.id
                WHERE r.id = ?
                GROUP BY r.id
            """, (github_id, repo_id)).fetchone()
    return dict(row) if row else None


def record_scan(repo_id: int, pr_number: int, pr_title: str, branch: str,
                commit_sha: str, findings_count: int, max_risk: float,
                duration_ms: int) -> int:
    with _connect() as conn:
        repo = conn.execute("SELECT user_id FROM repos WHERE id = ?", (repo_id,)).fetchone()
        user_id = repo["user_id"] if repo else None
        cur = conn.execute("""
            INSERT INTO scans (repo_id, pr_number, pr_title, branch, commit_sha,
                               findings_count, max_risk, duration_ms, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (repo_id, pr_number, pr_title, branch, commit_sha,
              findings_count, max_risk, duration_ms, user_id))
        scan_id = cur.lastrowid
        assert scan_id is not None
        conn.execute(
            "UPDATE repos SET last_scanned_at = datetime('now') WHERE id = ?",
            (repo_id,)
        )
        conn.commit()
    return scan_id


def mark_scan_validation_pending(scan_id: int):
    """Mark a scan as awaiting re-validation (Docker was unavailable during it)."""
    with _connect() as conn:
        conn.execute(
            "UPDATE scans SET validation_status = 'pending' WHERE id = ?",
            (scan_id,),
        )
        conn.commit()


def mark_scan_validated(scan_id: int):
    """Mark a scan as fully validated (Docker re-validation completed)."""
    with _connect() as conn:
        conn.execute(
            "UPDATE scans SET validation_status = 'ok' WHERE id = ?",
            (scan_id,),
        )
        conn.commit()


def get_pending_validation_scans(limit: int = 10) -> list:
    """Return scans awaiting re-validation, oldest first, joined with repo info."""
    with _connect() as conn:
        rows = conn.execute("""
            SELECT s.id, s.repo_id, s.pr_number, s.pr_title, s.branch, s.commit_sha,
                   s.status, s.validation_status, s.scanned_at,
                   r.full_name AS repo_full_name, r.install_id
            FROM scans s
            JOIN repos r ON s.repo_id = r.id
            WHERE s.validation_status = 'pending'
            ORDER BY s.scanned_at ASC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_pending_scans_for_commit(repo_full_name: str, commit_sha: str, limit: int = 5) -> list:
    """Return pending-validation scans for a specific commit (CI results arrived)."""
    with _connect() as conn:
        rows = conn.execute("""
            SELECT s.id, s.repo_id, s.pr_number, s.pr_title, s.branch, s.commit_sha,
                   s.status, s.validation_status, s.scanned_at,
                   r.full_name AS repo_full_name, r.install_id
            FROM scans s
            JOIN repos r ON s.repo_id = r.id
            WHERE s.validation_status = 'pending' AND s.commit_sha = ? AND r.full_name = ?
            ORDER BY s.scanned_at ASC
            LIMIT ?
        """, (commit_sha, repo_full_name, limit)).fetchall()
    return [dict(r) for r in rows]


def record_pending_validation(
    repo_full_name: str,
    pr_number: int,
    commit_sha: str,
    source_filename: str,
    candidate_id: str,
    patched_code: str,
    test_filename: str = "",
    test_content: str = "",
    extra_files: list | None = None,
    scan_mode: str = "",
    sandbox_network: str = "",
) -> int:
    """Persist a candidate awaiting CI-runner validation (idempotent).

    The UNIQUE key on (repo_full_name, commit_sha, source_filename,
    candidate_id) means repeated failed-closed captures of the same candidate
    never create duplicates. Returns the row id.
    """
    with _connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO pending_validations (
                repo_full_name, pr_number, commit_sha, source_filename, candidate_id,
                patched_code, test_filename, test_content, extra_files, scan_mode, sandbox_network
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            repo_full_name, pr_number, commit_sha, source_filename, candidate_id,
            patched_code, test_filename, test_content,
            json.dumps(extra_files or [], ensure_ascii=False),
            scan_mode, sandbox_network,
        ))
        conn.commit()
        row = conn.execute("""
            SELECT id FROM pending_validations
            WHERE repo_full_name = ? AND commit_sha = ? AND source_filename = ? AND candidate_id = ?
        """, (repo_full_name, commit_sha, source_filename, candidate_id)).fetchone()
    return int(row["id"]) if row else 0


def get_pending_validation(job_id: int) -> dict | None:
    """Return a single pending-validation job row."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM pending_validations WHERE id = ?", (job_id,)
        ).fetchone()
    return dict(row) if row else None


def get_pending_validations_for_commit(
    repo_full_name: str, commit_sha: str, statuses: list[str] | None = None
) -> list:
    """Return pending-validation jobs for a commit, optionally filtered by status."""
    with _connect() as conn:
        sql = "SELECT * FROM pending_validations WHERE repo_full_name = ? AND commit_sha = ?"
        params: list = [repo_full_name, commit_sha]
        if statuses:
            placeholders = ",".join("?" * len(statuses))
            sql += f" AND status IN ({placeholders})"
            params.extend(statuses)
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def update_pending_validation_status(job_id: int, status: str):
    """Update a pending-validation job's status (pending/dispatched/running/...)."""
    with _connect() as conn:
        conn.execute(
            "UPDATE pending_validations SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, job_id),
        )
        conn.commit()


def complete_pending_validation(job_id: int, result_json: str, status: str = "completed"):
    """Store a CI-runner validation result and mark the job completed."""
    with _connect() as conn:
        conn.execute(
            "UPDATE pending_validations SET status = ?, result_json = ?, updated_at = datetime('now') WHERE id = ?",
            (status, result_json, job_id),
        )
        conn.commit()


def count_ci_results_available(repo_full_name: str, commit_sha: str) -> int:
    """Count completed CI validations for a commit (runtime evidence exists)."""
    with _connect() as conn:
        row = conn.execute("""
            SELECT COUNT(*) AS n FROM pending_validations
            WHERE repo_full_name = ? AND commit_sha = ? AND status = 'completed'
        """, (repo_full_name, commit_sha)).fetchone()
    return int(row["n"]) if row else 0


def has_inflight_ci_validation(repo_full_name: str, commit_sha: str) -> bool:
    """Return True when CI validation jobs are queued or in flight for a commit."""
    with _connect() as conn:
        row = conn.execute("""
            SELECT 1 FROM pending_validations
            WHERE repo_full_name = ? AND commit_sha = ? AND status IN ('pending', 'dispatched', 'running')
            LIMIT 1
        """, (repo_full_name, commit_sha)).fetchone()
    return row is not None


def get_ci_result(
    repo_full_name: str, commit_sha: str, source_filename: str, candidate_id: str
) -> dict | None:
    """Return a completed CI validation job row for a candidate, or None."""
    with _connect() as conn:
        row = conn.execute("""
            SELECT * FROM pending_validations
            WHERE repo_full_name = ? AND commit_sha = ? AND source_filename = ? AND candidate_id = ?
              AND status = 'completed'
        """, (repo_full_name, commit_sha, source_filename, candidate_id)).fetchone()
    return dict(row) if row else None


def get_scan(scan_id: int, github_id: int | None = None) -> dict | None:
    """Return a single scan record by ID, joined with repo info.

    When github_id is provided the scan must belong to a repo in that user's
    installations, otherwise None is returned (hidden from other users).
    """
    with _connect() as conn:
        if github_id is None:
            row = conn.execute("""
                SELECT s.*, r.full_name AS repo_full_name, r.owner AS repo_owner,
                       r.name AS repo_name, r.install_id AS install_id
                FROM scans s
                JOIN repos r ON s.repo_id = r.id
                WHERE s.id = ?
            """, (scan_id,)).fetchone()
        else:
            row = conn.execute("""
                SELECT s.*, r.full_name AS repo_full_name, r.owner AS repo_owner,
                       r.name AS repo_name, r.install_id AS install_id
                FROM scans s
                JOIN repos r ON s.repo_id = r.id
                JOIN user_installations ui
                  ON ui.install_id = r.install_id AND ui.github_id = ?
                WHERE s.id = ?
            """, (github_id, scan_id)).fetchone()
    return dict(row) if row else None


def get_scan_findings(scan_id: int, github_id: int | None = None) -> list:
    """Return all findings for a specific scan ID, ordered by risk.

    When github_id is provided, findings are only returned for scans the user
    can access (scan must belong to one of their installations).
    """
    with _connect() as conn:
        if github_id is None:
            rows = conn.execute("""
                SELECT id, vuln_type, severity, risk_score, file_path, line_number, is_new, status, created_at
                FROM findings
                WHERE scan_id = ?
                ORDER BY risk_score DESC
            """, (scan_id,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT f.id, f.vuln_type, f.severity, f.risk_score, f.file_path, f.line_number, f.is_new, f.status, f.created_at
                FROM findings f
                JOIN scans s ON f.scan_id = s.id
                JOIN repos r ON s.repo_id = r.id
                JOIN user_installations ui
                  ON ui.install_id = r.install_id AND ui.github_id = ?
                WHERE f.scan_id = ?
                ORDER BY f.risk_score DESC
            """, (github_id, scan_id)).fetchall()
    return [dict(r) for r in rows]


def get_repo_scans(repo_id: int, github_id: int | None = None) -> list:
    def _rows(rows):
        out = []
        for r in rows:
            d = dict(r)
            d["is_latest"] = 1 if d.get("revision_number") == 1 else 0
            out.append(d)
        return out
    with _connect() as conn:
        if github_id is None:
            rows = conn.execute("""
                SELECT id, pr_number, pr_title, branch, commit_sha, status,
                       validation_status,
                       findings_count, max_risk, duration_ms, scanned_at,
                       ROW_NUMBER() OVER (
                           PARTITION BY repo_id, pr_number
                           ORDER BY scanned_at DESC, id DESC
                       ) AS revision_number
                FROM scans
                WHERE repo_id = ?
                ORDER BY scanned_at DESC
                LIMIT 50
            """, (repo_id,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT s.id, s.pr_number, s.pr_title, s.branch, s.commit_sha, s.status,
                       s.validation_status,
                       s.findings_count, s.max_risk, s.duration_ms, s.scanned_at,
                       ROW_NUMBER() OVER (
                           PARTITION BY s.repo_id, s.pr_number
                           ORDER BY s.scanned_at DESC, s.id DESC
                       ) AS revision_number
                FROM scans s
                JOIN repos r ON s.repo_id = r.id
                JOIN user_installations ui
                  ON ui.install_id = r.install_id AND ui.github_id = ?
                WHERE s.repo_id = ?
                ORDER BY s.scanned_at DESC
                LIMIT 50
            """, (github_id, repo_id)).fetchall()
    return _rows(rows)


def get_previous_scan_summary(full_name: str, exclude_pr: int | None = None) -> dict | None:
    """Return the most recent completed scan summary for a repository.

    Used for the "Repository Trend" section of the PR comment. Optionally
    excludes a PR number so a re-run of the same PR is not compared to itself.
    """
    with _connect() as conn:
        row = conn.execute("""
            SELECT s.findings_count, s.max_risk, s.scanned_at
            FROM scans s
            JOIN repos r ON r.id = s.repo_id
            WHERE r.full_name = ? AND (? IS NULL OR s.pr_number != ?)
            ORDER BY s.scanned_at DESC
            LIMIT 1
        """, (full_name, exclude_pr, exclude_pr)).fetchone()
    return dict(row) if row else None


def record_finding(scan_id: int, vuln_type: str, severity: str,
                   risk_score: float, file_path: str, line_number: int,
                   is_new: int = 0):
    with _connect() as conn:
        conn.execute("""
            INSERT INTO findings (scan_id, vuln_type, severity, risk_score,
                                  file_path, line_number, is_new)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (scan_id, vuln_type, severity, risk_score, file_path, line_number, is_new))
        conn.commit()


def update_finding_status(finding_id: int, status: str) -> None:
    """Update the workflow status of a finding (e.g. resolved, dismissed)."""
    with _connect() as conn:
        conn.execute(
            "UPDATE findings SET status = ? WHERE id = ?",
            (status, finding_id),
        )
        conn.commit()


def finding_belongs_to_user(finding_id: int, github_id: int) -> bool:
    """Return True when the finding belongs to one of the user's installations.

    Scopes a finding through findings -> scans -> repos -> user_installations so
    status mutations (and any future per-finding operations) cannot cross
    tenant boundaries.
    """
    with _connect() as conn:
        row = conn.execute("""
            SELECT f.id
            FROM findings f
            JOIN scans s ON s.id = f.scan_id
            JOIN repos r ON s.repo_id = r.id
            JOIN user_installations ui
              ON ui.install_id = r.install_id AND ui.github_id = ?
            WHERE f.id = ?
        """, (github_id, finding_id)).fetchone()
    return row is not None


def resolve_open_findings_for_pr(pr_number: int) -> int:
    """Mark open findings for a PR as resolved (e.g. when it merges)."""
    with _connect() as conn:
        cur = conn.execute("""
            UPDATE findings
            SET status = 'resolved'
            WHERE status = 'open'
              AND scan_id IN (SELECT id FROM scans WHERE pr_number = ?)
        """, (pr_number,))
        conn.commit()
        return cur.rowcount


def get_repo_findings(repo_id: int, github_id: int | None = None) -> list:
    with _connect() as conn:
        if github_id is None:
            rows = conn.execute("""
                SELECT f.id, f.vuln_type, f.severity, f.risk_score,
                       f.file_path, f.line_number, f.status, f.created_at,
                       s.pr_number, s.pr_title, s.scanned_at, s.id AS scan_id
                FROM findings f
                JOIN scans s ON f.scan_id = s.id
                WHERE s.repo_id = ? AND f.status = 'open'
                  AND f.scan_id IN (SELECT MAX(id) FROM scans WHERE repo_id = ? GROUP BY repo_id, pr_number)
                ORDER BY f.risk_score DESC
                LIMIT 200
            """, (repo_id, repo_id)).fetchall()
        else:
            rows = conn.execute("""
                SELECT f.id, f.vuln_type, f.severity, f.risk_score,
                       f.file_path, f.line_number, f.status, f.created_at,
                       s.pr_number, s.pr_title, s.scanned_at, s.id AS scan_id
                FROM findings f
                JOIN scans s ON f.scan_id = s.id
                JOIN repos r ON s.repo_id = r.id
                JOIN user_installations ui
                  ON ui.install_id = r.install_id AND ui.github_id = ?
                WHERE s.repo_id = ? AND f.status = 'open'
                  AND f.scan_id IN (SELECT MAX(id) FROM scans WHERE repo_id = ? GROUP BY repo_id, pr_number)
                ORDER BY f.risk_score DESC
                LIMIT 200
            """, (github_id, repo_id, repo_id)).fetchall()
    return [dict(r) for r in rows]


def get_all_findings(github_id: int, repo_id: int | None = None,
                     severity: str | None = None, vuln_type: str | None = None,
                     status: str | None = None, q: str | None = None,
                     limit: int = 200) -> list:
    """Findings across all of the user's repos, filtered and latest-scan deduped.

    The same PR re-scanned multiple times only contributes the latest scan's
    findings, matching the dashboard and per-repo aggregates.
    """
    where = ["ui.github_id = ?"]
    params: list = [github_id]
    if repo_id is not None:
        where.append("r.id = ?")
        params.append(repo_id)
    if severity:
        where.append("UPPER(f.severity) = ?")
        params.append(severity.upper())
    if vuln_type:
        where.append("f.vuln_type = ?")
        params.append(vuln_type)
    if status:
        where.append("f.status = ?")
        params.append(status)
    if q:
        where.append("(f.vuln_type LIKE ? OR f.file_path LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])
    where_sql = " AND ".join(where)
    params.append(limit)

    with _connect() as conn:
        rows = conn.execute(f"""
            SELECT f.id, f.vuln_type, f.severity, f.risk_score,
                   f.file_path, f.line_number, f.status, f.created_at,
                   f.scan_id, s.pr_number, s.pr_title,
                   r.id AS repo_id, r.full_name AS repo_full_name
            FROM findings f
            JOIN scans s ON f.scan_id = s.id
            JOIN repos r ON s.repo_id = r.id
            JOIN user_installations ui ON ui.install_id = r.install_id
            WHERE f.scan_id IN (SELECT MAX(id) FROM scans GROUP BY repo_id, pr_number)
              AND {where_sql}
            ORDER BY f.risk_score DESC
            LIMIT ?
        """, params)
    return [dict(r) for r in rows]


def get_all_scans(github_id: int, repo_id: int | None = None,
                  status: str | None = None, limit: int = 200) -> list:
    """Scans across all of the user's repos, most recent first."""
    where = ["ui.github_id = ?"]
    params: list = [github_id]
    if repo_id is not None:
        where.append("r.id = ?")
        params.append(repo_id)
    if status:
        where.append("s.status = ?")
        params.append(status)
    where_sql = " AND ".join(where)
    params.append(limit)

    with _connect() as conn:
        rows = conn.execute(f"""
            SELECT s.id, s.pr_number, s.pr_title, s.branch, s.commit_sha,
                   s.status, s.findings_count, s.max_risk, s.duration_ms,
                   s.scanned_at, r.id AS repo_id, r.full_name AS repo_full_name
            FROM scans s
            JOIN repos r ON s.repo_id = r.id
            JOIN user_installations ui ON ui.install_id = r.install_id
            WHERE {where_sql}
            ORDER BY s.scanned_at DESC
            LIMIT ?
        """, params)
    return [dict(r) for r in rows]


def get_user_settings(github_id: int | None = None) -> dict:
    """Return a user's effective scan settings (system defaults when unset)."""
    if github_id is None:
        return {
            "scan_mode": DEFAULT_SCAN_MODE,
            "sandbox_network": DEFAULT_SANDBOX_NETWORK,
            "codeql_enabled": True,
        }
    with _connect() as conn:
        row = conn.execute(
            "SELECT scan_mode, sandbox_network, codeql_enabled FROM user_settings WHERE github_id = ?",
            (github_id,),
        ).fetchone()
    if row is None:
        return {
            "scan_mode": DEFAULT_SCAN_MODE,
            "sandbox_network": DEFAULT_SANDBOX_NETWORK,
            "codeql_enabled": True,
        }
    return {
        "scan_mode": row["scan_mode"] or DEFAULT_SCAN_MODE,
        "sandbox_network": row["sandbox_network"] or DEFAULT_SANDBOX_NETWORK,
        "codeql_enabled": bool(row["codeql_enabled"]),
    }


def update_user_settings(github_id: int, scan_mode: str | None = None,
                         sandbox_network: str | None = None,
                         codeql_enabled: bool | None = None) -> dict:
    """Persist per-user scan settings, validating against the allowed options.

    Passing None for a field leaves it untouched. Raises ValueError when a
    provided value is not in the allowed SCAN_MODES / SANDBOX_NETWORKS.
    """
    if scan_mode is not None and scan_mode not in SCAN_MODES:
        raise ValueError(f"Invalid scan_mode: {scan_mode}")
    if sandbox_network is not None and sandbox_network not in SANDBOX_NETWORKS:
        raise ValueError(f"Invalid sandbox_network: {sandbox_network}")
    if codeql_enabled is not None and not isinstance(codeql_enabled, bool):
        raise ValueError("Invalid codeql_enabled: must be a boolean")

    current = get_user_settings(github_id)
    new_scan_mode = scan_mode if scan_mode is not None else current["scan_mode"]
    new_network = sandbox_network if sandbox_network is not None else current["sandbox_network"]
    new_codeql = codeql_enabled if codeql_enabled is not None else current["codeql_enabled"]

    with _connect() as conn:
        conn.execute("""
            INSERT INTO user_settings (github_id, scan_mode, sandbox_network, codeql_enabled, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(github_id) DO UPDATE SET
                scan_mode = excluded.scan_mode,
                sandbox_network = excluded.sandbox_network,
                codeql_enabled = excluded.codeql_enabled,
                updated_at = datetime('now')
        """, (github_id, new_scan_mode, new_network, 1 if new_codeql else 0))
        conn.commit()

    return {
        "scan_mode": new_scan_mode,
        "sandbox_network": new_network,
        "codeql_enabled": bool(new_codeql),
    }


def get_dashboard_repos(github_id: int | None = None) -> list:
    with _connect() as conn:
        if github_id is None:
            rows = conn.execute("""
                SELECT r.id, r.full_name, r.language, r.owner, r.description,
                    r.private, r.default_branch,
                    COUNT(DISTINCT s.id) AS total_scans,
                    COALESCE(MAX(s.scanned_at), '') AS last_scan_at,
                    COALESCE(SUM(CASE WHEN f.severity = 'HIGH' AND f.status = 'open' THEN 1 ELSE 0 END), 0) AS high_risk,
                    COALESCE(SUM(CASE WHEN f.severity = 'MEDIUM' AND f.status = 'open' THEN 1 ELSE 0 END), 0) AS med_risk,
                    COALESCE(SUM(CASE WHEN f.severity = 'LOW' AND f.status = 'open' THEN 1 ELSE 0 END), 0) AS low_risk
                FROM repos r
                LEFT JOIN scans s ON s.repo_id = r.id
                LEFT JOIN findings f ON f.scan_id = s.id
                GROUP BY r.id
                ORDER BY COALESCE(MAX(s.scanned_at), r.last_scanned_at) DESC
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT r.id, r.full_name, r.language, r.owner, r.description,
                    r.private, r.default_branch,
                    COUNT(DISTINCT s.id) AS total_scans,
                    COALESCE(MAX(s.scanned_at), '') AS last_scan_at,
                    COALESCE(SUM(CASE WHEN f.severity = 'HIGH' AND f.status = 'open' THEN 1 ELSE 0 END), 0) AS high_risk,
                    COALESCE(SUM(CASE WHEN f.severity = 'MEDIUM' AND f.status = 'open' THEN 1 ELSE 0 END), 0) AS med_risk,
                    COALESCE(SUM(CASE WHEN f.severity = 'LOW' AND f.status = 'open' THEN 1 ELSE 0 END), 0) AS low_risk
                FROM repos r
                JOIN user_installations ui
                  ON ui.install_id = r.install_id AND ui.github_id = ?
                LEFT JOIN scans s ON s.repo_id = r.id
                LEFT JOIN findings f ON f.scan_id = s.id
                GROUP BY r.id
                ORDER BY COALESCE(MAX(s.scanned_at), r.last_scanned_at) DESC
            """, (github_id,)).fetchall()
    return [dict(r) for r in rows]
