# Phase 3: worktree.py

**Spec Reference**: `specs/components/worktree.md`

## Overview

Implement the `Worktree` dataclass and functions to interact with the `wt` CLI tool. This module is a "leaf" module with no internal dependencies — it encapsulates all subprocess calls to `wt` and provides a clean data model for other components to consume.

## Steps

### Step 1: Implement WtCommandError Exception

**File**: `src/wk/worktree.py`

Create a custom exception class that captures structured error information:

```python
class WtCommandError(Exception):
    """Raised when a `wt` command fails.

    Attributes:
        command: The command that was run.
        stderr: Captured stderr output from the command.
        returncode: Process exit code.
    """
    def __init__(self, command: str, stderr: str, returncode: int) -> None:
        self.command = command
        self.stderr = stderr
        self.returncode = returncode
        super().__init__(f"Command '{command}' failed with exit code {returncode}: {stderr}")
```

### Step 2: Implement Worktree Dataclass

**File**: `src/wk/worktree.py`

Create a frozen dataclass for immutable worktree representation:

```python
@dataclass(frozen=True)
class Worktree:
    """Represents a single git worktree."""
    name: str
    path: Path
    branch: str
    created: datetime
```

### Step 3: Implement list_worktrees()

**File**: `src/wk/worktree.py`

- Run `wt list --format json` via subprocess
- Parse JSON output into `Worktree` objects
- Sort by `created` date descending (most recent first)
- Raise `WtCommandError` on non-zero exit code

Key implementation details:
- Use `subprocess.run(capture_output=True, text=True, check=False)`
- Parse datetime from ISO format string
- Handle empty list case (return `[]`)
- Be defensive: ignore unknown JSON fields

### Step 4: Implement create_worktree()

**File**: `src/wk/worktree.py`

- Run `wt switch --create <name> --base=@`
- Return the newly created `Worktree` by calling `find_worktree(name)` after creation
- Raise `WtCommandError` on failure

### Step 5: Implement remove_worktree()

**File**: `src/wk/worktree.py`

- Run `wt remove <name>`
- Raise `WtCommandError` on failure
- Return `None` on success

### Step 6: Implement find_worktree()

**File**: `src/wk/worktree.py`

- Call `list_worktrees()` and search by name (case-sensitive)
- Return `Worktree` if found, `None` otherwise

## Tests

**File**: `tests/test_worktree.py`

All tests mock `subprocess.run` to avoid requiring `wt` in the test environment.

| Test Name | Description |
|-----------|-------------|
| `test_list_worktrees_parses_valid_json` | Mock subprocess returns sample JSON, assert correct `Worktree` objects |
| `test_list_worktrees_sorted_by_created_desc` | Mock with multiple worktrees, verify newest first |
| `test_list_worktrees_empty_list` | Mock returns `[]`, assert empty list |
| `test_list_worktrees_raises_on_failure` | Mock non-zero exit, assert `WtCommandError` with stderr |
| `test_create_worktree_runs_correct_command` | Mock subprocess, verify `wt switch --create <name> --base=@` |
| `test_create_worktree_raises_on_duplicate` | Mock failure, assert `WtCommandError` |
| `test_remove_worktree_runs_correct_command` | Mock subprocess, verify `wt remove <name>` |
| `test_remove_worktree_raises_on_failure` | Mock failure, assert `WtCommandError` |
| `test_find_worktree_returns_match` | Mock list with 3 entries, search for middle one |
| `test_find_worktree_returns_none` | Mock list, search nonexistent name |
| `test_json_parser_handles_unknown_fields` | Add extra fields to mock JSON, no error |
| `test_worktree_is_immutable` | Attempt attribute assignment, expect `FrozenInstanceError` |

## Completion Criteria

- [ ] `WtCommandError` exception class implemented
- [ ] `Worktree` frozen dataclass implemented
- [ ] `list_worktrees()` implemented with sorting
- [ ] `create_worktree()` implemented
- [ ] `remove_worktree()` implemented
- [ ] `find_worktree()` implemented
- [ ] All 12 test cases passing
- [ ] `uv run ./checks.sh` passes (format, lint, types, tests)
