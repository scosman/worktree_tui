# Phase 6: TUI Theme and Worktree List Widget

## Overview

Implement the TUI styling (`tui/theme.py`) and worktree list widget (`tui/worktree_list.py`). These are prerequisites for the main app (Phase 7).

Spec files: `specs/components/tui_theme.md`, `specs/components/tui_worktree_list.md`

## Step 1: Implement `tui/theme.py`

### ThemeColors class

```python
class ThemeColors:
    """Named color constants for programmatic use."""
    ACCENT: str = "#50fa7b"      # For "New Worktree" row, highlights
    TEXT: str = "#f8f8f2"         # Primary text
    TEXT_DIM: str = "#6272a4"     # Secondary text (timestamps, paths)
    BACKGROUND: str = "#282a36"   # App background
    SELECTED: str = "#44475a"     # Selected row background
    ERROR: str = "#ff5555"        # Error notifications
    SUCCESS: str = "#50fa7b"      # Success notifications
```

### APP_CSS constant

A Textual CSS string with:
- Screen background
- WorktreeList styling
- ListItem styling (normal and highlighted)
- `.new-worktree` class for the "New Worktree" row
- `.worktree-name` and `.worktree-time` classes for worktree rows
- Footer styling with keybinding hints

```css
Screen {
    background: $background;
    align: center middle;
}

WorktreeList {
    width: 100%;
    height: 100%;
}

WorktreeList > ListItem {
    height: 1;
    padding: 0 2;
}

WorktreeList > ListItem.--highlight {
    background: $selected;
}

.new-worktree {
    color: $accent;
    text-style: bold;
}

.worktree-name {
    width: 1fr;
}

.worktree-time {
    color: $text-dim;
    text-align: right;
    width: auto;
}

Footer {
    background: $background;
}
```

## Step 2: Implement `tui/worktree_list.py`

### Relative time helper

```python
def _relative_time(dt: datetime) -> str:
    """Convert datetime to relative time string.

    Examples: "just now", "2 minutes ago", "3 hours ago", "2 days ago"
    """
```

Logic:
- Calculate seconds elapsed since `dt`
- Return appropriate string based on magnitude:
  - < 60 seconds: "just now"
  - < 60 minutes: "X minutes ago" (or "1 minute ago")
  - < 24 hours: "X hours ago" (or "1 hour ago")
  - < 7 days: "X days ago" (or "1 day ago")
  - < 30 days: "X weeks ago" (or "1 week ago")
  - >= 30 days: "X months ago" (or "1 month ago")

### WorktreeListItem class

```python
class WorktreeListItem(ListItem):
    """A single row in the worktree list."""

    worktree: Worktree | None

    def __init__(self, worktree: Worktree | None) -> None:
        """Create a row. worktree=None creates the "New Worktree" row."""
```

- For "New Worktree" row: display `+ New Worktree` with `.new-worktree` class
- For worktree rows: display name (left) and relative time (right)

Use Horizontal layout with:
- Static for name (`.worktree-name`)
- Static for time (`.worktree-time`)

### WorktreeList class

```python
class WorktreeList(ListView):
    """Navigable list of worktrees."""

    def __init__(self, worktrees: list[Worktree]) -> None:
        """Build the list: "New Worktree" row + one row per worktree."""

    @property
    def selected_worktree(self) -> Worktree | None:
        """Return the Worktree for the highlighted row, or None for "New Worktree"."""

    def refresh_worktrees(self, worktrees: list[Worktree]) -> None:
        """Replace list contents. Preserves cursor position if possible."""

    def on_mount(self) -> None:
        """Set cursor to index 1 (most recent worktree) if available."""
```

Implementation details:
- Constructor builds ListItem children from worktrees
- `selected_worktree` reads `self.index` and returns `children[index].worktree`
- `refresh_worktrees` clears children, rebuilds, and clamps index
- `on_mount` sets `self.index = 1` if `len > 1`

## Step 3: Update `tui/__init__.py`

Export the public classes:
```python
from .theme import APP_CSS, ThemeColors
from .worktree_list import WorktreeList, WorktreeListItem
```

## Tests

### `tests/test_tui_theme.py`

| # | Test Case |
|---|-----------|
| 1 | `APP_CSS` is a non-empty string |
| 2 | `ThemeColors` constants are valid hex colors (match `#[0-9a-f]{6}`) |

### `tests/test_tui_worktree_list.py`

| # | Test Case |
|---|-----------|
| 1 | `_relative_time` returns "just now" for recent times |
| 2 | `_relative_time` returns correct minutes/hours/days/weeks/months |
| 3 | List renders "New Worktree" as first item |
| 4 | List renders worktrees in provided order |
| 5 | `selected_worktree` returns None on "New Worktree" row |
| 6 | `selected_worktree` returns correct Worktree |
| 7 | Default cursor position is index 1 (with worktrees) |
| 8 | Default cursor is 0 when no worktrees |
| 9 | `refresh_worktrees` updates list contents |
| 10 | `refresh_worktrees` clamps cursor to bounds |

## Completion Criteria

- [ ] `tui/theme.py` implements `APP_CSS` and `ThemeColors`
- [ ] `tui/worktree_list.py` implements `WorktreeListItem`, `WorktreeList`, and `_relative_time`
- [ ] `tui/__init__.py` exports the public classes
- [ ] All tests pass
- [ ] `uv run ./checks.sh` passes (lint, format, types, tests)
