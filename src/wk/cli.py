"""CLI entry point for wk tool."""

import sys

from wk import actions
from wk.config import ConfigError, load_config
from wk.shell import (
    generate_wrapper_zsh,
    is_wrapped,
    print_shell_commands,
    run_setup_flow,
)
from wk.tui.app import run_app
from wk.worktree import WtCommandError, find_worktree, list_worktrees


def main() -> None:
    """Entry point registered in pyproject.toml as `wk = "wk.cli:main"`.

    Parses sys.argv, enforces wrapper check, routes to the appropriate action.
    Calls sys.exit() on errors.
    """
    argv = sys.argv

    # Route based on arguments
    if len(argv) == 1:
        # No args: TUI mode
        _require_wrapper()
        _run_tui()
    elif argv[1] == "init":
        # init zsh: print wrapper (no wrapper required)
        if len(argv) < 3 or argv[2] != "zsh":
            _usage_error("Usage: wk init zsh\nOnly zsh is supported.")
        print(generate_wrapper_zsh())
    elif argv[1] == "selector":
        # selector: persistent TUI mode (used inside Zellij pane)
        _run_selector()
    elif argv[1] == "workspace":
        # workspace: launch tmux session for selected worktree (used inside Zellij pane)
        _run_workspace()
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


def _require_wrapper() -> None:
    """Exit with setup flow if not running under shell wrapper."""
    if not is_wrapped():
        run_setup_flow()
        sys.exit(1)


def _usage_error(message: str) -> None:
    """Print usage error to stderr and exit non-zero."""
    print(message, file=sys.stderr)
    sys.exit(1)


def _run_tui() -> None:
    """Load config, run TUI or launch Zellij dashboard.

    If Zellij is available and we're not already inside Zellij,
    launches the 3-pane Zellij dashboard. Otherwise falls back
    to the classic single-pane TUI.
    """
    from wk.layout import is_inside_zellij, is_zellij_available, launch_zellij

    try:
        config = load_config()

        if is_zellij_available() and not is_inside_zellij():
            # Print zellij launch command for the wrapper to eval
            commands = launch_zellij(config)
            print_shell_commands(commands)
            return

        # Fallback: classic TUI mode (inside Zellij or no Zellij)
        worktrees = list_worktrees()
        commands = run_app(worktrees, config)
        print_shell_commands(commands)
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except WtCommandError as e:
        print(f"Error: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


def _run_selector() -> None:
    """Run the TUI in persistent selector mode (for Zellij pane)."""
    try:
        config = load_config()
        worktrees = list_worktrees()
        run_app(worktrees, config, persistent=True)
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except WtCommandError as e:
        print(f"Error: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)



def _run_workspace() -> None:
    """Run the workspace pane (tmux session manager).

    Called by the Zellij layout in the right pane. Watches IPC for
    worktree selection changes and creates/switches tmux sessions.
    """
    from wk.layout import is_tmux_available, run_workspace_loop

    try:
        config = load_config()

        if not is_tmux_available():
            print("Error: tmux is required for workspace mode", file=sys.stderr)
            sys.exit(1)

        run_workspace_loop(config)
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except WtCommandError as e:
        print(f"Error: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


def _cli_new(name: str) -> None:
    """Create new worktree and print launch commands."""
    try:
        config = load_config()
        commands = actions.action_new(name, config)
        print_shell_commands(commands)
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except WtCommandError as e:
        print(f"Error: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


def _cli_launch(name: str) -> None:
    """Launch existing worktree by name."""
    try:
        config = load_config()
        worktree = find_worktree(name)
        if worktree is None:
            print(f"Error: Worktree '{name}' not found", file=sys.stderr)
            sys.exit(1)
        commands = actions.action_launch(worktree, config)
        print_shell_commands(commands)
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except WtCommandError as e:
        print(f"Error: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
