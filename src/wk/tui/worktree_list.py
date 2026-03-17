"""Worktree list widget for TUI."""

from datetime import datetime

from textual.message import Message
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
    """Navigable list of worktrees with type-to-filter support.

    Filtering:
        - Press "/" to enter filter mode
        - Type to filter (matches name and branch)
        - Backspace removes last char
        - Escape exits filter mode (clears filter)
        - "New Worktree" row is hidden while filtering
    """

    DEFAULT_CSS = """
    WorktreeList {
        width: 100%;
        height: 100%;
    }
    """

    class FilterChanged(Message):
        """Posted when filter mode or text changes."""

        def __init__(self, filter_text: str, filtering: bool) -> None:
            self.filter_text = filter_text
            self.filtering = filtering
            super().__init__()

    def __init__(self, worktrees: list[Worktree]) -> None:
        """Build the list: "New Worktree" row + one row per worktree.

        Args:
            worktrees: List of worktrees to display (caller should sort).
        """
        self._all_worktrees = worktrees
        self._filter_text = ""
        self._filtering = False
        super().__init__(*self._build_items(), initial_index=self._default_index())

    def _build_items(self) -> list[WorktreeListItem]:
        """Build list items based on current filter state."""
        filtered = self._filtered_worktrees
        # Only show "New Worktree" when not filtering
        if self._filtering:
            return [WorktreeListItem(wt) for wt in filtered]
        else:
            items = [WorktreeListItem(None)]  # "New Worktree" row
            items.extend(WorktreeListItem(wt) for wt in filtered)
            return items

    def _default_index(self) -> int:
        """Return default index: first worktree if available, else 0."""
        items = self._build_items()
        if self._filtering:
            return 0 if items else 0
        return 1 if len(items) > 1 else 0

    @property
    def _filtered_worktrees(self) -> list[Worktree]:
        """Return worktrees filtered by current filter text."""
        if not self._filter_text:
            return self._all_worktrees
        filter_lower = self._filter_text.lower()
        return [
            wt
            for wt in self._all_worktrees
            if filter_lower in wt.name.lower() or filter_lower in wt.branch.lower()
        ]

    @property
    def filter_text(self) -> str:
        """Current filter text."""
        return self._filter_text

    @property
    def is_filtering(self) -> bool:
        """Whether currently in filter mode."""
        return self._filtering

    def start_filter(self) -> None:
        """Enter filter mode (called by app action)."""
        if not self._filtering:
            self._filtering = True
            self._filter_text = ""
            self._refresh_list(select_first=True)
            self.post_message(self.FilterChanged(self._filter_text, self._filtering))

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

    def on_key(self, event) -> None:
        """Handle key events for filtering."""
        key = event.key

        # "/" enters filter mode
        if key == "/" and not self._filtering:
            event.stop()
            self._filtering = True
            self._filter_text = ""
            self._refresh_list(select_first=True)
            self.post_message(self.FilterChanged(self._filter_text, self._filtering))
            return

        if not self._filtering:
            return  # Only handle filter keys when in filter mode

        # Escape exits filter mode
        if key == "escape":
            event.stop()
            self._filtering = False
            self._filter_text = ""
            self._refresh_list(select_first=False)
            self.post_message(self.FilterChanged(self._filter_text, self._filtering))
            return

        # Backspace removes last char, or exits if empty
        if key == "backspace":
            event.stop()
            if self._filter_text:
                self._filter_text = self._filter_text[:-1]
                self._refresh_list(select_first=True)
            else:
                self._filtering = False
                self._refresh_list(select_first=False)
            self.post_message(self.FilterChanged(self._filter_text, self._filtering))
            return

        # Printable characters add to filter
        if len(key) == 1 and key.isprintable():
            event.stop()
            self._filter_text += key
            self._refresh_list(select_first=True)
            self.post_message(self.FilterChanged(self._filter_text, self._filtering))

    def _refresh_list(self, select_first: bool = False) -> None:
        """Rebuild the list based on current filter.

        Args:
            select_first: If True, select first item. Otherwise preserve selection.
        """
        # Store current selection if not selecting first
        current_worktree = None if select_first else self.selected_worktree

        # Clear and rebuild
        self.clear()

        items = self._build_items()
        for item in items:
            self.append(item)

        if select_first:
            # Select first item
            self.index = 0 if items else 0
        elif current_worktree is not None:
            # Try to restore selection by name
            for i, item in enumerate(items):
                if item.worktree and item.worktree.name == current_worktree.name:
                    self.index = i
                    return
            # Fall back to default
            self.index = self._default_index()
        else:
            self.index = self._default_index()

    async def refresh_worktrees(self, worktrees: list[Worktree]) -> None:
        """Replace the list contents with a new set of worktrees.

        Preserves filter state and cursor position if possible.
        Used after delete to refresh without full app restart.

        Args:
            worktrees: New list of worktrees to display.
        """
        self._all_worktrees = worktrees
        await self._refresh_list_async()

    async def _refresh_list_async(self) -> None:
        """Async version of _refresh_list for use after delete."""
        current_worktree = self.selected_worktree
        await self.clear()

        items = self._build_items()
        for item in items:
            self.append(item)

        if current_worktree is not None:
            for i, item in enumerate(items):
                if item.worktree and item.worktree.name == current_worktree.name:
                    self.index = i
                    return
        self.index = self._default_index()
