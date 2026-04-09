"""Zellij layout generation and tmux session management."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from wk.config import WkConfig, WorkspaceWindow

# Isolated tmux socket name so our config doesn't affect user's tmux
_TMUX_SOCKET = "wk"


def tmux_session_name(worktree_name: str) -> str:
    """Build a tmux-safe session name from a worktree name.

    Replaces characters that tmux interprets specially (. : /)
    with hyphens so session targeting works reliably.
    """
    sanitized = worktree_name.replace("/", "-").replace(".", "-").replace(":", "-")
    return f"wk-{sanitized}"


def _tmux(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a tmux command on the wk socket."""
    return subprocess.run(
        ["tmux", "-L", _TMUX_SOCKET, *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _tmux_check(*args: str) -> None:
    """Run a tmux command on the wk socket, raising on failure."""
    subprocess.run(
        ["tmux", "-L", _TMUX_SOCKET, *args],
        check=True,
    )


def _write_tmux_conf() -> str:
    """Write a minimal tmux config and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".conf", delete=False, prefix="wk-tmux-"
    )
    f.write(
        "set -g prefix C-a\n"
        "unbind C-b\n"
        "bind C-a send-prefix\n"
        "set -g status on\n"
        "set -g status-left ' '\n"
        "set -g status-right ''\n"
        "set -g status-style 'bg=colour235 fg=colour245'\n"
        "set -g mouse on\n"
        "set -g default-terminal 'screen-256color'\n"
    )
    f.close()
    return f.name


def generate_zellij_layout(config: WkConfig) -> str:
    """Generate a KDL layout string for the 2-pane wk dashboard.

    Layout:
    +------------------+------------------------------+
    |  wk selector     |                              |
    |  (40% width)     |   wk workspace               |
    |                  |   (60% width, full height)    |
    |                  |                              |
    +------------------+------------------------------+
    """
    cwd = str(config.repo_root)

    return f"""\
layout {{
    pane split_direction="vertical" {{
        pane size="40%" command="wk" cwd="{cwd}" {{
            args "selector"
        }}
        pane size="60%" command="wk" cwd="{cwd}" {{
            args "workspace"
        }}
    }}
}}
"""


def launch_zellij(config: WkConfig) -> list[str]:
    """Write the layout to a temp file and return shell commands."""
    layout_content = generate_zellij_layout(config)
    session_name = tmux_session_name(config.repo_root.name)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".kdl", delete=False, prefix="wk-layout-"
    ) as f:
        f.write(layout_content)
        layout_path = f.name

    return [f"zellij --layout {layout_path} --new-session-with-layout {session_name}"]


def is_inside_zellij() -> bool:
    """Check if we're already running inside a Zellij session."""
    return "ZELLIJ" in os.environ


def _create_tmux_session(
    session_name: str,
    worktree_path: Path,
    config: WkConfig,
) -> None:
    """Create a new tmux session with configured windows."""
    cwd = str(worktree_path)

    env_prefix = ""
    if config.workspace_env_script:
        env_script = str(config.repo_root / config.workspace_env_script)
        env_prefix = f"source {env_script} && "

    windows = list(config.workspace_windows)
    if not windows:
        windows = [WorkspaceWindow(name="term", command="exec $SHELL")]

    conf_path = _write_tmux_conf()

    # Create session with first window
    first = windows[0]
    first_cwd = str(worktree_path / first.cwd) if first.cwd else cwd
    first_cmd = f"{env_prefix}{first.command}"

    subprocess.run(
        [
            "tmux",
            "-L",
            _TMUX_SOCKET,
            "-f",
            conf_path,
            "new-session",
            "-d",
            "-s",
            session_name,
            "-n",
            first.name,
            "-c",
            first_cwd,
            "bash",
            "-c",
            first_cmd,
        ],
        check=True,
    )

    # Apply session options explicitly (the -f config only takes effect on
    # server start, so we must set options per-session to be reliable)
    _tmux("set-option", "-t", session_name, "status", "on")
    _tmux("set-option", "-t", session_name, "status-left", " ")
    _tmux("set-option", "-t", session_name, "status-right", "")
    _tmux("set-option", "-t", session_name, "status-style", "bg=colour235 fg=colour245")
    _tmux("set-option", "-t", session_name, "mouse", "on")
    _tmux("set-option", "-t", session_name, "prefix", "C-a")
    _tmux("set-option", "-t", session_name, "remain-on-exit", "on")
    # C-a R to respawn a dead pane (server-global binding)
    _tmux("bind-key", "R", "respawn-pane", "-k")

    # Create remaining windows
    for win in windows[1:]:
        win_cwd = str(worktree_path / win.cwd) if win.cwd else cwd
        win_cmd = f"{env_prefix}{win.command}"
        _tmux_check(
            "new-window",
            "-t",
            session_name,
            "-n",
            win.name,
            "-c",
            win_cwd,
            "bash",
            "-c",
            win_cmd,
        )

    # Select the first window
    _tmux_check("select-window", "-t", f"{session_name}:{windows[0].name}")


def run_workspace_loop(config: WkConfig) -> None:
    """Run the workspace pane: watch IPC and manage tmux sessions.

    Creates/switches tmux sessions as the user selects different
    worktrees in the selector pane.
    """
    from wk.ipc import read_selection
    from wk.worktree import list_worktrees

    current_session: str | None = None

    # Get initial selection or fall back to first worktree
    selection = read_selection(config.repo_root)
    if selection is None:
        worktrees = list_worktrees()
        if worktrees:
            from wk.ipc import Selection, write_selection

            write_selection(
                config.repo_root,
                Selection(worktrees[0].name, str(worktrees[0].path)),
            )
            selection = read_selection(config.repo_root)

    if selection is None:
        print("No worktrees found.", flush=True)
        return

    # Create and attach to initial session
    session_name = tmux_session_name(selection.worktree_name)
    worktree_path = Path(selection.worktree_path)

    if _tmux("has-session", "-t", session_name).returncode != 0:
        _create_tmux_session(session_name, worktree_path, config)
    current_session = session_name

    # Attach to tmux — this takes over the terminal
    # We use a loop: when the user detaches (or we detach programmatically),
    # we check if the selection changed and switch sessions
    while True:
        # Attach (blocks until detach)
        subprocess.run(
            ["tmux", "-L", _TMUX_SOCKET, "attach-session", "-t", current_session],
            check=False,
        )

        # After detach, check if selection changed
        selection = read_selection(config.repo_root)
        if selection is None:
            break

        new_session = tmux_session_name(selection.worktree_name)
        if new_session == current_session:
            # User manually detached, re-attach
            continue

        # Selection changed — create new session if needed
        new_path = Path(selection.worktree_path)
        if _tmux("has-session", "-t", new_session).returncode != 0:
            _create_tmux_session(new_session, new_path, config)
        current_session = new_session


def restart_tmux_session(
    session_name: str,
    worktree_path: Path,
    config: WkConfig,
) -> None:
    """Kill and recreate a tmux session, then detach for reattach."""
    _tmux("kill-session", "-t", session_name)
    _create_tmux_session(session_name, worktree_path, config)
    _tmux("detach-client")


def switch_tmux_session(session_name: str) -> None:
    """Switch the attached tmux client to a different session."""
    _tmux("switch-client", "-t", session_name)


def tmux_capture_pane(session: str, window: str, lines: int = 25) -> str | None:
    """Capture the last N lines of a tmux pane."""
    result = _tmux(
        "capture-pane",
        "-p",
        "-t",
        f"{session}:{window}",
        "-S",
        f"-{lines}",
    )
    if result.returncode != 0:
        return None
    return result.stdout


def tmux_session_exists(session: str) -> bool:
    """Check if a tmux session exists."""
    return _tmux("has-session", "-t", session).returncode == 0


def is_tmux_available() -> bool:
    """Check if tmux is installed."""
    return shutil.which("tmux") is not None


def is_zellij_available() -> bool:
    """Check if zellij is installed."""
    return shutil.which("zellij") is not None
