# Component: `worktree.py`

**Location**: `src/wk/worktree.py`

## Goal

Provide a clean data model for worktrees and encapsulate all interactions with the `wt` CLI tool. Other modules work with `Worktree` dataclass instances — they never call `wt` directly.

## Public Interface

```python
@dataclass(frozen=True)
class Worktree:
    """Represents a single git worktree.

    Attributes:
        name: Worktree identifier (branch name without prefix).
        path: Absolute path to the worktree directory.
        branch: Full branch name.
        created: When the worktree was created.
    """
    name: str
    path: Path
    branch: str
    created: datetime

def list_worktrees() -> list[Worktree]:
    """Fetch all worktrees via `wt list --format json`.

    Returns a list sorted by created date descending (most recent first).
    Raises WtCommandError if the command fails.
    """

def create_worktree(name: str) -> Worktree:
    """Create a new worktree branching off HEAD.

    Runs: `wt switch --create <name> --base=@`
    Returns the newly created Worktree.
    Raises WtCommandError on failure (e.g. name already exists).
    """

def remove_worktree(name: str) -> None:
    """Remove a worktree.

    Runs: `wt remove <name>`
    Raises WtCommandError on failure.
    """

def find_worktree(name: str) -> Worktree | None:
    """Find a worktree by name. Returns None if not found.

    Calls list_worktrees() and searches by name (case-sensitive).
    """

class WtCommandError(Exception):
    """Raised when a `wt` command fails.

    Attributes:
        command: The command that was run.
        stderr: Captured stderr output from the command.
        returncode: Process exit code.
    """
    def __init__(self, command: str, stderr: str, returncode: int): ...
```

## JSON Parsing

`wt list --format json` output structure (expected — to be validated during implementation):

```json
[
  {
    "name": "my-feature",
    "path": "/Users/me/project/.worktrees/my-feature",
    "branch": "my-feature",
    "created": "2025-03-10T14:30:00Z"
  }
]
```

The parser should be defensive: ignore unknown fields, handle missing optional fields gracefully.

## Design Patterns

- **Value Object**: `Worktree` is a frozen dataclass. Immutable, safe to use as dict keys or in sets.
- **Repository pattern**: this module acts as the "repository" for worktree data — the single source of truth, abstracting away the `wt` CLI.
- **Custom exception hierarchy**: `WtCommandError` carries structured info (command, stderr, returncode) for callers to handle or display.

## Subprocess Execution

All commands run via `subprocess.run()` with:
- `capture_output=True`
- `text=True`
- `check=False` (manual error handling via returncode)

Stderr from failed commands is preserved in `WtCommandError` for display to the user.

## Dependencies (internal)

None. Leaf module.

## Dependencies (external)

- `subprocess` — running `wt` commands
- `json` — parsing `wt list --format json`
- `dataclasses` — data model
- `datetime` — timestamp parsing
- `pathlib.Path` — worktree paths

## Testing Strategy

All tests mock `subprocess.run` to avoid requiring `wt` to be installed in the test environment.

### Test Cases

| # | Test Case | Method |
|---|-----------|--------|
| 1 | `list_worktrees` parses valid JSON output | Unit: mock subprocess to return sample JSON, assert correct `Worktree` objects |
| 2 | `list_worktrees` returns sorted by created date desc | Unit: mock with multiple worktrees with different dates, assert order |
| 3 | `list_worktrees` returns empty list when no worktrees | Unit: mock subprocess returning `[]`, assert empty list |
| 4 | `list_worktrees` raises `WtCommandError` on failure | Unit: mock subprocess with non-zero exit, assert exception with stderr |
| 5 | `create_worktree` runs correct command with `--base=@` | Unit: mock subprocess, assert called with `wt switch --create <name> --base=@` |
| 6 | `create_worktree` raises on duplicate name | Unit: mock subprocess failure, assert `WtCommandError` |
| 7 | `remove_worktree` runs `wt remove <name>` | Unit: mock subprocess, assert correct command |
| 8 | `remove_worktree` raises on failure | Unit: mock subprocess failure, assert `WtCommandError` |
| 9 | `find_worktree` returns match by name | Unit: mock `list_worktrees` with 3 entries, search for middle one, assert match |
| 10 | `find_worktree` returns `None` for no match | Unit: mock `list_worktrees`, search for nonexistent name, assert `None` |
| 11 | JSON parser handles unknown fields gracefully | Unit: add extra fields to mock JSON, assert no error |
| 12 | `Worktree` is immutable | Unit: attempt attribute assignment, assert `FrozenInstanceError` |
