"""
tests/test_reaction_sync.py
Tests for reaction feedback harvesting via the GitHub Reactions REST API.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import utils.db as udb
from services.github.reaction_sync import fetch_reactions, sync_reaction_feedback


class _TempDB:
    """Patch DB_PATH with a throwaway SQLite file, then clean up."""

    def __enter__(self):
        import utils.db as udb_mod

        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        self._patcher = patch.object(udb_mod, "DB_PATH", Path(self._tmp))
        self._patcher.start()
        udb_mod.init_db()
        return self._tmp

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._patcher.stop()
        try:
            os.unlink(self._tmp)
        except PermissionError:
            pass


def _seed_repo(full_name: str, install_id: int, repo_id: int = 1):
    udb.upsert_repo({
        "id": repo_id,
        "full_name": full_name,
        "owner": full_name.split("/")[0],
        "name": full_name.split("/")[1],
        "description": "",
        "language": "Python",
        "private": 0,
        "default_branch": "main",
        "install_id": install_id,
    })


class TestReactionDB:
    def test_bot_comment_roundtrip(self):
        with _TempDB():
            udb.record_bot_comment(101, "owner/repo", 7)
            udb.record_bot_comment(102, "owner/repo2", 8)

            comments = udb.get_pollable_bot_comments()
            assert {c["comment_id"] for c in comments} == {101, 102}
            # Most recent comment first (ties broken by comment_id desc)
            assert comments[0]["comment_id"] == 102
            assert comments[0]["repo"] == "owner/repo2"

    def test_upsert_keeps_single_row_per_comment(self):
        with _TempDB():
            udb.record_bot_comment(101, "owner/repo", 7)
            udb.record_bot_comment(101, "owner/repo", 9)
            comments = udb.get_pollable_bot_comments()
            assert len(comments) == 1
            assert comments[0]["pr_number"] == 9

    def test_get_install_id_for_repo(self):
        with _TempDB():
            _seed_repo("owner/repo", 55)
            assert udb.get_install_id_for_repo("owner/repo") == 55
            assert udb.get_install_id_for_repo("unknown/repo") is None

    def test_reaction_processed_dedup(self):
        with _TempDB():
            assert udb.reaction_processed(500) is False
            udb.mark_reaction_processed(500, 101, "alice", "rocket")
            assert udb.reaction_processed(500) is True
            assert udb.reaction_processed(501) is False


class TestFetchReactions:
    def test_fetch_parses_reaction_list(self):
        payload = [
            {"id": 1, "content": "rocket", "user": {"login": "alice"}},
            {"id": 2, "content": "-1", "user": {"login": "bob"}},
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = payload
        with patch("services.github.reaction_sync.requests.get", return_value=mock_resp) as mock_get:
            result = fetch_reactions("owner/repo", 101, "tok")

        assert result == payload
        url = mock_get.call_args.args[0]
        assert "/repos/owner/repo/issues/comments/101/reactions" in url

    def test_fetch_non_200_returns_empty(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "forbidden"
        with patch("services.github.reaction_sync.requests.get", return_value=mock_resp):
            assert fetch_reactions("owner/repo", 101, "tok") == []


class TestSyncReactionFeedback:
    def test_records_feedback_for_rocket_and_reject(self):
        with _TempDB():
            _seed_repo("owner/repo", 55)
            udb.record_pr_finding(7, "SQL_INJECTION")
            udb.record_pr_finding(7, "COMMAND_INJECTION")
            udb.record_bot_comment(101, "owner/repo", 7)

            reactions = [
                {"id": 1, "content": "rocket", "user": {"login": "alice"}},
                {"id": 2, "content": "-1", "user": {"login": "bob"}},
                {"id": 3, "content": "+1", "user": {"login": "carol"}},
            ]
            with patch("services.github.reaction_sync.fetch_reactions", return_value=reactions):
                summary = sync_reaction_feedback(lambda install_id: f"tok-{install_id}")

            assert summary == {"accepted": 1, "rejected": 1, "skipped": 0}

            sql = udb.get_feedback_stats("SQL_INJECTION")
            cmd = udb.get_feedback_stats("COMMAND_INJECTION")
            assert sql == {"total": 2, "accepted": 1}  # alice 🚀 + bob 👎
            assert cmd == {"total": 2, "accepted": 1}

    def test_dedup_skips_processed_reactions(self):
        with _TempDB():
            _seed_repo("owner/repo", 55)
            udb.record_pr_finding(7, "SQL_INJECTION")
            udb.record_bot_comment(101, "owner/repo", 7)

            reactions = [{"id": 1, "content": "rocket", "user": {"login": "alice"}}]
            with patch("services.github.reaction_sync.fetch_reactions", return_value=reactions):
                sync_reaction_feedback(lambda i: f"tok-{i}")
                second = sync_reaction_feedback(lambda i: f"tok-{i}")

            assert second == {"accepted": 0, "rejected": 0, "skipped": 1}
            assert udb.get_feedback_stats("SQL_INJECTION") == {"total": 1, "accepted": 1}

    def test_no_reactions_no_feedback(self):
        with _TempDB():
            _seed_repo("owner/repo", 55)
            udb.record_pr_finding(7, "SQL_INJECTION")
            udb.record_bot_comment(101, "owner/repo", 7)

            with patch("services.github.reaction_sync.fetch_reactions", return_value=[]):
                summary = sync_reaction_feedback(lambda i: "tok")

            assert summary == {"accepted": 0, "rejected": 0, "skipped": 0}
            assert udb.get_feedback_stats("SQL_INJECTION") == {"total": 0, "accepted": 0}

    def test_missing_install_id_is_skipped_gracefully(self):
        with _TempDB():
            udb.record_bot_comment(101, "orphan/repo", 7)
            summary = sync_reaction_feedback(lambda i: "tok")
            assert summary == {"accepted": 0, "rejected": 0, "skipped": 0}

    def test_reaction_failure_isolated_per_comment(self):
        with _TempDB():
            _seed_repo("ok/repo", 1, repo_id=1)
            _seed_repo("bad/repo", 2, repo_id=2)
            udb.record_pr_finding(1, "SQL_INJECTION")
            udb.record_bot_comment(101, "ok/repo", 1)
            udb.record_bot_comment(102, "bad/repo", 2)

            def fake_fetch(repo, comment_id, token):
                if repo == "bad/repo":
                    raise RuntimeError("boom")
                return [{"id": 1, "content": "rocket", "user": {"login": "alice"}}]

            with patch("services.github.reaction_sync.fetch_reactions", side_effect=fake_fetch):
                summary = sync_reaction_feedback(lambda i: "tok")

            assert summary["accepted"] == 1
            assert udb.get_feedback_stats("SQL_INJECTION") == {"total": 1, "accepted": 1}


class TestPostPrCommentTracking:
    def test_new_comment_records_bot_comment_and_returns_id(self):
        from services.github.reporter import post_pr_comment

        with _TempDB():
            mock_resp = MagicMock()
            mock_resp.status_code = 201
            mock_resp.json.return_value = {"id": 999}
            with patch("services.github.reporter.requests.get") as mock_get, \
                 patch("services.github.reporter.requests.post", return_value=mock_resp):
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = []
                comment_id = post_pr_comment("owner/repo", 1, [], "token")

            assert comment_id == 999
            comments = udb.get_pollable_bot_comments()
            assert len(comments) == 1
            assert comments[0]["comment_id"] == 999
            assert comments[0]["repo"] == "owner/repo"
            assert comments[0]["pr_number"] == 1
