# Phase 8: cli.py

**Overview**: Implement the single entry point for the `wk` tool. Parses arguments, enforces shell wrapper requirement, and routes to the correct action.

**Spec**: `specs/components/cli.md`

## Steps

### Step 1: Implement main() with argument routing

File: `src/wk/cli.py`

Replace the stub with full implementation:

```python
def main() -> None:
    """Entry point - parses sys.argv, enforces wrapper, routes to action."""
    argv = sys.argv

    # Route based on arguments
    if len(argv) == 1:
        # No args: TUI mode
        _require_wrapper()
        _run_tui()
    elif argv[1] == "init":
        # init zsh: print wrapper (no wrapper required)
        if len(argv) < 3 or argv[2] != "zsh":
            _usage_error("Usage: wk init zsh")
        print(shell.generate_wrapper_zsh())
    elif argv[1] == "new":
        # new <name>: create and launch worktree
        _require_wrapper()
        if len(argv) < 3:
            _usage_error("Usage: wk new <name>")
        _cli_new(argv[2])
    else:
        # <name>: launch existing worktree
        _require_wrapper()
        _cli_launch(argv[1])
```

### Step 2: Implement helper functions

- `_require_wrapper()`: Check `shell.is_wrapped()`, call `shell.run_setup_flow()` and exit if not wrapped
- `_usage_error(message)`: Print to stderr, exit non-zero
- `_run_tui()`: Load config, get worktrees, run app, print commands
- `_cli_new(name)`: Load config, call `action_new()`, print commands
- `_cli_launch(name)`: Load config, find worktree, call `action_launch()`, print commands

### Step 3: Error handling

- `wk init bash` → stderr "Only zsh is supported"
- `wk new` (no name) → stderr "Usage: wk new <name>"
- `wk <nonexistent>` → stderr "Worktree '<name>' not found"
- Catch `ConfigError` and `WtCommandError`, print to stderr, exit non-zero

## Tests

File: `tests/test_cli.py`

| # | Test | Method |
|---|------|--------|
| 1 | `wk init zsh` prints wrapper to stdout | Subprocess, assert stdout contains "wk()" |
| 2 | `wk init zsh` works without wrapper env var | Subprocess without `__WK_WRAPPED`, assert exit 0 |
| 3 | `wk` without wrapper triggers setup flow | Subprocess, assert stderr contains "Shell Wrapper Setup" |
| 4 | `wk init bash` prints error | Subprocess, assert stderr contains "zsh", exit non-zero |
| 5 | `wk new` without name prints usage | Subprocess, assert stderr contains "Usage", exit non-zero |
| 6 | `wk new <name>` with wrapper creates and launches | Mock `create_worktree`, `action_new` |
| 7 | `wk <name>` with wrapper launches | Mock `find_worktree`, `action_launch` |
| 8 | `wk <nonexistent>` prints error | Mock `find_worktree` returns None |

## Completion Criteria

- [ ] `cli.py` implements full routing logic
- [ ] All 8 test cases pass
- [ ] `uv run ./checks.sh` passes (lint, format, types, tests)
- [ ] Manual test: `wk init zsh` outputs valid shell function
