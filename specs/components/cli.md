# Component: `cli.py`

**Location**: `src/wk/cli.py`

## Goal

Single entry point for the entire `wk` tool. Parses arguments, enforces the shell wrapper requirement, and routes to the correct action (TUI or CLI command). Keeps routing logic thin — delegates all real work to other modules.

## Public Interface

```python
def main() -> None:
    """Entry point registered in pyproject.toml as `wk = "wk.cli:main"`.

    Parses sys.argv, enforces wrapper check, routes to the appropriate action.
    Calls sys.exit() on errors.
    """
```

No other public functions. This module is the top-level orchestrator, not a library.

## Routing Rules

| Command              | Requires Wrapper | Action                                         |
|----------------------|------------------|-------------------------------------------------|
| `wk`                 | Yes              | Launch TUI, print returned shell commands       |
| `wk init zsh`        | No               | Print shell wrapper function to stdout, exit    |
| `wk new <name>`      | Yes              | Create worktree + print launch commands         |
| `wk <name>`          | Yes              | Look up worktree + print launch commands        |

### Argument Parsing

Use `sys.argv` directly (no framework). The command set is small and fixed:

- `len(argv) == 1` → TUI mode
- `argv[1] == "init"` and `argv[2] == "zsh"` → print wrapper
- `argv[1] == "new"` and `argv[2]` exists → create worktree
- `argv[1]` is anything else → treat as worktree name to launch

Unknown subcommands (e.g. `wk init bash`, `wk new` with no name) print a usage message to stderr and exit non-zero.

### Wrapper Enforcement

Before any action **except `wk init zsh`**:

1. Call `shell.is_wrapped()`.
2. If `False`: call `shell.run_setup_flow()`, then `sys.exit(1)`.

### Output Protocol

After the TUI or CLI action completes, `main()` receives a `list[str]` of shell commands (possibly empty). It calls `shell.print_shell_commands(commands)` which writes them to stdout for the wrapper to eval.

All user-facing messages (errors, prompts) go to **stderr** only.

## Design Patterns

- **Front Controller**: single entry point routing to handlers.
- **Thin orchestrator**: no business logic in `main()` — it only wires together shell, config, worktree, actions, and TUI modules.

## Dependencies (internal)

- `shell` — wrapper check, setup flow, command output
- `config` — load config (for CLI actions that need `open_workspace_cmd`)
- `worktree` — find/create worktrees (for CLI commands)
- `actions` — build shell command lists
- `tui.app` — launch TUI

## Testing Strategy

`cli.py` is primarily routing glue. Test via integration-style tests with subprocess invocations.

### Test Cases

| # | Test Case | Method |
|---|-----------|--------|
| 1 | `wk init zsh` prints a valid shell function to stdout | Subprocess: run `wk init zsh`, assert stdout contains the wrapper function, assert exit code 0 |
| 2 | `wk init zsh` works **without** the wrapper env var | Subprocess: run without `__WK_WRAPPED`, assert it still succeeds (no wrapper required for `init`) |
| 3 | `wk` without wrapper triggers setup flow | Subprocess: run without `__WK_WRAPPED`, assert stderr contains the setup prompt, assert exit code non-zero |
| 4 | `wk new` with no name prints usage to stderr | Subprocess: assert stderr contains usage info, exit code non-zero |
| 5 | `wk new myfeature` with wrapper creates and launches | Mock `worktree.create_worktree` + `actions.action_new`, verify stdout contains shell commands |
| 6 | `wk myfeature` with wrapper launches existing worktree | Mock `worktree.find_worktree` + `actions.action_launch`, verify stdout |
| 7 | `wk nonexistent` with wrapper prints error | Mock `worktree.find_worktree` returning `None`, assert stderr contains error, exit code non-zero |
| 8 | `wk init bash` prints unsupported error | Assert stderr contains "unsupported" or similar, exit code non-zero |
