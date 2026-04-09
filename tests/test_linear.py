"""Tests for Linear status provider."""

from unittest.mock import patch

from wk.status.linear import (
    LinearStatus,
    LinearStatusCache,
    extract_ticket_id,
    fetch_linear_statuses,
)


class TestExtractTicketId:
    """Tests for extract_ticket_id."""

    def test_simple_ticket(self) -> None:
        assert extract_ticket_id("KIL-123") == "KIL-123"

    def test_ticket_with_slash_description(self) -> None:
        assert extract_ticket_id("KIL-123/add-feature") == "KIL-123"

    def test_ticket_with_dash_description(self) -> None:
        assert extract_ticket_id("KIL-456-fix-bug") == "KIL-456"

    def test_no_ticket(self) -> None:
        assert extract_ticket_id("main") is None

    def test_lowercase_no_match(self) -> None:
        assert extract_ticket_id("kil-123") is None

    def test_different_team_prefix(self) -> None:
        assert extract_ticket_id("ENG-42/refactor") == "ENG-42"


class TestFetchLinearStatuses:
    """Tests for fetch_linear_statuses."""

    def test_returns_empty_without_api_key(self) -> None:
        """Should return empty dict without API key."""
        with patch.dict("os.environ", {}, clear=True):
            result = fetch_linear_statuses(["KIL-123/feature"])
            assert result == {}

    def test_returns_empty_for_no_tickets(self) -> None:
        """Should return empty dict when no worktree names match tickets."""
        result = fetch_linear_statuses(
            ["main", "develop"],
            api_key="test-key",
        )
        assert result == {}

    def test_maps_worktree_names_to_statuses(self) -> None:
        """Should map worktree names back to their statuses."""
        with patch(
            "wk.status.linear._fetch_issue_states",
            return_value={"KIL-123": "In Progress"},
        ):
            result = fetch_linear_statuses(
                ["KIL-123/feature", "main"],
                api_key="test-key",
            )
            assert "KIL-123/feature" in result
            assert result["KIL-123/feature"].state_name == "In Progress"
            assert "main" not in result


class TestLinearStatusCache:
    """Tests for LinearStatusCache."""

    def test_caches_result(self) -> None:
        """Should cache and reuse results within TTL."""
        cache = LinearStatusCache(ttl=60.0)

        with patch(
            "wk.status.linear.fetch_linear_statuses",
            return_value={
                "KIL-1": LinearStatus("KIL-1", "Done"),
            },
        ) as mock_fetch:
            result1 = cache.get(["KIL-1/feat"], api_key="key")
            result2 = cache.get(["KIL-1/feat"], api_key="key")
            assert result1 == result2
            mock_fetch.assert_called_once()

    def test_invalidate(self) -> None:
        """invalidate() should force the next get() to refetch."""
        cache = LinearStatusCache(ttl=60.0)

        with patch(
            "wk.status.linear.fetch_linear_statuses",
            return_value={},
        ) as mock_fetch:
            cache.get(["KIL-1"], api_key="key")
            cache.invalidate()
            cache.get(["KIL-1"], api_key="key")
            assert mock_fetch.call_count == 2
