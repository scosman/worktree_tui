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

## Step 5: `actions.py` ✅

- [ ] Mark the step as complete in `specs/implementation_plan.md`.

Update the implementation plan to mark Step 5 as complete. Now let me update the phase plan. update the phase 5 completion criteria. and mark them off. delete `test_action_delete_propagates_wt_command_error` test cases by name and description |
| expected cd command | | expected launch commands |
- [ ] Tests passing
- [ ] `uv run ./checks.sh` passes (lint, format, types, tests)

> Depends on: config, worktree

## Step 7: `tui/app.py`

- [ ] Implement `WkApp`, `run_app()`, all action handlers, stderr rendering
 - [ ] Tests (spec: `specs/components/tui_app.md`, `specs/components/tui_worktree_list.md`)
    > Grouped: theme is small and a direct prerequisite for the list widget.
> Depends on: worktree

- [ ] Implement `APP_CSS`, `ThemeColors`
- [ ] Implement `WorktreeListItem`, `WorktreeList`, relative time helper
- [ ] Tests (specs: `specs/components/tui_theme.md`, `specs/components/tui_worktree_list.md`)

> Grouped: theme is small and a direct prerequisite for the list widget.
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
