# Phase 2: `config.py`

**Overview**: Implement configuration loading from `.config/wk.yml`. This module provides the `WkConfig` dataclass and `load_config()` function used by all other components to access user preferences.

**Spec reference**: `specs/components/config.md`

---

## Steps

### Step 1: Implement `ConfigError` exception class

**File**: `src/wk/config.py`

```python
class ConfigError(Exception):
    """Raised for config-related errors (not in git repo, malformed YAML)."""
```

### Step 2: Implement `WkConfig` dataclass

**File**: `src/wk/config.py`

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
    repo_root: Path = field(default_factory=lambda: Path("."))
```

Key points:
- `frozen=True` makes it immutable
- `repo_root` needs `field(default_factory=...)` because Path is mutable

### Step 3: Implement `_find_repo_root()` helper

**File**: `src/wk/config.py`

```python
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
```

### Step 4: Implement `load_config()` function

**File**: `src/wk/config.py`

```python
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
    open_cmd = None
    restart_cmd = None

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
```

Key points:
- Uses `yaml.safe_load()` for security
- Returns empty dict on empty file with `or {}`
- Ignores unknown keys (fail-soft)
- Malformed YAML raises `ConfigError`

### Step 5: Add imports at top of file

**File**: `src/wk/config.py`

```python
from dataclasses import dataclass, field
from pathlib import Path
import subprocess

import yaml
```

---

## Tests

**File**: `tests/test_config.py`

| # | Test Name | Description |
|---|-----------|-------------|
| 1 | `test_valid_config_loads` | Write temp `.config/wk.yml` with both commands, mock repo root, assert fields |
| 2 | `test_missing_config_returns_defaults` | Mock repo root to temp dir with no config, assert `None` for both commands |
| 3 | `test_empty_config_returns_defaults` | Write empty file, assert defaults |
| 4 | `test_unknown_keys_ignored` | Write file with extra keys, assert no error and only known fields set |
| 5 | `test_malformed_yaml_raises_config_error` | Write invalid YAML `{{{invalid`, assert `ConfigError` |
| 6 | `test_repo_root_set_correctly` | Mock subprocess to return specific path, assert `config.repo_root` matches |
| 7 | `test_not_in_git_repo_raises_config_error` | Mock `git rev-parse` to fail, assert `ConfigError` |
| 8 | `test_config_is_immutable` | Try to set attribute on `WkConfig`, assert `FrozenInstanceError` |

---

## Completion Criteria

- [x] `ConfigError` exception class defined
- [x] `WkConfig` frozen dataclass with 3 fields
- [x] `load_config()` function implemented
- [x] `_find_repo_root()` helper implemented (private function)
- [x] All 8 tests pass
- [x] `uv run ./checks.sh` passes (lint, format, types)
