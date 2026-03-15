# Phase 5: actions.py

**Spec Reference**: `specs/components/actions.md`

## Overview

Implement shared business logic for all user actions (launch, jump, restart, new, delete). Each action function encapsulates the full workflow and returns shell commands as data — never writing to stdout itself. Used by both the TUI and CLI code paths.

## Steps

### Step 1: Create actions.py with imports and action_launch()

**File**: `src/wk/actions.py`

Implement `action_launch()`:

```python
import shlex
from wk.config import WkConfig
from wk.worktree import Worktree, WtCommandError, create_worktree, remove_worktree

def action_launch(worktree: Worktree, config: WkConfig) -> list[str]:
    """Build shell commands to launch a worktree workspace.

    Returns:
        - ["cd <path>"] if no open_workspace_cmd configured.
        - ["cd <path>", "<open_workspace_cmd>"] if configured.
    """
    cd_cmd = f"cd {shlex.quote(str(worktree.path))}"
    if config.open_workspace_cmd:
        return [cd_cmd, config.open_workspace_cmd]
    return [cd_cmd]
```

### Step 2: Implement action_jump()

**File**: `src/wk/actions.py`

```python
def action_jump(worktree: Worktree) -> list[str]:
    """Build shell commands to cd into a worktree.

    Returns:
        - ["cd <path>"]
    """
    return [f"cd {shlex.quote(str(worktree.path))}"]
```

### Step 3: Implement action_restart()

**File**: `src/wk/actions.py`

```python
def action_restart(worktree: Worktree, config: WkConfig) -> list[str]:
    """Build shell commands to restart a worktree workspace.

    Returns:
        - ["cd <path>", "<restart_workspace_cmd>"] if configured.
        - ["cd <path>"] if restart_workspace_cmd is not configured (fallback to jump).
    """
    cd_cmd = f"cd {shlex.quote(str(worktree.path))}"
    if config.restart_workspace_cmd:
        return [cd_cmd, config.restart_workspace_cmd]
    return [cd_cmd]
```

### Step 4: Implement action_new()

**File**: `src/wk/actions.py`

```python
def action_new(name: str, config: WkConfig) -> list[str]:
    """Create a new worktree off HEAD and return launch commands.

    1. Calls create_worktree(name).
    2. Calls action_launch() with the new worktree.
    Returns the same commands as action_launch.
    Raises WtCommandError if creation fails.
    """
    worktree = create_worktree(name)
    return action_launch(worktree, config)
```

### Step 5: Implement action_delete()

**File**: `src/wk/actions.py`

```python
def action_delete(name: str) -> None:
    """Delete a worktree.

    Calls remove_worktree(name).
    Raises WtCommandError if removal fails.
    Returns nothing — no shell commands needed (caller stays in TUI or exits).
    """
    remove_worktree(name)
```

## Tests

**File**: `tests/test_actions.py`

| Test Name | Description |
|-----------|-------------|
| `test_action_launch_with_open_cmd` | Create `Worktree` and `WkConfig(open_workspace_cmd="start.sh")`, assert `["cd <path>", "start.sh"]` |
| `test_action_launch_without_open_cmd` | `WkConfig(open_workspace_cmd=None)`, assert `["cd <path>"]` |
| `test_action_launch_quotes_paths_with_spaces` | `Worktree(path="/my path/tree")`, assert cd command is properly quoted |
| `test_action_jump_returns_cd_command` | Assert `["cd <path>"]` |
| `test_action_jump_quotes_paths` | Path with spaces, assert proper quoting |
| `test_action_restart_with_restart_cmd` | `WkConfig(restart_workspace_cmd="start.sh")`, assert `["cd <path>", "start.sh"]` |
| `test_action_restart_without_restart_cmd` | `WkConfig(restart_workspace_cmd=None)`, assert `["cd <path>"]` (fallback to jump) |
| `test_action_restart_quotes_paths_with_spaces` | Path with spaces, assert proper quoting |
| `test_action_new_calls_create_then_returns_launch` | Mock `create_worktree`, assert it was called with name, assert return matches `action_launch` output |
| `test_action_new_propagates_wt_command_error` | Mock `create_worktree` raising `WtCommandError`, assert it propagates |
| `test_action_delete_calls_remove_worktree` | Mock `remove_worktree`, assert called with name |
| `test_action_delete_propagates_wt_command_error` | Mock `remove_worktree` raising, assert propagation |
| `test_action_delete_returns_none` | Assert return value is `None` |

## Completion Criteria

- [ ] `action_launch()` implemented
- [ ] `action_jump()` implemented
- [ ] `action_restart()` implemented
- [ ] `action_new()` implemented
- [ ] `action_delete()` implemented
- [ ] All test cases passing
- [ ] `uv run ./checks.sh` passes (format, lint, types, tests)
