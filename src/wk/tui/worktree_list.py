"""Worktree list widget for TUI."""

from datetime import datetime

from textual.widgets import ListItem, ListView, Static

from wk.worktree import Worktree


def _relative_time(dt: datetime) -> str:
    """Convert datetime to relative time string.

    Args:
        dt: The datetime to convert (assumed to be in the past).

    Returns:
        A human-readable relative time string like "2 hours ago".
    """
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    delta = now - dt
    seconds = int(delta.total_seconds())

    if seconds < 60:
        return "just now"

    minutes = seconds // 60
    if minutes < 60:
        return "1 minute ago" if minutes == 1 else f"{minutes} minutes ago"

    hours = minutes // 60
    if hours < 24:
        return "1 hour ago" if hours == 1 else f"{hours} hours ago"

    days = hours // 24
    if days < 7:
        return "1 day ago" if days == 1 else f"{days} days ago"

    weeks = days // 7
    if weeks < 4:
        return "1 week ago" if weeks == 1 else f"{weeks} weeks ago"

    months = days // 30
    return "1 month ago" if months == 1 else f"{months} months ago"


class WorktreeListItem(ListItem):
    """A single row in the worktree list.

    Attributes:
        worktree: The Worktree object for this row, or None for the "New Worktree" row.
    """

    DEFAULT_CSS = """
    WorktreeListItem {
        layout: horizontal;
        height: 1;
        padding: 0 2;
    }
    """

    def __init__(self, worktree: Worktree | None) -> None:
        """Create a row.

        Args:
            worktree: The Worktree to display, or None to create the "New Worktree" row.
        """
        self.worktree = worktree
        super().__init__()

    def compose(self):
        """Build the row content."""
        if self.worktree is None:
            # "New Worktree" row
            yield Static("+ New Worktree", classes="new-worktree")
        else:
            # Worktree row: name on left, time on right
            time_str = _relative_time(self.worktree.created)
            yield Static(self.worktree.name, classes="worktree-name")
            yield Static(time_str, classes="worktree-time")


class WorktreeList(ListView):
    """Navigable list of worktrees.

    Emits no custom messages — the parent app reads the selected item
    and decides what to do.
    """

    DEFAULT_CSS = """
    WorktreeList {
        width: 100%;
        height: 100%;
    }
    """

    def __init__(self, worktrees: list[Worktree]) -> None:
        """Build the list: "New Worktree" row + one row per worktree.

        Args:
            worktrees: List of worktrees to display (caller should sort).
        """
        # Build children: "New Worktree" first, then one per worktree
        items = [WorktreeListItem(None)]  # "New Worktree" row
        items.extend(WorktreeListItem(wt) for wt in worktrees)

        # Default to first worktree (index 1) if available, else index 0
        initial_index = 1 if len(items) > 1 else 0
        super().__init__(*items, initial_index=initial_index)

    @property
    def selected_worktree(self) -> Worktree | None:
        """Return the Worktree for the currently highlighted row.

        Returns None if the "New Worktree" row is selected.
        """
        item = self.highlighted_child
        if item is None:
            return None
        # highlighted_child returns ListItem, but we only add WorktreeListItem children
        return getattr(item, "worktree", None)

    async def refresh_worktrees(self, worktrees: list[Worktree]) -> None:
        """Replace the list contents with a new set of worktrees.

        Preserves cursor position if possible (clamps to list bounds).
        Used after delete to refresh without full app restart.

        Args:
            worktrees: New list of worktrees to display.
        """
        # Remember current cursor position
        current_index = self.index

        # Clear existing children (must be awaited)
        await self.clear()

        # Build new children
        items = [WorktreeListItem(None)]
        items.extend(WorktreeListItem(wt) for wt in worktrees)

        # Add new children
        for item in items:
            self.append(item)

        # Clamp cursor to new list bounds
        max_index = len(items) - 1
        if current_index is None:
            current_index = 0
        self.index = min(current_index, max_index)
