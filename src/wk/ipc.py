"""File-based IPC for communication between wk panes.

The selector pane writes the currently selected worktree to a JSON state file.
Other panes (diff, workspace) poll this file to react to selection changes.
"""

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Selection:
    """The currently selected worktree.

    Attributes:
        worktree_name: Name/identifier of the selected worktree.
        worktree_path: Absolute path to the worktree directory.
    """

    worktree_name: str
    worktree_path: str


def _state_dir(repo_root: Path) -> Path:
    """Return the state directory for a given repo.

    Uses $XDG_RUNTIME_DIR/wk/<repo-hash> if available,
    otherwise falls back to $TMPDIR/wk-<user>/<repo-hash>.
    """
    repo_hash = hashlib.sha256(str(repo_root).encode()).hexdigest()[:12]
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        return Path(runtime_dir) / "wk" / repo_hash
    return Path(tempfile.gettempdir()) / f"wk-{os.getuid()}" / repo_hash


def state_file_path(repo_root: Path) -> Path:
    """Return the path to the IPC state file for a repo."""
    return _state_dir(repo_root) / "state.json"


def write_selection(repo_root: Path, selection: Selection) -> None:
    """Atomically write the current selection to the state file.

    Uses write-to-temp + rename for atomicity.
    """
    path = state_file_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = json.dumps(asdict(selection))
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(data)
    tmp_path.rename(path)


def read_selection(repo_root: Path) -> Selection | None:
    """Read the current selection from the state file.

    Returns None if the file doesn't exist or is malformed.
    """
    path = state_file_path(repo_root)
    try:
        data = json.loads(path.read_text())
        return Selection(
            worktree_name=data["worktree_name"],
            worktree_path=data["worktree_path"],
        )
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def clear_state(repo_root: Path) -> None:
    """Remove the state file. Called on exit/cleanup."""
    path = state_file_path(repo_root)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
