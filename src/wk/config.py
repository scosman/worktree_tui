"""Configuration loading from .config/wk.yml."""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConfigError(Exception):
    """Raised for config-related errors (not in git repo, malformed YAML)."""


@dataclass(frozen=True)
class CustomCommand:
    """A user-defined custom command bound to a key.

    Attributes:
        key: Single character key binding.
        name: Display name shown in footer.
        command: Shell command to run in the worktree directory.
        confirm: If True, show confirmation dialog before running.
    """

    key: str
    name: str
    command: str
    confirm: bool = False


@dataclass(frozen=True)
class WkConfig:
    """Immutable configuration for wk.

    Attributes:
        open_workspace_cmd: Shell command to run when launching a workspace.
            Executed in the worktree directory. None means launch is cd-only.
        restart_workspace_cmd: Shell command to run when restarting a workspace.
            Executed in the worktree directory. None falls back to jump (cd-only).
        custom_commands: Tuple of user-defined custom commands with key bindings.
        repo_root: Absolute path to the git repo root.
    """

    open_workspace_cmd: str | None = None
    restart_workspace_cmd: str | None = None
    custom_commands: tuple[CustomCommand, ...] = ()
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


def _parse_custom_commands(raw: object) -> tuple[CustomCommand, ...]:
    """Parse the custom_commands section of the config.

    Args:
        raw: The raw value from the config file's custom_commands key.

    Returns:
        A tuple of CustomCommand objects.

    Raises:
        ConfigError: If the format is invalid or required fields are missing.
    """
    if not raw:
        return ()

    if not isinstance(raw, dict):
        raise ConfigError(
            f"custom_commands must be a mapping, got {type(raw).__name__}"
        )

    commands: list[CustomCommand] = []
    for key, entry in raw.items():
        # Validate key is a single character
        if not isinstance(key, str) or len(key) != 1:
            raise ConfigError(
                f"custom_commands: key '{key}' must be a single character"
            )

        # Validate entry is a dict
        if not isinstance(entry, dict):
            raise ConfigError(
                f"custom_commands['{key}']: must be a mapping with 'name' and 'command'"
            )

        # Use type: ignore for dict access since YAML parsing produces
        # dict[object, object] which we validate at runtime
        entry_dict: dict[object, object] = entry  # type: ignore[assignment]

        # Extract and validate required fields
        name = entry_dict.get("name")
        if not isinstance(name, str):
            raise ConfigError(
                f"custom_commands['{key}']: missing required field 'name'"
            )

        command = entry_dict.get("command")
        if not isinstance(command, str):
            raise ConfigError(
                f"custom_commands['{key}']: missing required field 'command'"
            )

        # Extract optional confirm field
        confirm = entry_dict.get("confirm", False)
        if not isinstance(confirm, bool):
            raise ConfigError(f"custom_commands['{key}']: 'confirm' must be a boolean")

        commands.append(
            CustomCommand(key=key, name=name, command=command, confirm=confirm)
        )

    return tuple(commands)


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
    custom_commands: tuple[CustomCommand, ...] = ()

    if config_path.exists():
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Malformed YAML in {config_path}: {e}") from e

        # Validate that data is a dict (not a string or other type)
        if not isinstance(data, dict):
            raise ConfigError(
                f"Invalid config format in {config_path}: expected YAML mapping, "
                f"got {type(data).__name__}. Use 'key: value' syntax, not 'KEY=value'."
            )

        # Extract known keys, ignore unknown
        open_cmd = data.get("open_workspace_cmd")
        restart_cmd = data.get("restart_workspace_cmd")
        custom_commands = _parse_custom_commands(data.get("custom_commands"))

    return WkConfig(
        open_workspace_cmd=open_cmd,
        restart_workspace_cmd=restart_cmd,
        custom_commands=custom_commands,
        repo_root=repo_root,
    )
