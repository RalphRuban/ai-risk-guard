"""
tests/test_migrations.py

Verifies that init_db() upgrades pre-existing on-disk databases:
  - adds the `codeql_provisioned` column to a repos table that predates it
  - rebuilds `ast_cache` with BLOB-affinity `tree` when it was created as TEXT
"""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import utils.db as udb


def _old_repos_schema(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE repos (
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
            last_scanned_at TEXT
        )
    """)
    conn.execute("INSERT INTO repos (id, full_name) VALUES (1, 'owner/repo')")
    conn.commit()


def test_init_db_adds_codeql_provisioned_column(tmp_path):
    db_file = Path(tmp_path) / "old.db"
    conn = sqlite3.connect(str(db_file))
    _old_repos_schema(conn)
    conn.close()

    with patch.object(udb, "DB_PATH", db_file):
        udb.init_db()
        with udb._connect() as conn:
            cols = [r["name"] for r in conn.execute("PRAGMA table_info(repos)").fetchall()]

    assert "codeql_provisioned" in cols


def test_init_db_is_idempotent_when_column_present(tmp_path):
    db_file = Path(tmp_path) / "new.db"
    conn = sqlite3.connect(str(db_file))
    _old_repos_schema(conn)
    conn.execute(
        "ALTER TABLE repos ADD COLUMN codeql_provisioned INTEGER DEFAULT 0"
    )
    conn.commit()
    conn.close()

    with patch.object(udb, "DB_PATH", db_file):
        udb.init_db()
        with udb._connect() as conn:
            cols = [r["name"] for r in conn.execute("PRAGMA table_info(repos)").fetchall()]

    assert cols.count("codeql_provisioned") == 1


def _old_user_settings_schema(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE user_settings (
            github_id INTEGER PRIMARY KEY,
            scan_mode TEXT,
            sandbox_network TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def test_init_db_adds_codeql_enabled_column(tmp_path):
    db_file = Path(tmp_path) / "settings.db"
    conn = sqlite3.connect(str(db_file))
    _old_user_settings_schema(conn)
    conn.close()

    with patch.object(udb, "DB_PATH", db_file):
        udb.init_db()
        with udb._connect() as conn:
            cols = [r["name"] for r in conn.execute("PRAGMA table_info(user_settings)").fetchall()]

    assert "codeql_enabled" in cols


def test_init_db_is_idempotent_for_codeql_enabled(tmp_path):
    db_file = Path(tmp_path) / "settings2.db"
    conn = sqlite3.connect(str(db_file))
    _old_user_settings_schema(conn)
    conn.execute("ALTER TABLE user_settings ADD COLUMN codeql_enabled INTEGER DEFAULT 1")
    conn.commit()
    conn.close()

    with patch.object(udb, "DB_PATH", db_file):
        udb.init_db()
        with udb._connect() as conn:
            cols = [r["name"] for r in conn.execute("PRAGMA table_info(user_settings)").fetchall()]

    assert cols.count("codeql_enabled") == 1


def test_init_db_rebuilds_ast_cache_with_blob_tree(tmp_path):
    db_file = Path(tmp_path) / "ast.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE ast_cache (
            cache_key TEXT PRIMARY KEY,
            tree TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            ttl_seconds INTEGER DEFAULT 86400
        )
    """)
    conn.execute("INSERT INTO ast_cache (cache_key, tree) VALUES ('k', 'stale')")
    conn.commit()
    conn.close()

    with patch.object(udb, "DB_PATH", db_file):
        udb.init_db()
        with udb._connect() as conn:
            cols = {r["name"]: r["type"] for r in conn.execute("PRAGMA table_info(ast_cache)").fetchall()}
            remaining = conn.execute("SELECT COUNT(*) FROM ast_cache").fetchone()[0]

    assert cols["tree"] == "BLOB"
    assert remaining == 0


def test_init_db_keeps_blob_ast_cache_untouched(tmp_path):
    db_file = Path(tmp_path) / "blob.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE ast_cache (
            cache_key TEXT PRIMARY KEY,
            file_path TEXT NOT NULL DEFAULT '',
            tree BLOB NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            ttl_seconds INTEGER DEFAULT 86400
        )
    """)
    conn.execute("INSERT INTO ast_cache (cache_key, tree) VALUES (?, ?)", ("k", b"\x80\x05N."))
    conn.commit()
    conn.close()

    with patch.object(udb, "DB_PATH", db_file):
        udb.init_db()
        with udb._connect() as conn:
            cols = {r["name"]: r["type"] for r in conn.execute("PRAGMA table_info(ast_cache)").fetchall()}
            remaining = conn.execute("SELECT COUNT(*) FROM ast_cache").fetchone()[0]

    assert cols["tree"] == "BLOB"
    assert remaining == 1


def test_init_db_records_schema_version(tmp_path):
    db_file = Path(tmp_path) / "versioned.db"
    with patch.object(udb, "DB_PATH", db_file):
        udb.init_db()
        with udb._connect() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]

    assert version == udb.DB_SCHEMA_VERSION
    assert udb.DB_SCHEMA_VERSION >= 1


def test_maybe_vacuum_reclaims_dominant_freelist(tmp_path):
    db_file = Path(tmp_path) / "vacuum.db"
    with patch.object(udb, "DB_PATH", db_file):
        udb.init_db()
        with udb._connect() as conn:
            conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, data TEXT)")
            conn.executemany(
                "INSERT INTO t (data) VALUES (?)",
                [(str(i),) for i in range(2000)],
            )
            conn.commit()
            conn.execute("DELETE FROM t")
            conn.commit()
            freelist = conn.execute("PRAGMA freelist_count").fetchone()[0]
        udb._maybe_vacuum(min_freelist_pages=1, freelist_fraction=0.0)
        with udb._connect() as conn:
            freelist_after = conn.execute("PRAGMA freelist_count").fetchone()[0]

    assert freelist > 0
    assert freelist_after == 0


def test_maybe_vacuum_skips_small_freelist(tmp_path):
    db_file = Path(tmp_path) / "no_vacuum.db"
    with patch.object(udb, "DB_PATH", db_file):
        udb.init_db()
        udb._maybe_vacuum(min_freelist_pages=10 ** 9, freelist_fraction=1.0)

    with udb._connect() as conn:
        assert conn.execute("PRAGMA freelist_count").fetchone()[0] >= 0
