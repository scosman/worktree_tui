# Component: `tui/worktree_list.py`

**Location**: `src/wk/tui/worktree_list.py`

## Goal

A Textual list widget that displays worktrees with a "New Worktree" entry at the top. Responsible only for rendering and selection — all action logic lives in the app.

## Public Interface

```python
class WorktreeListItem(ListItem):
    """A single row in the worktree list.

    Attributes:
        worktree: The Worktree object for this row, or None for the "New Worktree" row.
    """
    worktree: Worktree | None

    def __init__(self, worktree: Worktree | None) -> None: ...

class WorktreeList(ListView):
    """Navigable list of worktrees.

    Emits no custom messages — the parent app reads the selected item
    and decides what to do.
    """

    def __init__(self, worktrees: list[Worktree]) -> None:
        """Build the list: "New Worktree" row + one row per worktree."""

    @property
    def selected_worktree(self) -> Worktree | None:
        """Return the Worktree for the currently highlighted row.

        Returns None if the "New Worktree" row is selected.
        """

    def refresh_worktrees(self, worktrees: list[Worktree]) -> None:
        """Replace the list contents with a new set of worktrees.

        Preserves cursor position if possible (clamps to list bounds).
        Used after delete to refresh without full app restart.
        """
```

## Row Rendering

### "New Worktree" Row (index 0)

```
  + New Worktree
```

Visually distinct: different color (accent/green), `+` prefix. Uses theme styling.

### Worktree Rows (index 1+)

```
  my-feature          2 hours ago
```

Each row displays:
- **Name**: the worktree name, left-aligned
- **Relative time**: created date as relative time (e.g. "2 hours ago", "3 days ago"), right-aligned or after padding

Relative time formatting: use a simple helper function (not a dependency). Levels: "just now", "X minutes ago", "X hours ago", "X days ago", "X weeks ago", "X months ago".

### Selected Row Indicator

The currently highlighted row uses Textual's built-in `ListView` cursor styling (highlight bar). Additionally, a `▸` marker on the selected row for extra clarity.

## Default Cursor Position

On mount, the cursor is set to index 1 (the most recent worktree), skipping the "New Worktree" row. If there are no worktrees, cursor stays at index 0.

```python
def on_mount(self) -> None:
    if len(self.children) > 1:
        self.index = 1
```

## Design Patterns

- **Composite widget**: extends `ListView`, composes `ListItem` children.
- **Data-driven rendering**: the widget receives a `list[Worktree]` and builds its children from it. No data fetching inside the widget.
- **Separation of concerns**: the widget owns rendering and selection state only. It does not handle keypresses for actions (j/d/n) — those are handled by the app via bindings.

## Dependencies (internal)

- `worktree` — `Worktree` dataclass (for type annotation and data access)
- `tui.theme` — CSS class names and styling constants

## Dependencies (external)

- `textual.widgets` — `ListView`, `ListItem`, `Label`, `Static`
- `datetime` — relative time calculation

## Testing Strategy

### Test Cases

| # | Test Case | Method |
|---|-----------|--------|
| 1 | List renders "New Worktree" as first item | Pilot: mount widget with 2 worktrees, assert first child is the "New" row |
| 2 | List renders worktrees in provided order | Pilot: pass 3 worktrees, assert row names match (order preserved from input — caller sorts) |
| 3 | `selected_worktree` returns `None` on "New Worktree" row | Pilot: set index to 0, assert `selected_worktree is None` |
| 4 | `selected_worktree` returns correct `Worktree` | Pilot: set index to 1, assert `selected_worktree == worktrees[0]` |
| 5 | Default cursor position is index 1 | Pilot: mount with worktrees, assert `index == 1` after mount |
| 6 | Default cursor is 0 when no worktrees | Pilot: mount with empty list, assert `index == 0` |
| 7 | `refresh_worktrees` updates list contents | Pilot: initial 3 worktrees, call refresh with 2, assert 3 rows total (1 new + 2 worktrees) |
| 8 | `refresh_worktrees` clamps cursor | Pilot: cursor at index 3 (4 items), refresh to 2 items (3 rows), assert cursor clamped |
| 9 | Relative time displays correctly | Unit: test the time formatter — datetime 2 hours ago → "2 hours ago", 3 days → "3 days ago", etc. |
| 10 | "New Worktree" row has distinct styling | Pilot: assert the first row has the accent CSS class |
| 11 | Worktree name and time are visible in row | Pilot: assert row content contains the worktree name and a relative time string |
