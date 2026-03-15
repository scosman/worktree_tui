"""Shared business logic for launch/jump/restart/new/delete actions."""

import shlex

from wk.config import WkConfig
from wk.worktree import Worktree, create_worktree, remove_worktree


def action_custom_command(worktree: Worktree, command: str) -> list[str]:
    """Build shell commands to run a custom command in a worktree directory.

    Always cd's into the worktree first, then runs the command.

    Args:
        worktree: The worktree to run the command in.
        command: The shell command to run (passed through as-is).

    Returns:
        A list containing ["cd <path>", "<command>"].
    """
    cd_cmd = f"cd {shlex.quote(str(worktree.path))}"
    return [cd_cmd, command]


def action_launch(worktree: Worktree, config: WkConfig) -> list[str]:
    """Build shell commands to launch a worktree workspace.

    Returns:
        - ["cd <path>"] if no open_workspace_cmd configured.
        - ["cd <path>", "<open_workspace_cmd>"] if configured.
    """
    cd_cmd = f"cd {shlex.quote(str(worktree.path))}"
    if config.open_workspace_cmd:
        return [cd_cmd, config.open_workspace_cmd]
    return [cd_cmd]


def action_jump(worktree: Worktree) -> list[str]:
    """Build shell commands to cd into a worktree.

    Returns:
        - ["cd <path>"]
    """
    return [f"cd {shlex.quote(str(worktree.path))}"]


def action_restart(worktree: Worktree, config: WkConfig) -> list[str]:
    """Build shell commands to restart a worktree workspace.

    Returns:
        - ["cd <path>", "<restart_workspace_cmd>"] if configured.
        - ["cd <path>"] if restart_workspace_cmd is not configured (fallback to jump).
    """
    cd_cmd = f"cd {shlex.quote(str(worktree.path))}"
    if config.restart_workspace_cmd:
        return [cd_cmd, config.restart_workspace_cmd]
    return [cd_cmd]


def action_new(name: str, config: WkConfig) -> list[str]:
    """Create a new worktree off HEAD and return launch commands.

    1. Calls create_worktree(name).
    2. Calls action_launch() with the new worktree.
    Returns the same commands as action_launch.
    Raises WtCommandError if creation fails.
    """
    worktree = create_worktree(name)
    return action_launch(worktree, config)


def action_delete(name: str, force: bool = False) -> None:
    """Delete a worktree.

    Calls remove_worktree(name, force).
    Raises WtCommandError if removal fails.
    Returns nothing — no shell commands needed (caller stays in TUI or exits).
    """
    remove_worktree(name, force=force)
