# Component: `config.py`

**Location**: `src/wk/config.py`

## Goal

Load and validate the `wk` configuration file (`.config/wk.yml`) from the git repo root. Provide safe defaults when the config file or individual keys are missing. Locate the repo root reliably.

## Public Interface

```python
@dataclass(frozen=True)
class WkConfig:
    """Immutable configuration for wk.

    Attributes:
        open_workspace_cmd: Shell command to run when launching a workspace.
            Executed in the worktree directory. None means launch is cd-only.
        restart_workspace_cmd: Shell command to run when restarting a workspace.
            Executed in the worktree directory. None means restart falls back to jump (cd-only).
        repo_root: Absolute path to the git repo root.
    """
    open_workspace_cmd: str | None = None
    restart_workspace_cmd: str | None = None
    repo_root: Path = Path(".")

def load_config() -> WkConfig:
    """Load .config/wk.yml from the git repo root.

    - Finds repo root via `git rev-parse --show-toplevel`.
    - Reads .config/wk.yml relative to that root.
    - Returns WkConfig with defaults for any missing values.
    - If the file doesn't exist or is empty, returns all defaults.
    - Raises ConfigError on malformed YAML or if not in a git repo.
    """

class ConfigError(Exception):
    """Raised for config-related errors (not in git repo, malformed YAML)."""
```

## Config File Format

Path: `<repo_root>/.config/wk.yml`

```yaml
open_workspace_cmd: ".config/wt/start.sh"
restart_workspace_cmd: ".config/wt/start.sh"
```

Two keys for now. The schema is intentionally minimal and additive.

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
