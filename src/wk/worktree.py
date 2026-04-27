"""Worktree data models and wt command interface."""

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class WtCommandError(Exception):
    """Raised when a `wt` command fails.

    Attributes:
        command: The command that was run.
        stderr: Captured stderr output from the command.
        returncode: Process exit code.
    """

    def __init__(self, command: str, stderr: str, returncode: int) -> None:
        self.command = command
        self.stderr = stderr
        self.returncode = returncode
        super().__init__(
            f"Command '{command}' failed with exit code {returncode}: {stderr}"
        )


@dataclass(frozen=True)
class Worktree:
    """Represents a single git worktree.

    Attributes:
        name: Worktree identifier (branch name without prefix).
        path: Absolute path to the worktree directory.
        branch: Full branch name.
        created: When the worktree was created.
    """

    name: str
    path: Path
    branch: str
    created: datetime


def _run_wt(args: list[str]) -> str:
    """Run a wt command and return stdout.

    Raises WtCommandError on failure.
    """
    cmd = ["wt", *args]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise WtCommandError(" ".join(cmd), result.stderr, result.returncode)
    return result.stdout


def _parse_worktree(data: dict) -> Worktree:
    """Parse a worktree dict from JSON into a Worktree object."""
    # Handle created timestamp - can be ISO string or Unix timestamp in commit
    created: datetime
    if "created" in data and data["created"]:
        created_str = data["created"]
        if created_str.endswith("Z"):
            created_str = created_str[:-1] + "+00:00"
        created = datetime.fromisoformat(created_str)
    elif "commit" in data and "timestamp" in data["commit"]:
        created = datetime.fromtimestamp(data["commit"]["timestamp"], tz=None)
    else:
        created = datetime.now()

    # Use branch as name if name not present. `get(..., "")` doesn't help
    # when the key exists with value null — coerce explicitly.
    name = data.get("name") or data.get("branch") or ""
    branch = data.get("branch") or name

    return Worktree(
        name=name,
        path=Path(data["path"]),
        branch=branch,
        created=created,
    )


def list_worktrees() -> list[Worktree]:
    """Fetch all worktrees via `wt list --format json`.

    Returns a list sorted by created date descending (most recent first).
    Raises WtCommandError if the command fails.
    """
    stdout = _run_wt(["list", "--format", "json"])
    data = json.loads(stdout)
    worktrees = [_parse_worktree(item) for item in data]
    # Sort: main/master first, then by created date descending
    worktrees.sort(
        key=lambda w: (w.branch not in ("main", "master"), w.created),
        reverse=True,
    )
    # Move main/master back to the front (reverse flipped it to the end)
    main = [w for w in worktrees if w.branch in ("main", "master")]
    rest = [w for w in worktrees if w.branch not in ("main", "master")]
    return main + rest


def create_worktree(name: str) -> Worktree:
    """Create a new worktree branching off HEAD.

    Runs: `wt switch --create <name> --base=@ --yes`
    Returns the newly created Worktree.
    Raises WtCommandError on failure (e.g. name already exists).
    """
    _run_wt(["switch", "--create", name, "--base=@", "--yes"])
    # Find and return the newly created worktree
    result = find_worktree(name)
    if result is None:
        raise WtCommandError(
            f"wt switch --create {name} --base=@",
            "Worktree created but not found in list",
            1,
        )
    return result


def remove_worktree(name: str, force: bool = False) -> None:
    """Remove a worktree.

    Runs: `wt remove <name> --yes` (with --force if force=True)
    Raises WtCommandError on failure.
    """
    args = ["remove", name, "--yes"]
    if force:
        args.append("--force")
    _run_wt(args)


def find_worktree(name: str) -> Worktree | None:
    """Find a worktree by name. Returns None if not found.

    Calls list_worktrees() and searches by name (case-sensitive).
    """
    for worktree in list_worktrees():
        if worktree.name == name:
            return worktree
    return None
