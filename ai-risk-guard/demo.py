#!/usr/bin/env python3
"""Task Tracker API — a small team task-management service.

This module is the AI Risk Guard demo application. It implements a realistic
SQLite-backed task service and intentionally contains several security flaws
(hardcoded secret, SQL injection, command injection, path traversal, SSRF,
and weak hashing) so a PR scan produces findings across the report.

The companion test file lives at ``tests/demo_test.py``.
"""

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone

import requests

# --------------------------------------------------------------------------
# Configuration (intentionally insecure — demo only)
# --------------------------------------------------------------------------

# 1. HARDCODED_SECRET: database password baked into the source tree.
DB_PASSWORD = "9kF2#qLz!pRdWx7v"

DATA_DIR = "./task_attachments"
DB_PATH = "./tasks.db"
PREVIEW_DIR = "./previews"
VALID_STATUSES = ("open", "in_progress", "done")


# --------------------------------------------------------------------------
# Database helpers
# --------------------------------------------------------------------------


def connect_db(path: str = DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with rows accessible by column name."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create the tasks table when it does not yet exist."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tasks ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "title TEXT NOT NULL,"
        "description TEXT NOT NULL DEFAULT '',"
        "owner TEXT NOT NULL,"
        "status TEXT NOT NULL DEFAULT 'open',"
        "created_at TEXT NOT NULL)"
    )
    conn.commit()


# --------------------------------------------------------------------------
# CRUD
# --------------------------------------------------------------------------


def create_task(conn, title, description, owner):
    """Insert a new task and return its id."""
    cursor = conn.execute(
        "INSERT INTO tasks (title, description, owner, status, created_at) "
        "VALUES (?, ?, ?, 'open', ?)",
        (title, description, owner, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def list_tasks(conn, status=None):
    """Return every task, optionally filtered by status."""
    if status:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def get_task(conn, task_id):
    """Fetch a single task by id, or None when it does not exist."""
    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    return dict(row) if row else None


# 2. SQL_INJECTION: the search term is interpolated straight into the query.
def search_tasks(conn, keyword):
    """Search tasks whose title matches *keyword* (unsafe query building)."""
    rows = conn.execute(f"SELECT * FROM tasks WHERE title LIKE '%{keyword}%'").fetchall()
    return [dict(row) for row in rows]


def update_task_status(conn, task_id, status):
    """Move a task into a new status and return True on success."""
    cursor = conn.execute(
        "UPDATE tasks SET status = ? WHERE id = ?",
        (status, task_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_task(conn, task_id):
    """Remove a task and return True when a row was deleted."""
    cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    return cursor.rowcount > 0


# --------------------------------------------------------------------------
# Attachments and previews
# --------------------------------------------------------------------------


# 3. PATH_TRAVERSAL: the task id flows into a filesystem path unsanitized.
def read_attachment(task_id):
    """Read the attachment file stored for a task."""
    with open(f"{DATA_DIR}/{task_id}.txt", "r", encoding="utf-8") as handle:
        return handle.read()


# 4. SSRF: the preview URL is fetched server-side with no allow-list.
def add_preview_note(task_id, url):
    """Download a remote page and cache a short preview for a task."""
    response = requests.get(url, timeout=5)
    snippet = response.text[:500]
    save_preview_cache(task_id, {"url": url, "snippet": snippet})
    return snippet


def save_preview_cache(task_id, payload):
    """Persist a preview payload as JSON on disk."""
    if not os.path.isdir(PREVIEW_DIR):
        os.makedirs(PREVIEW_DIR, exist_ok=True)
    path = f"{PREVIEW_DIR}/{task_id}.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def load_preview_cache(task_id):
    """Read a previously saved preview, or None when missing."""
    path = f"{PREVIEW_DIR}/{task_id}.json"
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


# 5. COMMAND_INJECTION: keyword is interpolated into a shell command.
def export_matches(conn, keyword):
    """Grep the exported CSV for tasks matching *keyword* via the shell."""
    report_path = "task_report.csv"
    result = subprocess.run(
        f"grep -n \"{keyword}\" {report_path}",
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def export_all_tasks(conn, path):
    """Write every task to a CSV file and return the number exported."""
    rows = list_tasks(conn)
    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(
            f"{row['id']},{row['title']},{row['owner']},{row['status']}\n"
            for row in rows
        )
    return len(rows)


# --------------------------------------------------------------------------
# Authentication helpers
# --------------------------------------------------------------------------


# 6. WEAK_CRYPTOGRAPHY: MD5 is not suitable for hashing credentials.
def hash_api_token(token):
    """Return a hex digest for an API token (unsafe hashing)."""
    return hashlib.md5(token.encode("utf-8")).hexdigest()


def verify_api_token(token, expected_hash):
    """Return True when *token* hashes to *expected_hash*."""
    return hash_api_token(token) == expected_hash


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv=None):
    """Command-line entry point for the task service."""
    parser = argparse.ArgumentParser(prog="demo", description="Task Tracker API")
    parser.add_argument("--db", default=DB_PATH, help="SQLite database file")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="create a task")
    add.add_argument("title")
    add.add_argument("owner")
    add.add_argument("--description", default="")

    search = sub.add_parser("search", help="search tasks")
    search.add_argument("keyword")

    status = sub.add_parser("status", help="change a task status")
    status.add_argument("task_id", type=int)
    status.add_argument("value", choices=VALID_STATUSES)

    args = parser.parse_args(argv)

    conn = connect_db(args.db)
    init_db(conn)
    try:
        if args.command == "add":
            task_id = create_task(conn, args.title, args.description, args.owner)
            print(f"created task {task_id}")
        elif args.command == "search":
            for task in search_tasks(conn, args.keyword):
                print(f"#{task['id']} {task['title']} ({task['status']})")
        elif args.command == "status":
            ok = update_task_status(conn, args.task_id, args.value)
            print("updated" if ok else "task not found")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
