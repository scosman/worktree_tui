# Component: `tui/app.py`

**Location**: `src/wk/tui/app.py`

## Goal

The main Textual application. Owns the screen layout, keybindings, and action dispatch. Renders to **stderr** so stdout stays clean for the shell wrapper protocol. Returns shell commands as an exit result for the caller to print.

## Public Interface

```python
class WkApp(App):
    """Main wk TUI application.

    Args:
        worktrees: List of Worktree objects to display.
        config: WkConfig for workspace launching.

    After the app exits, check `shell_commands` for commands to eval.
    """

    shell_commands: list[str]  # Set before exit; caller reads after app.run()

    def __init__(self, worktrees: list[Worktree], config: WkConfig) -> None: ...

def run_app(worktrees: list[Worktree], config: WkConfig) -> list[str]:
    """Convenience function: create and run WkApp, return shell commands.

    Configures the app to render to stderr.
    Returns the shell_commands set by the app (empty list if user quit).
    """
```

## Key Bindings

```python
BINDINGS = [
    Binding("q", "quit", "Quit"),
    Binding("escape", "quit", "Quit", show=False),
    Binding("enter", "select", "Launch"),
    Binding("j", "jump", "Jump"),
    Binding("r", "restart", "Restart"),
    Binding("d", "delete", "Delete"),
    Binding("n", "new", "New"),
]
```

Bindings are shown in a footer bar via Textual's built-in `Footer` widget.

## Action Handlers

### `action_select` (Enter)

- If cursor is on "New Worktree" row: triggers `action_new`.
- If cursor is on a worktree row: calls `actions.action_launch(worktree, config)`, stores result in `shell_commands`, exits app.

### `action_jump` (j)

- Ignored on "New Worktree" row.
- On worktree row: calls `actions.action_jump(worktree)`, stores in `shell_commands`, exits app.

### `action_restart` (r)

- Ignored on "New Worktree" row.
- On worktree row: calls `actions.action_restart(worktree, config)`, stores in `shell_commands`, exits app.

### `action_delete` (d)

- Ignored on "New Worktree" row.
- On worktree row: shows a confirmation dialog.
- On confirm: calls `actions.action_delete(name)`, refreshes the worktree list.
- On cancel: returns to list.
- Error from `wt remove`: displayed as a notification/toast.

### `action_new` (n / Enter on New Worktree)

- Shows an inline text input for the worktree name.
- On submit: calls `actions.action_new(name, config)`, stores launch commands in `shell_commands`, exits app.
- On cancel (Esc): returns to list.
- Error from `wt switch --create`: displayed as a notification/toast.

### `action_quit` (q / Esc)

- Sets `shell_commands = []`, exits app.

## Screen Layout

```
┌──────────────────────────────────────────┐
│  wk - Worktree Manager        (header)   │
├──────────────────────────────────────────┤
│  + New Worktree                          │
│  ▸ my-feature          2 hours ago       │
│    fix-login-bug       3 days ago        │
│    redesign-navbar     1 week ago        │
│                                          │
│                                          │
├──────────────────────────────────────────┤
│  Enter:Launch  j:Jump  r:Restart  d:Delete  n:New  │
└──────────────────────────────────────────┘
```

## stderr Rendering

**Critical implementation detail**: the app must render to stderr so the shell wrapper can capture stdout.

```python
app = WkApp(worktrees, config)
app.run(file=sys.stderr)
```

Textual's `App.run()` accepts a `file` parameter (added in Textual 0.x) that redirects all terminal output to the given file object.

## Design Patterns

- **Mediator**: the app mediates between the list widget, input dialogs, and action functions. Widgets don't call actions directly.
- **Result object**: `shell_commands` acts as a return value from the app. The app sets it before exiting; the caller reads it after `run()` returns.
- **Composition**: the app composes Textual widgets (`WorktreeList`, `Footer`, `Header`, `Input`) rather than inheriting complex behavior.

## Dependencies (internal)

- `actions` — `action_launch`, `action_jump`, `action_restart`, `action_new`, `action_delete`
- `worktree` — `Worktree` dataclass
- `config` — `WkConfig` dataclass
- `tui.worktree_list` — `WorktreeList` widget
- `tui.theme` — CSS styling

## Dependencies (external)

- `textual` — `App`, `Binding`, `Footer`, `Header`, `Input`, `Screen`

## Testing Strategy

Use Textual's built-in testing framework (`App.run_test()`) which provides an async pilot for simulating key presses and asserting widget state.

### Test Cases

| # | Test Case | Method |
|---|-----------|--------|
| 1 | App displays worktrees in correct order | Pilot: launch app with 3 worktrees, assert list items match order (new worktree first, then by date desc) |
| 2 | Default selection is second item (most recent worktree) | Pilot: launch app, assert highlighted index is 1 |
| 3 | Enter on worktree row sets launch commands and exits | Pilot: press Enter on a worktree, assert `shell_commands` contains cd + open_workspace_cmd |
| 4 | Enter on "New Worktree" row opens input | Pilot: move to index 0, press Enter, assert Input widget is visible |
| 5 | `j` on worktree row sets jump commands and exits | Pilot: press `j`, assert `shell_commands` contains cd only |
| 6 | `j` on "New Worktree" row is a no-op | Pilot: move to index 0, press `j`, assert app still running |
| 7 | `r` on worktree row sets restart commands and exits | Pilot: press `r`, assert `shell_commands` contains cd + restart_workspace_cmd |
| 8 | `r` on "New Worktree" row is a no-op | Pilot: move to index 0, press `r`, assert app still running |
| 9 | `d` on worktree row shows confirmation | Pilot: press `d`, assert confirmation dialog visible |
| 10 | Confirming delete removes worktree and refreshes list | Pilot: press `d`, confirm, mock `action_delete`, assert list refreshed with one fewer item |
| 11 | Cancelling delete returns to list | Pilot: press `d`, press Esc, assert list visible, no deletion |
| 12 | `n` opens new worktree input | Pilot: press `n`, assert Input widget visible |
| 13 | Submitting new name creates worktree and exits | Pilot: press `n`, type name, press Enter, mock `action_new`, assert `shell_commands` set |
| 14 | `q` exits with empty commands | Pilot: press `q`, assert `shell_commands` is empty |
| 15 | Esc exits with empty commands | Pilot: press Esc, assert `shell_commands` is empty |
| 16 | Error on delete shows notification | Pilot: mock `action_delete` raising `WtCommandError`, press `d` + confirm, assert error notification shown |
| 17 | Error on new shows notification | Pilot: mock `action_new` raising `WtCommandError`, submit name, assert error notification shown |
| 18 | App with no worktrees shows only "New Worktree" | Pilot: launch with empty list, assert single item |
| 19 | App renders to stderr (stdout stays clean) | Integration: run app, assert nothing written to stdout |
