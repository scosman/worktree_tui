# Functionality Spec: `wk`

A polished TUI and CLI for managing git worktrees via [Worktrunk](https://worktrunk.dev/).

## Shell Wrapper Requirement

`wk` needs to change the parent shell's working directory (for Jump and Launch actions). This requires a shell wrapper function.

### Detection & Setup Flow

1. The shell wrapper sets an env var (e.g. `__WK_WRAPPED=1`) before invoking the Python program.
2. On every invocation, the Python program checks for this env var.
3. If **not wrapped**: the TUI does not launch. Instead:
   - Detect if the user's shell is zsh (via `$SHELL`).
   - Prompt: *"wk requires a shell wrapper to function. Install it now? (y/n)"*
   - **If yes**: show exactly what will be appended to `~/.zshrc`, ask for confirmation, write it, then instruct the user to run `source ~/.zshrc`.
   - **If no**: print the manual setup instructions and exit.
4. If **wrapped**: proceed normally.

### Shell Wrapper Function (zsh)

The wrapper function:
- Sets `__WK_WRAPPED=1`
- Captures stdout from the Python program into a variable
- Evals the captured output (which may contain `cd` commands or other shell commands)

Installed via `eval "$(wk init zsh)"` in `~/.zshrc`, or by the auto-install flow above.

### Communication Protocol

The Python program communicates shell actions by printing commands to stdout:
- **Jump**: prints `cd /path/to/worktree`
- **Launch**: prints `cd /path/to/worktree && .config/wt/start.sh` (or whatever `OPEN_WORKSPACE_CMD` is configured)
- **Restart**: prints `cd /path/to/worktree && <RESTART_WORKSPACE_CMD>` (runs the restart command in the worktree directory)
- **No action** (e.g. user quits): prints nothing

Textual uses the alternate screen buffer, so stdout is clean after the TUI exits.

## TUI (Interactive Mode)

Launched by running `wk` with no arguments (or no matching CLI command).

### Main Screen

A keyboard-navigable list of worktrees.

**List contents:**
1. First item: **"+ New Worktree"** (always present)
2. Remaining items: all worktrees from `wt list --format json`, sorted by **created date descending** (most recent first)

**Default selection:** the second item (most recent worktree), not "New Worktree".

### Keyboard Shortcuts (shown in a footer bar)

| Key       | Action                    |
|-----------|---------------------------|
| `Enter`   | Launch workspace          |
| `j`       | Jump (cd to worktree)     |
| `r`       | Restart workspace         |
| `d`       | Delete worktree           |
| `n`       | New worktree              |
| `q`/`Esc` | Quit                      |

- On "New Worktree" row: `Enter` also triggers the new worktree flow.
- `j`, `r`, `d`, `Enter` (Launch) only apply to existing worktree rows.

### New Worktree Flow

1. User is prompted for a worktree/branch name (inline text input).
2. `wk` creates the worktree: `wt switch --create <name> --base=@`
3. On success, launches the workspace (cd + OPEN_WORKSPACE_CMD).

**Base branch**: always branches off **HEAD** (the current branch) using `--base=@`, not main.

### Delete Flow

1. User presses `d` on a worktree row.
2. Confirmation prompt: *"Delete worktree '<name>'? (y/n)"*
3. On confirm: runs `wt remove <name>`.
4. Refreshes the list.

### Launch Flow

1. TUI exits cleanly.
2. Prints shell commands to stdout: `cd <worktree_path>` then the `OPEN_WORKSPACE_CMD` (if configured).
3. Shell wrapper evals the output.

### Jump Flow

1. TUI exits cleanly.
2. Prints `cd <worktree_path>` to stdout.
3. Shell wrapper evals the output.

### Restart Flow

1. TUI exits cleanly.
2. Prints shell commands to stdout: `cd <worktree_path>` then the `RESTART_WORKSPACE_CMD` (if configured).
3. Shell wrapper evals the output.
4. If `restart_workspace_cmd` is not configured, this action is a no-op (same as Jump).

## CLI Commands

### `wk new <FEATURE_NAME>`

Creates a new worktree branching off the current branch, then launches it.

Equivalent to: `wt switch --create <name> --base=@ -x <OPEN_WORKSPACE_CMD>`

Outputs shell commands (cd + launch) for the wrapper to eval.

### `wk <FEATURE_NAME>`

Launches an existing worktree by name.

Outputs shell commands (cd + launch) for the wrapper to eval.

If no worktree matches `<FEATURE_NAME>`, prints an error and exits non-zero.

### `wk init zsh`

Prints the shell wrapper function definition to stdout. Used for manual setup:

```
eval "$(wk init zsh)"
```

## Configuration

Config file: `.config/wk.yml` (relative to the **git repo root**).

```yaml
open_workspace_cmd: ".config/wt/start.sh"
restart_workspace_cmd: ".config/wt/start.sh"
```

- `open_workspace_cmd`: shell command to run when launching a worktree workspace. Executed in the worktree directory. If missing, Launch just does `cd`.
- `restart_workspace_cmd`: shell command to run when restarting a worktree workspace. Executed in the worktree directory. If missing, Restart falls back to Jump (just `cd`).

## Data Source

Worktree list is fetched via `wt list --format json`.

Expected fields used:
- Worktree name/branch
- Worktree path
- Created date (for sorting)

## Supported Shells

- **zsh only** (for now)

## Tech Stack

- **Language**: Python 3.13+
- **TUI framework**: Textual
- **Package manager**: uv
- **CLI entry point**: `wk`
