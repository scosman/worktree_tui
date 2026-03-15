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

- [ ] Implement `WkApp`, `run_app()`, all action handlers, stderr rendering
- [ ] Tests (spec: `specs/components/tui_app.md`)

> Depends on: actions, worktree_list, theme

## Step 8: `cli.py`

- [ ] Implement `main()` with arg routing, wrapper enforcement, output protocol
- [ ] Tests (spec: `specs/components/cli.md`)
- [ ] End-to-end manual test: `wk init zsh`, wrapper install, TUI launch, CLI commands

> Depends on: all other components
