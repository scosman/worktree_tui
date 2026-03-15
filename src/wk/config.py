"""Configuration loading from .config/wk.yml."""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConfigError(Exception):
    """Raised for config-related errors (not in git repo, malformed YAML)."""


@dataclass(frozen=True)
class WkConfig:
    """Immutable configuration for wk.

    Attributes:
        open_workspace_cmd: Shell command to run when launching a workspace.
            Executed in the worktree directory. None means launch is cd-only.
        restart_workspace_cmd: Shell command to run when restarting a workspace.
            Executed in the worktree directory. None falls back to jump (cd-only).
        repo_root: Absolute path to the git repo root.
    """

    open_workspace_cmd: str | None = None
    restart_workspace_cmd: str | None = None
    repo_root: Path = field(default_factory=lambda: Path("."))


def _find_repo_root() -> Path:
    """Find the git repo root via `git rev-parse --show-toplevel`.

    Raises:
        ConfigError: If not in a git repo or git command fails.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ConfigError("Not in a git repository")
    return Path(result.stdout.strip())


def load_config() -> WkConfig:
    """Load .config/wk.yml from the git repo root.

    - Finds repo root via `git rev-parse --show-toplevel`.
    - Reads .config/wk.yml relative to that root.
    - Returns WkConfig with defaults for any missing values.
    - If the file doesn't exist or is empty, returns all defaults.
    - Raises ConfigError on malformed YAML or if not in a git repo.
    """
    repo_root = _find_repo_root()
    config_path = repo_root / ".config" / "wk.yml"

    # Default values
    open_cmd: str | None = None
    restart_cmd: str | None = None

    if config_path.exists():
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Malformed YAML in {config_path}: {e}") from e

        # Extract known keys, ignore unknown
        open_cmd = data.get("open_workspace_cmd")
        restart_cmd = data.get("restart_workspace_cmd")

    return WkConfig(
        open_workspace_cmd=open_cmd,
        restart_workspace_cmd=restart_cmd,
        repo_root=repo_root,
    )
