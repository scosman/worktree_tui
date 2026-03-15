# Component: `actions.py`

**Location**: `src/wk/actions.py`

## Goal

Shared business logic for all user actions (launch, jump, restart, new, delete). Each action function encapsulates the full workflow and returns shell commands as data — never writing to stdout itself. Used by both the TUI and CLI code paths.

## Public Interface

```python
def action_launch(worktree: Worktree, config: WkConfig) -> list[str]:
    """Build shell commands to launch a worktree workspace.

    Returns:
        - ["cd <path>"] if no open_workspace_cmd configured.
        - ["cd <path>", "<open_workspace_cmd>"] if configured.
    """

def action_jump(worktree: Worktree) -> list[str]:
    """Build shell commands to cd into a worktree.

    Returns:
        - ["cd <path>"]
    """

def action_restart(worktree: Worktree, config: WkConfig) -> list[str]:
    """Build shell commands to restart a worktree workspace.

    Returns:
        - ["cd <path>", "<restart_workspace_cmd>"] if configured.
        - ["cd <path>"] if restart_workspace_cmd is not configured (fallback to jump).
    """

def action_new(name: str, config: WkConfig) -> list[str]:
    """Create a new worktree off HEAD and return launch commands.

    1. Calls worktree.create_worktree(name).
    2. Calls action_launch() with the new worktree.
    Returns the same commands as action_launch.
    Raises WtCommandError if creation fails.
    """

def action_delete(name: str) -> None:
    """Delete a worktree.

    Calls worktree.remove_worktree(name).
    Raises WtCommandError if removal fails.
    Returns nothing — no shell commands needed (caller stays in TUI or exits).
    """
```

## Command Construction

Shell commands are plain strings. The `cd` command uses the worktree's absolute path, shell-quoted to handle paths with spaces:

```python
f"cd {shlex.quote(str(worktree.path))}"
```

The `open_workspace_cmd` is appended as a separate command (not joined with `&&`). Each command is a separate line in stdout, and the wrapper evals them sequentially.

## Design Patterns

- **Pure functions (nearly)**: `action_launch`, `action_jump`, and `action_restart` are pure — no side effects, deterministic output from inputs. `action_new` and `action_delete` have side effects (creating/removing worktrees) but still return data rather than printing.
- **Command pattern (data)**: actions return command lists as data, not execute them. The caller decides when/how to execute (print to stdout for wrapper eval).
- **Single Responsibility**: this module only builds command lists and delegates subprocess work to `worktree.py`.

## Dependencies (internal)

- `worktree` — `Worktree` dataclass, `create_worktree()`, `remove_worktree()`
- `config` — `WkConfig` dataclass (passed in, not loaded here)

## Dependencies (external)

- `shlex` — shell-safe quoting of paths

## Testing Strategy

### Test Cases

| # | Test Case | Method |
|---|-----------|--------|
| 1 | `action_launch` with `open_workspace_cmd` returns cd + cmd | Unit: create `Worktree` and `WkConfig(open_workspace_cmd="start.sh")`, assert `["cd <path>", "start.sh"]` |
| 2 | `action_launch` without `open_workspace_cmd` returns cd only | Unit: `WkConfig(open_workspace_cmd=None)`, assert `["cd <path>"]` |
| 3 | `action_launch` shell-quotes paths with spaces | Unit: `Worktree(path="/my path/tree")`, assert cd command is properly quoted |
| 4 | `action_jump` returns cd command | Unit: assert `["cd <path>"]` |
| 5 | `action_jump` shell-quotes paths | Unit: path with spaces, assert proper quoting |
| 6 | `action_restart` with `restart_workspace_cmd` returns cd + cmd | Unit: `WkConfig(restart_workspace_cmd="start.sh")`, assert `["cd <path>", "start.sh"]` |
| 7 | `action_restart` without `restart_workspace_cmd` returns cd only | Unit: `WkConfig(restart_workspace_cmd=None)`, assert `["cd <path>"]` (fallback to jump) |
| 8 | `action_restart` shell-quotes paths with spaces | Unit: path with spaces, assert proper quoting |
| 9 | `action_new` calls `create_worktree` then returns launch commands | Unit: mock `create_worktree`, assert it was called with name, assert return matches `action_launch` output |
| 10 | `action_new` propagates `WtCommandError` on creation failure | Unit: mock `create_worktree` raising `WtCommandError`, assert it propagates |
| 11 | `action_delete` calls `remove_worktree` | Unit: mock `remove_worktree`, assert called with name |
| 12 | `action_delete` propagates `WtCommandError` on failure | Unit: mock `remove_worktree` raising, assert propagation |
| 13 | `action_delete` returns `None` | Unit: assert return value is `None` |
