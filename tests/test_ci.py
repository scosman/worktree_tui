"""Tests for CI status provider."""

import json
from pathlib import Path
from unittest.mock import patch

from wk.status.ci import CIStatus, CIStatusCache, _rollup_status, fetch_ci_statuses


class TestCIStatus:
    """Tests for CIStatus dataclass."""

    def test_display_no_pr(self) -> None:
        """No PR should show dash."""
        status = CIStatus()
        assert status.display == "—"

    def test_display_success(self) -> None:
        """Successful checks should show checkmark."""
        status = CIStatus(check_status="success", pr_url="https://github.com/pr/1")
        assert status.display == "✓"

    def test_display_failure(self) -> None:
        """Failed checks should show X."""
        status = CIStatus(check_status="failure", pr_url="https://github.com/pr/1")
        assert status.display == "✗"

    def test_display_pending(self) -> None:
        """Pending checks should show spinner."""
        status = CIStatus(check_status="pending", pr_url="https://github.com/pr/1")
        assert status.display == "⟳"

    def test_display_merged(self) -> None:
        """Merged PR should show checkmark regardless of check status."""
        status = CIStatus(
            check_status="failure",
            is_merged=True,
            pr_url="https://github.com/pr/1",
        )
        assert status.display == "✓"

    def test_is_approved(self) -> None:
        """is_approved should reflect review decision."""
        assert CIStatus(review_decision="APPROVED").is_approved is True
        assert CIStatus(review_decision="CHANGES_REQUESTED").is_approved is False
        assert CIStatus().is_approved is False


class TestRollupStatus:
    """Tests for _rollup_status helper."""

    def test_empty_checks(self) -> None:
        """Empty or None checks should return None."""
        assert _rollup_status(None) is None
        assert _rollup_status([]) is None

    def test_all_success(self) -> None:
        """All completed/success should return 'success'."""
        checks = [
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
        ]
        assert _rollup_status(checks) == "success"

    def test_any_failure(self) -> None:
        """Any failure should return 'failure'."""
        checks = [
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
            {"status": "COMPLETED", "conclusion": "FAILURE"},
        ]
        assert _rollup_status(checks) == "failure"

    def test_pending(self) -> None:
        """Non-completed status should return 'pending'."""
        checks = [
            {"status": "IN_PROGRESS", "conclusion": ""},
        ]
        assert _rollup_status(checks) == "pending"


class TestFetchCIStatuses:
    """Tests for fetch_ci_statuses."""

    def test_returns_empty_when_gh_not_available(self, tmp_path: Path) -> None:
        """Should return empty dict when gh is not installed."""
        with patch("wk.status.ci.shutil.which", return_value=None):
            result = fetch_ci_statuses(tmp_path)
            assert result == {}

    def test_parses_gh_output(self, tmp_path: Path) -> None:
        """Should parse gh pr list JSON output."""
        prs = [
            {
                "headRefName": "feature-1",
                "statusCheckRollup": [{"status": "COMPLETED", "conclusion": "SUCCESS"}],
                "reviewDecision": "APPROVED",
                "mergedAt": None,
                "closedAt": None,
                "url": "https://github.com/repo/pull/1",
                "reviewRequests": [{"login": "reviewer"}],
                "assignees": [],
            },
        ]
        mock_result = type(
            "Result",
            (),
            {"returncode": 0, "stdout": json.dumps(prs)},
        )()

        with (
            patch("wk.status.ci.shutil.which", return_value="/usr/bin/gh"),
            patch("wk.status.ci.subprocess.run", return_value=mock_result),
        ):
            result = fetch_ci_statuses(tmp_path)
            assert "feature-1" in result
            assert result["feature-1"].check_status == "success"
            assert result["feature-1"].is_approved is True
            assert result["feature-1"].display == "✓"


class TestCIStatusCache:
    """Tests for CIStatusCache."""

    def test_caches_result(self, tmp_path: Path) -> None:
        """Should cache and reuse results within TTL."""
        cache = CIStatusCache(ttl=60.0)
        status = CIStatus(
            check_status="success",
            pr_url="https://github.com/pr/1",
        )

        with patch(
            "wk.status.ci.fetch_ci_statuses",
            return_value={"main": status},
        ) as mock_fetch:
            result1 = cache.get(tmp_path)
            result2 = cache.get(tmp_path)
            assert result1 == result2
            mock_fetch.assert_called_once()

    def test_invalidate_forces_refresh(self, tmp_path: Path) -> None:
        """invalidate() should force the next get() to refetch."""
        cache = CIStatusCache(ttl=60.0)

        with patch(
            "wk.status.ci.fetch_ci_statuses",
            return_value={},
        ) as mock_fetch:
            cache.get(tmp_path)
            cache.invalidate()
            cache.get(tmp_path)
            assert mock_fetch.call_count == 2
