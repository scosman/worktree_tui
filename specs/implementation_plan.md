# Implementation Plan

## Step 1: Project Scaffolding

- [x] Configure `pyproject.toml` (src layout, entry point `wk = "wk.cli:main"`, dependencies: textual, pyyaml)
- [x] Create `src/wk/` package structure with `__init__.py` files
- [x] Set up test infrastructure (pytest, test directory)
- [x] Verify `uv run wk` invokes the entry point

## Step 2: `config.py`

- [x] Implement `WkConfig`, `ConfigError`, `find_repo_root()`, `load_config()`
- [x] Tests (spec: `specs/components/config.md`)

## Step 3: `worktree.py`

- [x] Implement `Worktree`, `WtCommandError`, `list_worktrees()`, `create_worktree()`, `remove_worktree()`, `find_worktree()`
- [x] Tests (spec: `specs/components/worktree.md`)

## Step 4: `shell.py`

- [x] Implement `is_wrapped()`, `generate_wrapper_zsh()`, `print_shell_commands()`, `run_setup_flow()`
- [x] Tests (spec: `specs/components/shell.md`)

## Step 5: `actions.py`

- [x] Implement `action_launch()`, `action_jump()`, `action_restart()`, `action_new()`, `action_delete()`
- [x] Tests (spec: `specs/components/actions.md`)
- [x] `uv run ./checks.sh` passes (lint, format, types, tests)

> Depends on: config, worktree

## Step 6: `tui/theme.py` and `tui/worktree_list.py`

- [x] Implement `APP_CSS`, `ThemeColors`
- [x] Implement `WorktreeListItem`, `WorktreeList`, relative time helper
- [x] Tests (specs: `specs/components/tui_theme.md`, `specs/components/tui_worktree_list.md`)
- [x] `uv run ./checks.sh` passes (lint, format, types, tests)

> Depends on: worktree

## Step 7: `tui/app.py`

- [x] Implement `WkApp`, `run_app()`, all action handlers, stderr rendering
- [x] Tests (spec: `specs/components/tui_app.md`)
- [x] `uv run ./checks.sh` passes (lint, format, types, tests)

> Depends on: actions, worktree_list, theme

## Step 8: `cli.py`

- [x] Implement `main()` with arg routing, wrapper enforcement, output protocol
- [x] Tests (spec: `specs/components/cli.md`)
- [x] End-to-end manual test: `wk init zsh`, wrapper install, TUI launch, CLI commands

> Depends on: all other components

## Step 9: Custom Commands

- [x] Add `CustomCommand` dataclass and parsing to `config.py`
- [x] Add `action_custom_command()` to `actions.py`
- [x] Add dynamic custom command bindings and handlers to `tui/app.py` (including confirmation dialog)
- [x] Tests for config parsing, action, and TUI behavior
- [x] `uv run ./checks.sh` passes (lint, format, types, tests)

> Depends on: config, actions, tui/app

## Step 10: IPC + Zellij/Tmux Infrastructure

- [x] Implement `ipc.py` (Selection, write_selection, read_selection, clear_state, state_file_path)
- [x] Implement `layout.py` (generate_zellij_layout, launch_zellij, launch_tmux_workspace, tmux_capture_pane)
- [x] Tests for IPC roundtrip, layout generation, tool availability checks

## Step 11: Persistent Selector Mode

- [x] Add `wk selector` subcommand to `cli.py`
- [x] Add `persistent=True` mode to `tui/app.py` (no exit on select, IPC write on highlight)
- [x] Add `HighlightChanged` message to `tui/worktree_list.py`
- [x] Tests for selector CLI routing and persistent mode

> Depends on: IPC, tui/app

## Step 12: Diff Pane

- [x] Implement `panes/diff_pane.py` (polls IPC, renders git diff)
- [x] Add `wk diff-pane` subcommand to `cli.py`
- [x] Tests for diff pane

> Depends on: IPC

## Step 13: Zellij Launch + Tmux Workspace

- [x] Change bare `wk` to launch Zellij when available (falls back to classic TUI)
- [x] Add `wk workspace` subcommand for tmux session management
- [x] Tests for Zellij launch and fallback behavior

> Depends on: layout, selector, diff-pane

## Step 14: CI Status Column

- [x] Implement `status/ci.py` (CIStatus, fetch_ci_statuses, CIStatusCache)
- [x] Add `RowStatus` dataclass and columnar layout to `tui/worktree_list.py`
- [x] Add periodic refresh timer to `tui/app.py`
- [x] Add column CSS to `tui/theme.py`
- [x] Tests for CI status parsing and caching

> Depends on: worktree_list, app

## Step 15: Linear Status Column

- [x] Implement `status/linear.py` (LinearStatus, extract_ticket_id, fetch_linear_statuses, LinearStatusCache)
- [x] Add `linear_api_key`, `linear_team_prefix` to `config.py`
- [x] Integrate Linear status into app refresh cycle
- [x] Tests for Linear ticket extraction and API mocking

> Depends on: config, worktree_list, app

## Step 16: Agent Status Column

- [x] Implement `status/agent.py` (detect_agent_state, pattern matching for Claude Code)
- [x] Add 5-second agent refresh timer to `tui/app.py`
- [x] Tests for agent state pattern matching

> Depends on: layout (tmux), worktree_list, app

## Step 17: ADVICE Column

- [x] Implement `status/advice.py` (compute_advice with priority rules)
- [x] Integrate advice computation into agent refresh handler
- [x] Tests for advice priority rules

> Depends on: ci, agent
