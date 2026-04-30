"""Zellij layout generation and tmux session management."""

import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from wk.config import WkConfig, WorkspaceWindow
from wk.ipc import _state_dir

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


_TMUX_CONF = os.path.expanduser("~/.config/wk/tmux.conf")


def _write_tmux_conf() -> str:
    """Write tmux config to a stable path and return it."""
    os.makedirs(os.path.dirname(_TMUX_CONF), exist_ok=True)
    with open(_TMUX_CONF, "w") as f:
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
            "set -g remain-on-exit on\n"
            "set -g window-status-format ' #I:#W '\n"
            "set -g window-status-current-format ' #I:#W* '\n"
            "bind Left previous-window\n"
            "bind Right next-window\n"
            "bind R respawn-pane -k\n"
            "set -g base-index 1\n"
        )
    return _TMUX_CONF


def generate_zellij_layout(config: WkConfig) -> str:
    """Generate a KDL layout string for the 2-pane wk dashboard.

    Layout:
    +------------------+------------------------------+
    |  wk hub          |                              |
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
            args "hub"
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
    session_name = f"wk-{config.repo_root.name}"
    cwd = str(config.repo_root)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".kdl", delete=False, prefix="wk-layout-"
    ) as f:
        f.write(layout_content)
        layout_path = f.name

    commands: list[str] = []

    # Source env script before launching zellij so all panes inherit env
    if config.workspace_env_script:
        env_script = str(config.repo_root / config.workspace_env_script)
        commands.append(f"cd {cwd} && source {env_script}")

    # Reuse existing session if it exists, otherwise create new
    commands.append(
        f"if zellij list-sessions --no-formatting 2>/dev/null | grep -q '^{session_name} '; then"
        f" zellij attach {session_name};"
        f" else zellij -s {session_name} --new-session-with-layout {layout_path}; fi"
    )
    return commands


def _set_pane_title(name: str) -> None:
    """Set the terminal/pane title using escape sequences."""
    # Works in zellij, tmux, and most terminal emulators
    print(f"\x1b]0;{name}\x07", end="", flush=True)


def is_inside_zellij() -> bool:
    """Check if we're already running inside a Zellij session."""
    return "ZELLIJ" in os.environ


def _source_env(
    env_script: str,
    cwd: str,
) -> dict[str, str]:
    """Source the env script in a subprocess and capture exported env vars."""
    shell = os.environ.get("SHELL", "bash")
    result = subprocess.run(
        [shell, "-c", f"cd {cwd} && source {env_script} && env"],
        capture_output=True,
        text=True,
        check=False,
    )
    env: dict[str, str] = {}
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if "=" in line:
                key, _, val = line.partition("=")
                env[key] = val
    return env


def _create_tmux_session(
    session_name: str,
    worktree_path: Path,
    config: WkConfig,
) -> None:
    """Create a new tmux session with configured windows."""
    cwd = str(worktree_path)

    # Source the env script once and capture all env vars
    extra_env: dict[str, str] = {}
    if config.workspace_env_script:
        env_script = str(config.repo_root / config.workspace_env_script)
        extra_env = _source_env(env_script, cwd)

    windows = list(config.workspace_windows)
    if not windows:
        windows = [WorkspaceWindow(name="term", command="exec $SHELL")]

    conf_path = _write_tmux_conf()

    # Build env source prefix — use bash (not zsh) to source the env
    # script. The old zellij layout used bash for this, and exec $SHELL
    # from bash correctly inherits PATH into zsh's hash table.
    env_source = ""
    if config.workspace_env_script:
        env_script = str(config.repo_root / config.workspace_env_script)
        env_source = f"cd {cwd} && source {env_script} && "

    # Create session with first window
    first = windows[0]
    first_cwd = str(worktree_path / first.cwd) if first.cwd else cwd
    first_cmd = f"{env_source}{first.command}"

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

    # Set env vars on the tmux session so all windows inherit them
    for key, val in extra_env.items():
        _tmux("set-environment", "-t", session_name, key, val)

    # Per-session options
    _tmux("set-option", "-t", session_name, "prefix", "C-a")
    # Source the conf to ensure global options are set
    # (-f only works on first server start, not subsequent sessions)
    _tmux("source-file", conf_path)

    # Create remaining windows — env inherited from tmux session
    for win in windows[1:]:
        win_cwd = str(worktree_path / win.cwd) if win.cwd else cwd
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
            win.command,
        )

    # Renumber windows to start from base-index and select the first
    _tmux("move-window", "-r", "-t", session_name)
    _tmux_check("select-window", "-t", f"{session_name}:{windows[0].name}")

    # Record the pane PGIDs so restart can kill orphaned children later,
    # even after the pane shell dies and they get reparented to launchd.
    _save_session_pgids(
        config.repo_root, session_name, _capture_session_pgids(session_name)
    )


def run_workspace_loop(config: WkConfig) -> None:
    """Run the workspace pane: watch IPC and manage tmux sessions.

    Creates/switches tmux sessions as the user selects different
    worktrees in the selector pane.
    """
    import time

    from wk.ipc import clear_state, read_selection

    current_session: str | None = None

    # Clear stale selection and wait for the selector to write fresh data.
    # Hub seeds the initial selection on mount, but we wait generously here
    # so a cold-start TUI on a slow system doesn't lose the race.
    clear_state(config.repo_root)
    selection = None
    for _ in range(300):  # Wait up to 30 seconds
        selection = read_selection(config.repo_root)
        if selection is not None:
            break
        time.sleep(0.1)

    if selection is None:
        print("No worktrees found.", flush=True)
        return

    # Create and attach to initial session
    session_name = tmux_session_name(selection.worktree_name)
    worktree_path = Path(selection.worktree_path)

    if _tmux("has-session", "-t", session_name).returncode != 0:
        _create_tmux_session(session_name, worktree_path, config)
    current_session = session_name
    _set_pane_title(f"wk workspace - {selection.worktree_name}")

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
        _set_pane_title(f"wk workspace - {selection.worktree_name}")


def _descendant_pids(pid: int) -> list[int]:
    """Return all descendant PIDs of `pid` (recursive)."""
    result = subprocess.run(
        ["pgrep", "-P", str(pid)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    children = [int(p) for p in result.stdout.split() if p.strip()]
    out = list(children)
    for c in children:
        out.extend(_descendant_pids(c))
    return out


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _pgid_alive(pgid: int) -> bool:
    """Return True if any process is still in the given process group."""
    result = subprocess.run(
        ["pgrep", "-g", str(pgid)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def _get_pgid(pid: int) -> int | None:
    """Look up the process group ID of `pid` via ps."""
    result = subprocess.run(
        ["ps", "-o", "pgid=", "-p", str(pid)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _capture_session_pgids(session_name: str) -> list[int]:
    """Return the PGID of each pane shell in the session."""
    result = _tmux("list-panes", "-s", "-t", session_name, "-F", "#{pane_pid}")
    if result.returncode != 0:
        return []
    pgids: list[int] = []
    for raw in result.stdout.split():
        raw = raw.strip()
        if not raw:
            continue
        try:
            pid = int(raw)
        except ValueError:
            continue
        pgid = _get_pgid(pid)
        if pgid is not None and pgid not in pgids:
            pgids.append(pgid)
    return pgids


def _pgids_state_path(repo_root: Path, session_name: str) -> Path:
    return _state_dir(repo_root) / f"pgids-{session_name}.json"


def _save_session_pgids(repo_root: Path, session_name: str, pgids: list[int]) -> None:
    if not pgids:
        return
    path = _pgids_state_path(repo_root, session_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pgids))


def _load_session_pgids(repo_root: Path, session_name: str) -> list[int]:
    path = _pgids_state_path(repo_root, session_name)
    try:
        data = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return [int(p) for p in data if isinstance(p, int)]


def _clear_session_pgids(repo_root: Path, session_name: str) -> None:
    path = _pgids_state_path(repo_root, session_name)
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _terminate_session_processes(
    repo_root: Path,
    session_name: str,
    grace_seconds: float = 2.0,
) -> None:
    """Kill all processes belonging to the session, including orphans.

    tmux's `kill-session` sends SIGHUP to the pane shell, which some wrappers
    (npm/uv/etc.) don't propagate to children. When the backend dies and the
    pane is marked dead (`remain-on-exit`), the orphaned children get
    reparented to launchd, so a descendant walk from the pane PID misses them.
    Saved PGIDs catch the orphans because PG membership survives reparenting.
    """
    pids: list[int] = []
    pgids: list[int] = list(_load_session_pgids(repo_root, session_name))

    result = _tmux("list-panes", "-s", "-t", session_name, "-F", "#{pane_pid}")
    if result.returncode == 0:
        for raw in result.stdout.split():
            raw = raw.strip()
            if not raw:
                continue
            try:
                pid = int(raw)
            except ValueError:
                continue
            pids.append(pid)
            pids.extend(_descendant_pids(pid))

    if not pids and not pgids:
        return

    for pgid in pgids:
        try:
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass

    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        if not any(_pid_alive(p) for p in pids) and not any(
            _pgid_alive(g) for g in pgids
        ):
            break
        time.sleep(0.1)

    for pgid in pgids:
        if _pgid_alive(pgid):
            try:
                os.killpg(pgid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
    for pid in pids:
        if _pid_alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

    _clear_session_pgids(repo_root, session_name)


def restart_tmux_session(
    session_name: str,
    worktree_path: Path,
    config: WkConfig,
) -> None:
    """Kill and recreate a tmux session, then detach for reattach."""
    _terminate_session_processes(config.repo_root, session_name)
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
