# Component: `config.py`

**Location**: `src/wk/config.py`

## Goal

Load and validate the `wk` configuration file (`.config/wk.yml`) from the git repo root. Provide safe defaults when the config file or individual keys are missing. Locate the repo root reliably.

## Public Interface

```python
@dataclass(frozen=True)
class CustomCommand:
    """A user-defined custom command bound to a key.

    Attributes:
        key: Single character key binding.
        name: Display name shown in the footer bar.
        command: Shell command to execute (always runs after cd into worktree dir).
        confirm: If True, show a confirmation dialog before executing.
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
            Executed in the worktree directory. None means restart falls back to jump (cd-only).
        custom_commands: List of custom commands parsed from config.
        repo_root: Absolute path to the git repo root.
    """
    open_workspace_cmd: str | None = None
    restart_workspace_cmd: str | None = None
    custom_commands: tuple[CustomCommand, ...] = ()
    repo_root: Path = Path(".")

def load_config() -> WkConfig:
    """Load .config/wk.yml from the git repo root.

    - Finds repo root via `git rev-parse --show-toplevel`.
    - Reads .config/wk.yml relative to that root.
    - Returns WkConfig with defaults for any missing values.
    - If the file doesn't exist or is empty, returns all defaults.
    - Raises ConfigError on malformed YAML or if not in a git repo.
    - Parses `custom_commands` map: validates each entry has `name` (str)
      and `command` (str), optional `confirm` (bool, default false).
      Keys must be single characters. Raises ConfigError on validation failure.
    """

class ConfigError(Exception):
    """Raised for config-related errors (not in git repo, malformed YAML)."""
```

## Config File Format

Path: `<repo_root>/.config/wk.yml`

```yaml
open_workspace_cmd: ".config/wt/start.sh"
restart_workspace_cmd: ".config/wt/start.sh"
custom_commands:
  t:
    name: Terminate
    command: "wt remove --force $(basename $PWD)"
    confirm: true
  s:
    name: Status
    command: "git status"
```

### `custom_commands` Parsing Rules

- The top-level value must be a dict (map of key -> definition).
- Each key in the map is a single character (the key binding).
- Each value must be a dict with:
  - `name` (str, required): display name for the footer.
  - `command` (str, required): shell command to run.
  - `confirm` (bool, optional, default `false`): whether to prompt before executing.
- Validation errors (missing `name`/`command`, non-single-char key, wrong types) raise `ConfigError`.
- Unknown fields inside a command definition are silently ignored.
- Custom command keys may overlap with built-in keys — the TUI handles override logic.

## Design Patterns

- **Value Object**: `WkConfig` is a frozen dataclass — immutable once created, safe to pass around.
- **Fail-soft defaults**: missing file or missing keys silently fall back to defaults. Only genuinely broken states (bad YAML syntax, not in a git repo) raise errors.

## Dependencies (internal)

None. Leaf module.

## Dependencies (external)

- `yaml` (pyyaml) — YAML parsing
- `subprocess` — git commands
- `pathlib.Path` — path handling
- `dataclasses` — config struct

## Testing Strategy

### Test Cases

| # | Test Case | Method |
|---|-----------|--------|
| 1 | Valid config file loads correctly | Unit: write a temp `.config/wk.yml` with `open_workspace_cmd` and `restart_workspace_cmd`, mock `find_repo_root`, assert field values |
| 2 | Missing config file returns defaults | Unit: mock repo root to a temp dir with no `.config/wk.yml`, assert `open_workspace_cmd is None` and `restart_workspace_cmd is None` |
| 3 | Empty config file returns defaults | Unit: write empty file, assert defaults |
| 4 | Config with unknown keys ignores them | Unit: write file with `open_workspace_cmd` + `extra_key: foo`, assert only known fields set, no error |
| 5 | Malformed YAML raises `ConfigError` | Unit: write `{{{invalid`, assert `ConfigError` raised |
| 6 | `repo_root` is set to actual git root | Unit: mock subprocess to return a path, assert `config.repo_root` matches |
| 7 | Not in a git repo raises `ConfigError` | Unit: mock `git rev-parse` to fail, assert `ConfigError` |
| 8 | `WkConfig` is immutable | Unit: assert `frozen=True`, attempt attribute assignment raises `FrozenInstanceError` |
| 9 | Valid `custom_commands` parsed into `CustomCommand` tuple | Unit: write config with two custom commands, assert `config.custom_commands` has correct key/name/command/confirm values |
| 10 | `custom_commands` with missing `name` raises `ConfigError` | Unit: write config with command entry missing `name`, assert `ConfigError` |
| 11 | `custom_commands` with missing `command` raises `ConfigError` | Unit: write config with command entry missing `command`, assert `ConfigError` |
| 12 | `custom_commands` key longer than one char raises `ConfigError` | Unit: write config with key `"ab"`, assert `ConfigError` |
| 13 | `custom_commands` `confirm` defaults to `false` | Unit: write config without `confirm` field, assert `custom_command.confirm is False` |
| 14 | `custom_commands` with `confirm: true` sets field | Unit: write config with `confirm: true`, assert `custom_command.confirm is True` |
| 15 | Missing `custom_commands` key results in empty tuple | Unit: write config without `custom_commands`, assert `config.custom_commands == ()` |
| 16 | `custom_commands` ignores unknown fields in entry | Unit: write config with extra field in a command entry, assert no error, field ignored |
