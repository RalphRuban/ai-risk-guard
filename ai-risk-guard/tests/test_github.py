"""
tests/test_github.py
Tests for GitHub integration: SARIF upload, labels, and comments.
"""

from unittest.mock import MagicMock, patch

from services.github.reporter import (
    _check_conclusion,
    _extract_scan_number,
    _risk_label_name,
    create_check_run,
    find_existing_bot_comment,
    post_pr_comment,
    remove_pr_labels,
    set_pr_labels,
    update_pr_comment,
    upload_sarif_to_code_scanning,
)


class TestReporterCodeScanning:
    """Tests for code scanning SARIF upload."""

    @patch("services.github.reporter.requests.get")
    @patch("services.github.reporter.requests.post")
    def test_upload_sarif_success(self, mock_post, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {"id": "test-sarif-id"}
        mock_response.text = ""
        mock_post.return_value = mock_response

        mock_status = MagicMock()
        mock_status.status_code = 200
        mock_status.json.return_value = {"processing_status": "completed"}
        mock_get.return_value = mock_status

        result = upload_sarif_to_code_scanning(
            "test_owner/test_repo", 1, "test_token", "{}", "HEAD"
        )

        assert result is None  # function doesn't return anything on success

    @patch("services.github.reporter.requests.post")
    def test_upload_sarif_422(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = '{"message": "already uploaded"}'
        mock_post.return_value = mock_response

        # Should not raise — 422 is handled gracefully as duplicate
        upload_sarif_to_code_scanning("owner/repo", 1, "token", "{}", "HEAD")

    @patch("services.github.reporter.requests.get")
    def test_find_existing_bot_comment_returns_none(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = find_existing_bot_comment("owner/repo", "1", "token")

        assert result is None

    @patch("services.github.reporter.requests.get")
    def test_find_existing_bot_comment_empty_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = find_existing_bot_comment("owner/repo", "1", "token")

        assert result is None

    @patch("services.github.reporter.requests.get")
    @patch("services.github.reporter.requests.delete")
    def test_find_existing_bot_comment_with_matching(self, mock_delete, mock_get):
        def side_effect(*args, **kwargs):
            page = kwargs.get("url", args[0] if args else "")
            resp = MagicMock()
            resp.status_code = 200
            if "page=1" in page:
                resp.json.return_value = [
                    {"id": 42, "body": "<!-- ai-risk-guard scan:1 -->\n<!-- ai-risk-guard -->", "user": {"type": "Bot"}, "created_at": "2025-01-01T00:00:00Z"}
                ]
            else:
                resp.json.return_value = []
            return resp
        mock_get.side_effect = side_effect
        mock_delete.return_value.status_code = 204

        result = find_existing_bot_comment("owner/repo", "1", "token")

        assert result is not None
        assert result[0] == 42
        assert result[1] == 1

    @patch("services.github.reporter.requests.get")
    @patch("services.github.reporter.requests.delete")
    def test_find_existing_bot_comment_prefers_most_recent(
        self, mock_delete, mock_get
    ):
        def side_effect(*args, **kwargs):
            page = kwargs.get("url", args[0] if args else "")
            resp = MagicMock()
            resp.status_code = 200
            if "page=1" in page:
                resp.json.return_value = [
                    {"id": 1, "body": "<!-- ai-risk-guard scan:1 -->\n<!-- ai-risk-guard -->", "user": {"type": "Bot"}, "created_at": "2025-01-01T00:00:00Z"},
                    {"id": 2, "body": "<!-- ai-risk-guard scan:2 -->\n<!-- ai-risk-guard -->", "user": {"type": "Bot"}, "created_at": "2025-01-02T00:00:00Z"},
                ]
            else:
                resp.json.return_value = []
            return resp
        mock_get.side_effect = side_effect

        mock_delete.return_value.status_code = 204

        result = find_existing_bot_comment("owner/repo", "1", "token")

        assert result is not None
        assert result[0] == 2
        assert result[1] == 2

    @patch("services.github.reporter.requests.post")
    @patch("services.github.reporter.requests.get")
    @patch("services.github.reporter.requests.delete")
    def test_post_new_comment_when_no_existing(
        self, mock_delete, mock_get, mock_post
    ):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []

        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"id": 99}

        post_pr_comment("owner/repo", 1, [], "token")

        mock_post.assert_called_once()

    @patch("services.github.reporter.requests.patch")
    @patch("services.github.reporter.requests.get")
    @patch("services.github.reporter.requests.delete")
    def test_update_existing_comment(
        self, mock_delete, mock_get, mock_patch
    ):
        def side_effect(*args, **kwargs):
            page = kwargs.get("url", args[0] if args else "")
            resp = MagicMock()
            resp.status_code = 200
            if "page=1" in page:
                resp.json.return_value = [
                    {"id": 42, "body": "<!-- ai-risk-guard scan:1 -->\n<!-- ai-risk-guard -->", "user": {"type": "Bot"}, "created_at": "2025-01-01T00:00:00Z"}
                ]
            else:
                resp.json.return_value = []
            return resp
        mock_get.side_effect = side_effect
        mock_delete.return_value.status_code = 204
        mock_patch.return_value.status_code = 200

        post_pr_comment("owner/repo", 1, [{"risk": 5, "vulnerability": {"type": "SQLI", "severity": "MEDIUM"}}], "token")

        mock_patch.assert_called_once()

    def test_update_pr_comment(self):
        with patch("services.github.reporter.requests.patch") as mock_patch:
            mock_patch.return_value.status_code = 200
            result = update_pr_comment("owner/repo", 42, "token", "new body")
            assert result is True

    def test_update_pr_comment_failure(self):
        with patch("services.github.reporter.requests.patch") as mock_patch:
            mock_patch.return_value.status_code = 404
            result = update_pr_comment("owner/repo", 42, "token", "new body")
            assert result is False



class TestGitHubLabels:
    """Tests for GitHub PR labeling."""

    @patch("services.github.reporter.requests.put")
    @patch("services.github.reporter.remove_pr_labels")
    def test_set_pr_labels_adds_label(self, mock_remove, mock_put):
        mock_put.return_value.status_code = 200

        set_pr_labels("owner/repo", 1, "token", 8.0)

        mock_put.assert_called_once()

    @patch("services.github.reporter.requests.put")
    @patch("services.github.reporter.remove_pr_labels")
    def test_set_pr_labels_failure(self, mock_remove, mock_put):
        mock_put.return_value.status_code = 404

        # Should not raise
        set_pr_labels("owner/repo", 1, "token", 8.0)

    @patch("services.github.reporter.requests.put")
    @patch("services.github.reporter.remove_pr_labels")
    def test_set_pr_labels_exception_safe(self, mock_remove, mock_put):
        mock_put.side_effect = Exception("API error")

        # Should not raise
        set_pr_labels("owner/repo", 1, "token", 5.0)

    def test_risk_label_name_high(self):
        assert _risk_label_name(8.0) == "security-risk-high"
        assert _risk_label_name(7.0) == "security-risk-high"

    def test_risk_label_name_moderate(self):
        assert _risk_label_name(5.0) == "security-risk-medium"
        assert _risk_label_name(4.0) == "security-risk-medium"

    def test_risk_label_name_low(self):
        assert _risk_label_name(2.0) == "security-risk-low"
        assert _risk_label_name(0.0) == "security-risk-low"

    @patch("services.github.reporter.requests.delete")
    def test_remove_pr_labels_success(self, mock_delete):
        mock_delete.return_value.status_code = 200

        remove_pr_labels("owner/repo", 1, "token", ["security-risk-high", "security-risk-low"])

        assert mock_delete.call_count == 2

    @patch("services.github.reporter.requests.delete")
    def test_remove_pr_labels_404_safe(self, mock_delete):
        mock_delete.return_value.status_code = 404

        # Should not raise
        remove_pr_labels("owner/repo", 1, "token", ["security-risk-high"])


class TestExtractScanNumber:
    """Tests for _extract_scan_number."""

    def test_extract_scan_number_from_comment(self):
        body = "<!-- ai-risk-guard scan:42 -->\n## AI Risk Guard\n<!-- ai-risk-guard -->"
        assert _extract_scan_number(body) == 42

    def test_extract_scan_number_not_found(self):
        body = "## AI Risk Guard\nNo scan info"
        assert _extract_scan_number(body) == 0

    def test_extract_scan_number_empty(self):
        assert _extract_scan_number("") == 0

    def test_extract_scan_number_increments(self):
        """If existing comment has scan:5, the next scan should be 6."""
        body = "<!-- ai-risk-guard scan:5 -->\n..."
        existing = _extract_scan_number(body)
        next_scan = existing + 1
        assert next_scan == 6


def _finding(**overrides):
    """Build a minimal finding dict that passes all validation signals by default."""
    finding = {
        "vulnerability": {"type": "SQL_INJECTION", "severity": "MEDIUM"},
        "rule_id": "SQL001",
        "patch_suppressed": False,
        "validation": {
            "success": True,
            "details": {
                "syntax": {"success": True},
                "sandbox": {"success": True},
                "rescan": {"success": True},
                "policy": {"success": True},
            },
            "test_results": {"success": True, "mode": "docker", "skipped": False},
        },
    }
    finding.update(overrides)
    return finding


class TestCheckRun:
    """Tests for GitHub Check Run patch verification (informational, non-gating)."""

    def test_check_conclusion_empty_results_is_success(self):
        conclusion, summary = _check_conclusion([])
        assert conclusion == "success"
        assert "No security vulnerabilities" in summary

    def test_check_conclusion_all_green_is_success(self):
        results = [
            _finding(),
            _finding(vulnerability={"type": "SSRF", "severity": "HIGH"}, rule_id="SSRF001"),
        ]
        conclusion, summary = _check_conclusion(results)
        assert conclusion == "success"
        assert "✅" in summary

    def test_check_conclusion_failed_tests_is_failure(self):
        results = [
            _finding(
                validation={
                    "success": False,
                    "details": {
                        "syntax": {"success": True},
                        "rescan": {"success": True},
                    },
                    "test_results": {"success": False, "mode": "docker", "skipped": False},
                }
            )
        ]
        conclusion, summary = _check_conclusion(results)
        assert conclusion == "failure"
        assert "failed regression tests" in summary

    def test_check_conclusion_rescan_not_clean_is_failure(self):
        results = [
            _finding(
                validation={
                    "success": False,
                    "details": {
                        "syntax": {"success": True},
                        "rescan": {"success": False},
                    },
                    "test_results": {"success": True, "mode": "docker", "skipped": False},
                }
            )
        ]
        conclusion, _ = _check_conclusion(results)
        assert conclusion == "failure"

    def test_check_conclusion_skipped_tests_is_neutral(self):
        results = [
            _finding(
                validation={
                    "success": False,
                    "details": {
                        "syntax": {"success": True},
                        "rescan": {"success": True},
                    },
                    "test_results": {"success": False, "mode": "docker", "skipped": True},
                }
            )
        ]
        conclusion, summary = _check_conclusion(results)
        assert conclusion == "neutral"
        assert "skipped" in summary

    def test_check_conclusion_docker_unavailable_is_neutral(self):
        results = [
            _finding(
                validation={
                    "success": True,
                    "details": {
                        "syntax": {"success": True},
                        "rescan": {"success": True},
                    },
                    "test_results": {
                        "success": True,
                        "mode": "local",
                        "skipped": False,
                        "docker_unavailable": True,
                    },
                }
            )
        ]
        conclusion, summary = _check_conclusion(results)
        assert conclusion == "neutral"
        assert "local fallback" in summary

    def test_check_conclusion_patch_suppressed_is_neutral(self):
        results = [_finding(patch_suppressed=True)]
        conclusion, summary = _check_conclusion(results)
        assert conclusion == "neutral"
        assert "patch suppressed" in summary

    def test_check_conclusion_failure_beats_neutral(self):
        results = [
            _finding(),
            _finding(patch_suppressed=True),
            _finding(
                validation={
                    "success": False,
                    "details": {
                        "syntax": {"success": True},
                        "rescan": {"success": True},
                    },
                    "test_results": {"success": False, "mode": "docker", "skipped": False},
                }
            ),
        ]
        conclusion, _ = _check_conclusion(results)
        assert conclusion == "failure"

    def test_check_conclusion_gating_false_makes_failure_neutral(self):
        results = [
            _finding(
                validation={
                    "success": False,
                    "details": {
                        "syntax": {"success": True},
                        "rescan": {"success": True},
                    },
                    "test_results": {"success": False, "mode": "docker", "skipped": False},
                }
            )
        ]
        conclusion, summary = _check_conclusion(results, gating=False)
        assert conclusion == "neutral"
        assert "(neutral)" in summary
        assert "never blocks merges" in summary

    def test_check_conclusion_gating_true_keeps_failure(self):
        results = [
            _finding(
                validation={
                    "success": False,
                    "details": {
                        "syntax": {"success": True},
                        "rescan": {"success": True},
                    },
                    "test_results": {"success": False, "mode": "docker", "skipped": False},
                }
            )
        ]
        conclusion, _ = _check_conclusion(results, gating=True)
        assert conclusion == "failure"

    @patch("services.github.reporter.requests.post")
    def test_create_check_run_posts_neutral_when_not_gating(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "check-123"}
        mock_post.return_value = mock_response

        failed_finding = _finding(
            validation={
                "success": False,
                "details": {
                    "syntax": {"success": True},
                    "rescan": {"success": True},
                },
                "test_results": {"success": False, "mode": "docker", "skipped": False},
            }
        )
        create_check_run("owner/repo", 7, "token", [failed_finding], "deadbeef1234567890")

        payload = mock_post.call_args[1]["json"]
        assert payload["conclusion"] == "neutral"
        assert "(neutral)" in payload["output"]["summary"]

    @patch("services.github.reporter.requests.post")
    def test_create_check_run_posts_correct_payload(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "check-123"}
        mock_post.return_value = mock_response

        create_check_run(
            "owner/repo", 7, "token", [_finding()], "deadbeef1234567890"
        )

        url = mock_post.call_args[0][0]
        payload = mock_post.call_args[1]["json"]
        assert url == "https://api.github.com/repos/owner/repo/check-runs"
        assert payload["name"] == "ai-risk-guard/validation"
        assert payload["head_sha"] == "deadbeef1234567890"
        assert payload["status"] == "completed"
        assert payload["conclusion"] == "success"
        assert "AI Risk Guard patch validation" in payload["output"]["title"]
        assert payload["output"]["summary"].startswith("### AI Risk Guard")

    @patch("services.github.reporter.requests.post")
    def test_create_check_run_non_2xx_does_not_raise(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = '{"message": "bad request"}'
        mock_post.return_value = mock_response

        # Should not raise
        create_check_run("owner/repo", 7, "token", [_finding()], "deadbeef")

    @patch("services.github.reporter.requests.post")
    def test_create_check_run_exception_safe(self, mock_post):
        mock_post.side_effect = Exception("API error")

        # Should not raise
        create_check_run("owner/repo", 7, "token", [_finding()], "deadbeef")
