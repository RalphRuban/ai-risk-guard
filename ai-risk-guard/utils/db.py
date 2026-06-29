"""
utils/db.py
Persistent SQLite-backed dashboard storage.
Replaces the in-memory analysis_data dict in main.py.
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "data/dashboard.db"))


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist. Call once at startup."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dashboard (
                key   TEXT PRIMARY KEY,
                value INTEGER NOT NULL DEFAULT 0
            )
        """)
        
        # New table for feedback loop (Week 4)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patch_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vuln_type TEXT NOT NULL,
                outcome TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # New table to track findings per PR for automated merge-feedback (Phase 3)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pr_findings (
                pr_number INTEGER,
                vuln_type TEXT,
                PRIMARY KEY (pr_number, vuln_type)
            )
        """)

        # Seed rows so UPDATE always finds a row
        for key in ("total_prs", "total_vulnerabilities",
                    "risk_LOW", "risk_MEDIUM", "risk_HIGH"):
            conn.execute(
                "INSERT OR IGNORE INTO dashboard (key, value) VALUES (?, 0)",
                (key,)
            )
        conn.commit()


def record_feedback(vuln_type: str, outcome: str):
    """Record developer feedback (ACCEPTED/REJECTED)."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO patch_feedback (vuln_type, outcome) VALUES (?, ?)",
            (vuln_type, outcome)
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
            f"UPDATE dashboard SET value = value + 1 WHERE key = 'risk_{risk_level}'"
        )
        conn.commit()


def get_dashboard() -> dict:
    """Return the current dashboard stats as a plain dict."""
    with _connect() as conn:
        rows = conn.execute("SELECT key, value FROM dashboard").fetchall()

    data = {row["key"]: row["value"] for row in rows}

    # Get trend data (last 7 days)
    with _connect() as conn:
        trends = conn.execute("""
            SELECT date(timestamp) as day, COUNT(*) as count 
            FROM patch_feedback 
            GROUP BY day 
            ORDER BY day DESC LIMIT 7
        """).fetchall()

    # Get agent performance
    with _connect() as conn:
        # Note: We'll need to update record_feedback to track agent_id later
        # For now, let's just get the breakdown by vuln type
        agent_perf = conn.execute("""
            SELECT vuln_type, outcome, COUNT(*) as count 
            FROM patch_feedback 
            GROUP BY vuln_type, outcome
        """).fetchall()

    return {
        "total_prs":             data.get("total_prs", 0),
        "total_vulnerabilities": data.get("total_vulnerabilities", 0),
        "risk_levels": {
            "LOW":    data.get("risk_LOW", 0),
            "MEDIUM": data.get("risk_MEDIUM", 0),
            "HIGH":   data.get("risk_HIGH", 0),
        },
        "trends": [{"day": t["day"], "count": t["count"]} for t in trends],
        "performance": [{"type": a["vuln_type"], "outcome": a["outcome"], "count": a["count"]} for a in agent_perf]
    }