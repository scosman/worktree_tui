# Phase 7: `tui/app.py`

**Overview**: Implement the main Textual TUI application (`WkApp`) that owns screen layout, keybindings, and action dispatch. Renders to stderr so stdout stays clean for the shell wrapper protocol. Returns shell commands as an exit result.

**Spec file**: `specs/components/tui_app.md`

## Steps

### Step 1: Basic WkApp structure and imports

File: `src/wk/tui/app.py`

Imports needed:
```python
import sys

from textual.app import App, Binding
from textual.containers import Center, Middle
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Label, Static

from wk.actions import action_delete, action_jump, action_launch, action_new, action_restart
from wk.config import WkConfig
from wk.worktree import WtCommandError, Worktree
from wk.tui.theme import APP_CSS
from wk.tui.worktree_list import WorktreeList
```

Class skeleton:
```python
class WkApp(App):
    """Main wk TUI application."""

    CSS = APP_CSS

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit", show=False),
        Binding("enter", "select", "Launch"),
        Binding("j", "jump", "Jump"),
        Binding("r", "restart", "Restart"),
        Binding("d", "delete", "Delete"),
        Binding("n", "new", "New"),
    ]

    shell_commands: list[str]

    def __init__(self, worktrees: list[Worktree], config: WkConfig) -> None:
        super().__init__()
        self._worktrees = worktrees
        self._config = config
        self.shell_commands = []
```

### Step 2: Main screen compose method

The compose method creates the main screen layout:
- Header at top
- WorktreeList in the middle
- Footer at bottom

```python
def compose(self):
    yield Header()
    yield WorktreeList(self._worktrees)
    yield Footer()
```

### Step 3: Action handlers for immediate exit

Implement `action_select`, `action_jump`, `action_restart`:
- Get selected worktree from the list widget
- Call the corresponding action function
- Store result in `shell_commands`
- Exit app

```python
def action_select(self) -> None:
    """Launch selected worktree (Enter)."""
    list_widget = self.query_one(WorktreeList)
    worktree = list_widget.selected_worktree
    if worktree is None:
        # On "New Worktree" row - delegate to action_new
        self._show_new_input()
    else:
        self.shell_commands = action_launch(worktree, self._config)
        self.exit()

def action_jump(self) -> None:
    """Jump to selected worktree (j)."""
    list_widget = self.query_one(WorktreeList)
    worktree = list_widget.selected_worktree
    if worktree is not None:
        self.shell_commands = action_jump(worktree)
        self.exit()

def action_restart(self) -> None:
    """Restart selected worktree (r)."""
    list_widget = self.query_one(WorktreeList)
    worktree = list_widget.selected_worktree
    if worktree is not None:
        self.shell_commands = action_restart(worktree, self._config)
        self.exit()
```

### Step 4: Delete action with confirmation dialog

Implement `action_delete`:
- Show confirmation dialog using Textual's built-in `Question` pattern or custom screen
- On confirm: call `action_delete`, refresh list
- On cancel: return to list
- Handle `WtCommandError` and show notification

Use a simple inline confirmation approach with a ModalScreen.

### Step 5: New worktree action with input dialog

Implement `action_new`:
- Show input dialog for name
- On submit: call `action_new`, store commands, exit
- On cancel (Esc): return to list
- Handle `WtCommandError` and show notification

### Step 6: Quit action

```python
def action_quit(self) -> None:
    """Exit with empty commands."""
    self.shell_commands = []
    self.exit()
```

### Step 7: run_app convenience function

```python
def run_app(worktrees: list[Worktree], config: WkConfig) -> list[str]:
    """Create and run WkApp, return shell commands."""
    app = WkApp(worktrees, config)
    app.run(file=sys.stderr)
    return app.shell_commands
```

### Step 8: Input/Confirmation screens

Create inline input handling:
- For new worktree: show Input widget overlay
- For delete: show confirmation with Yes/No options

Use Textual's pattern of pushing a modal screen or using inline widgets.

## Tests

File: `tests/test_tui_app.py`

Use Textual's `App.run_test()` async pilot for testing:

1. **test_displays_worktrees_in_order** - Launch with 3 worktrees, verify list items match expected order
2. **test_default_selection_is_second_item** - Verify highlighted index is 1 (first worktree, not "New Worktree")
3. **test_enter_on_worktree_launches** - Press Enter on worktree, assert shell_commands has cd + open_workspace_cmd
4. **test_enter_on_new_worktree_opens_input** - Navigate to index 0, press Enter, assert Input visible
5. **test_jump_sets_cd_only** - Press `j`, assert shell_commands has cd only
6. **test_jump_on_new_worktree_noop** - Navigate to index 0, press `j`, verify app still running
7. **test_restart_sets_commands** - Press `r`, assert shell_commands has cd + restart_workspace_cmd
8. **test_restart_on_new_worktree_noop** - Navigate to index 0, press `r`, verify app still running
9. **test_delete_shows_confirmation** - Press `d`, assert confirmation visible
10. **test_delete_confirm_refreshes_list** - Mock action_delete, press d + confirm, verify list refreshed
11. **test_delete_cancel_returns** - Press d, press Esc, verify no deletion
12. **test_new_opens_input** - Press `n`, assert Input visible
13. **test_new_submit_creates_and_exits** - Press n, type name, Enter, mock action_new, verify shell_commands set
14. **test_quit_exits_empty** - Press `q`, assert shell_commands is empty
15. **test_escape_exits_empty** - Press Escape, assert shell_commands is empty
16. **test_delete_error_shows_notification** - Mock action_delete raising WtCommandError, verify error shown
17. **test_new_error_shows_notification** - Mock action_new raising WtCommandError, verify error shown
18. **test_empty_worktrees_shows_new_only** - Launch with empty list, verify single "New Worktree" item

## Completion Criteria

- [ ] `WkApp` class with all keybindings implemented
- [ ] `action_select`, `action_jump`, `action_restart`, `action_delete`, `action_new`, `action_quit` handlers
- [ ] Input dialog for new worktree name
- [ ] Confirmation dialog for delete
- [ ] Error notifications for failed operations
- [ ] `run_app()` function that renders to stderr
- [ ] All tests pass
- [ ] `uv run ./checks.sh` passes (lint, format, types, tests)
