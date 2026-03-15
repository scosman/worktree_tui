"""Tests for tui/worktree_list.py."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from textual.app import App, ComposeResult

from wk.tui.worktree_list import WorktreeList, WorktreeListItem, _relative_time
from wk.worktree import Worktree


class TestRelativeTime:
    """Tests for _relative_time helper."""

    def test_just_now(self):
        """Times less than 60 seconds ago return 'just now'."""
        now = datetime.now(UTC)
        dt = now - timedelta(seconds=30)
        assert _relative_time(dt) == "just now"

    def test_one_minute_ago(self):
        """60-119 seconds returns '1 minute ago'."""
        now = datetime.now(UTC)
        dt = now - timedelta(seconds=90)
        assert _relative_time(dt) == "1 minute ago"

    def test_minutes_ago(self):
        """2-59 minutes returns 'X minutes ago'."""
        now = datetime.now(UTC)
        dt = now - timedelta(minutes=5)
        assert _relative_time(dt) == "5 minutes ago"

    def test_one_hour_ago(self):
        """60-119 minutes returns '1 hour ago'."""
        now = datetime.now(UTC)
        dt = now - timedelta(minutes=90)
        assert _relative_time(dt) == "1 hour ago"

    def test_hours_ago(self):
        """2-23 hours returns 'X hours ago'."""
        now = datetime.now(UTC)
        dt = now - timedelta(hours=5)
        assert _relative_time(dt) == "5 hours ago"

    def test_one_day_ago(self):
        """24-47 hours returns '1 day ago'."""
        now = datetime.now(UTC)
        dt = now - timedelta(hours=30)
        assert _relative_time(dt) == "1 day ago"

    def test_days_ago(self):
        """2-6 days returns 'X days ago'."""
        now = datetime.now(UTC)
        dt = now - timedelta(days=3)
        assert _relative_time(dt) == "3 days ago"

    def test_one_week_ago(self):
        """7-13 days returns '1 week ago'."""
        now = datetime.now(UTC)
        dt = now - timedelta(days=10)
        assert _relative_time(dt) == "1 week ago"

    def test_weeks_ago(self):
        """2-3 weeks returns 'X weeks ago'."""
        now = datetime.now(UTC)
        dt = now - timedelta(days=14)
        assert _relative_time(dt) == "2 weeks ago"

    def test_one_month_ago(self):
        """30+ days returns '1 month ago'."""
        now = datetime.now(UTC)
        dt = now - timedelta(days=35)
        assert _relative_time(dt) == "1 month ago"

    def test_months_ago(self):
        """60+ days returns 'X months ago'."""
        now = datetime.now(UTC)
        dt = now - timedelta(days=90)
        assert _relative_time(dt) == "3 months ago"

    def test_naive_datetime(self):
        """Works with naive datetime (no timezone)."""
        now = datetime.now()
        dt = now - timedelta(hours=2)
        assert _relative_time(dt) == "2 hours ago"


class TestWorktreeListItem:
    """Tests for WorktreeListItem."""

    def test_worktree_attribute_stores_none_for_new_row(self):
        """New Worktree row has worktree=None."""
        item = WorktreeListItem(None)
        assert item.worktree is None

    def test_worktree_attribute_stores_worktree(self):
        """Regular row stores the worktree."""
        wt = Worktree(
            name="my-feature",
            path=Path("/path/to/worktree"),
            branch="my-feature",
            created=datetime.now(UTC),
        )
        item = WorktreeListItem(wt)
        assert item.worktree is wt


# Helper to create worktrees for tests
def make_worktree(name: str, days_ago: int = 0) -> Worktree:
    """Create a Worktree with given name and creation time."""
    created = datetime.now(UTC) - timedelta(days=days_ago)
    return Worktree(
        name=name,
        path=Path(f"/path/to/{name}"),
        branch=name,
        created=created,
    )


# Test App for mounting WorktreeList
class _TestApp(App):
    """Minimal app for testing WorktreeList."""

    def __init__(self, worktrees: list[Worktree]):
        super().__init__()
        self._worktrees = worktrees

    def compose(self) -> ComposeResult:
        yield WorktreeList(self._worktrees)


class TestWorktreeListMounted:
    """Tests for WorktreeList widget that require mounting."""

    @pytest.mark.asyncio
    async def test_new_worktree_is_first_item(self):
        """List renders 'New Worktree' as first item."""
        worktrees = [make_worktree("feature-1")]
        async with _TestApp(worktrees).run_test() as pilot:
            widget = pilot.app.query_one(WorktreeList)
            children = list(widget.children)
            assert len(children) >= 1
            assert isinstance(children[0], WorktreeListItem)
            assert children[0].worktree is None

    @pytest.mark.asyncio
    async def test_renders_worktrees_in_order(self):
        """List renders worktrees in the order provided."""
        worktrees = [
            make_worktree("feature-a"),
            make_worktree("feature-b"),
            make_worktree("feature-c"),
        ]
        async with _TestApp(worktrees).run_test() as pilot:
            widget = pilot.app.query_one(WorktreeList)
            children = list(widget.children)
            # First is "New Worktree", then the worktrees
            assert len(children) == 4
            assert isinstance(children[1], WorktreeListItem)
            assert isinstance(children[2], WorktreeListItem)
            assert isinstance(children[3], WorktreeListItem)
            assert children[1].worktree is worktrees[0]
            assert children[2].worktree is worktrees[1]
            assert children[3].worktree is worktrees[2]

    @pytest.mark.asyncio
    async def test_selected_worktree_returns_none_for_new_row(self):
        """selected_worktree returns None when 'New Worktree' is selected."""
        worktrees = [make_worktree("feature-1")]
        async with _TestApp(worktrees).run_test() as pilot:
            widget = pilot.app.query_one(WorktreeList)
            widget.index = 0
            assert widget.selected_worktree is None

    @pytest.mark.asyncio
    async def test_selected_worktree_returns_correct_worktree(self):
        """selected_worktree returns the Worktree for the selected row."""
        worktrees = [
            make_worktree("feature-1"),
            make_worktree("feature-2"),
        ]
        async with _TestApp(worktrees).run_test() as pilot:
            widget = pilot.app.query_one(WorktreeList)
            widget.index = 1  # First worktree (after "New Worktree")
            assert widget.selected_worktree is worktrees[0]

    @pytest.mark.asyncio
    async def test_default_cursor_is_index_1_with_worktrees(self):
        """Default cursor position is index 1 (most recent worktree)."""
        worktrees = [make_worktree("feature-1")]
        async with _TestApp(worktrees).run_test() as pilot:
            widget = pilot.app.query_one(WorktreeList)
            # on_mount is called automatically
            assert widget.index == 1

    @pytest.mark.asyncio
    async def test_default_cursor_is_0_with_no_worktrees(self):
        """Default cursor is 0 when there are no worktrees."""
        async with _TestApp([]).run_test() as pilot:
            widget = pilot.app.query_one(WorktreeList)
            assert widget.index == 0

    @pytest.mark.asyncio
    async def test_refresh_worktrees_updates_contents(self):
        """refresh_worktrees replaces the list contents."""
        initial = [
            make_worktree("feature-1"),
            make_worktree("feature-2"),
            make_worktree("feature-3"),
        ]
        async with _TestApp(initial).run_test() as pilot:
            widget = pilot.app.query_one(WorktreeList)

            # Refresh with fewer worktrees
            new_worktrees = [
                make_worktree("feature-a"),
                make_worktree("feature-b"),
            ]
            await widget.refresh_worktrees(new_worktrees)

            children = list(widget.children)
            # 1 "New" + 2 worktrees = 3 total
            assert len(children) == 3
            assert isinstance(children[0], WorktreeListItem)
            assert isinstance(children[1], WorktreeListItem)
            assert isinstance(children[2], WorktreeListItem)
            assert children[0].worktree is None
            assert children[1].worktree is new_worktrees[0]
            assert children[2].worktree is new_worktrees[1]

    @pytest.mark.asyncio
    async def test_refresh_worktrees_clamps_cursor(self):
        """refresh_worktrees clamps cursor to new list bounds."""
        initial = [
            make_worktree("feature-1"),
            make_worktree("feature-2"),
            make_worktree("feature-3"),
        ]
        async with _TestApp(initial).run_test() as pilot:
            widget = pilot.app.query_one(WorktreeList)
            widget.index = 3  # Last worktree

            # Refresh to fewer items (only 1 worktree = 2 total items)
            new_worktrees = [make_worktree("feature-a")]
            await widget.refresh_worktrees(new_worktrees)

            # Cursor should clamp to max index (1)
            assert widget.index == 1
