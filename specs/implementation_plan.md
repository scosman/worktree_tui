# Implementation Plan

## Step 1: Project Scaffolding

- [ ] Configure `pyproject.toml` (src layout, entry point `wk = "wk.cli:main"`, dependencies: textual, pyyaml)
- [ ] Create `src/wk/` package structure with `__init__.py` files
- [ ] Set up test infrastructure (pytest, test directory)
- [ ] Verify `uv run wk` invokes the entry point

## Step 2: `config.py`

- [ ] Implement `WkConfig`, `ConfigError`, `find_repo_root()`, `load_config()`
- [ ] Tests (spec: `specs/components/config.md`)

## Step 3: `worktree.py`

- [ ] Implement `Worktree`, `WtCommandError`, `list_worktrees()`, `create_worktree()`, `remove_worktree()`, `find_worktree()`
- [ ] Tests (spec: `specs/components/worktree.md`)

## Step 4: `shell.py`

- [ ] Implement `is_wrapped()`, `generate_wrapper_zsh()`, `print_shell_commands()`, `run_setup_flow()`
- [ ] Tests (spec: `specs/components/shell.md`)

## Step 5: `actions.py`

- [ ] Implement `action_launch()`, `action_jump()`, `action_new()`, `action_delete()`
- [ ] Tests (spec: `specs/components/actions.md`)

> Depends on: config, worktree

## Step 6: `tui/theme.py` + `tui/worktree_list.py`

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
