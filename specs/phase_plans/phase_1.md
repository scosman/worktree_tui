# Phase 1: Project Scaffolding

## Overview

Set up the basic project structure for the `wk` TUI application. This phase creates the Python package layout, configures build settings, sets up test infrastructure, and verifies the entry point works.

**Spec Reference**: `specs/architecture.md` - Project Structure section

## Steps

### Step 1.1: Configure pyproject.toml

Update `pyproject.toml` with:

```toml
[project]
name = "wk"
version = "0.1.0"
description = "Worktree TUI - Interactive worktree management"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "textual>=0.47.0",
    "pyyaml>=6.0",
]

[project.scripts]
wk = "wk.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/wk"]

[tool.pytest.ini_options]
testpaths = ["tests"]

# Ruff configuration
[tool.ruff]
line-length = 88
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

# Ty configuration
[tool.ty.environment]
python-version = "3.13"
```

### Step 1.2: Create src/wk package structure

Create the following directory structure and files:

```
src/
└── wk/
    ├── __init__.py      # Package init with version
    ├── cli.py           # Entry point stub (def main(): pass)
    ├── config.py        # Empty module
    ├── worktree.py      # Empty module
    ├── shell.py         # Empty module
    ├── actions.py       # Empty module
    └── tui/
        ├── __init__.py
        ├── app.py       # Empty module
        ├── worktree_list.py  # Empty module
        └── theme.py     # Empty module
```

**`src/wk/__init__.py`**:
```python
"""Worktree TUI - Interactive worktree management."""
__version__ = "0.1.0"
```

**`src/wk/cli.py`** (stub for entry point testing):
```python
"""CLI entry point."""


def main() -> None:
    """Main entry point for the wk command."""
    print("wk initialized")  # Temporary stub
```

### Step 1.3: Set up test infrastructure

Create test directory with pytest configuration:

```
tests/
├── __init__.py
└── test_cli.py      # Basic test to verify test infrastructure works
```

**`tests/test_cli.py`**:
```python
"""Tests for CLI entry point."""
from wk.cli import main


def test_main_exists():
    """Verify main function exists and is callable."""
    assert callable(main)
```

### Step 1.4: Verify entry point

Run `uv run wk` and verify it outputs "wk initialized".

## Tests

### Automated Tests

| Test File | Test Name | What it Verifies |
|-----------|-----------|------------------|
| `tests/test_cli.py` | `test_main_exists` | The main() function exists and is callable |

### Manual Verification

1. Run `uv run wk` - should print "wk initialized"
2. Run `uv run pytest` - should pass with 1 test
3. Run `uv run ./checks.sh` - should pass (or skip types if no code yet)

## Completion Criteria

- [ ] `pyproject.toml` configured with src layout, entry point, dependencies
- [ ] `src/wk/` package structure created with all module files
- [ ] `tests/` directory created with pytest configuration
- [ ] `uv run wk` executes and prints "wk initialized"
- [ ] `uv run pytest` passes
- [ ] `uv run ./checks.sh` passes (format, lint, types, tests)
