# Phase 4: shell.py

**Spec Reference**: `specs/components/shell.md`

## Overview

Implement shell wrapper generation, detection, and setup flow. This module is a "leaf" module with no internal dependencies. It manages the shell wrapper lifecycle: detecting if `wk` is running inside the wrapper, generating the wrapper function, handling the first-run setup flow, and providing the protocol for sending shell commands back to the parent shell via stdout.

## Steps

### Step 1: Implement is_wrapped()

**File**: `src/wk/shell.py`

Check for the `__WK_WRAPPED` environment variable:

```python
import os

def is_wrapped() -> bool:
    """Return True if the __WK_WRAPPED=1 env var is set.

    Used by cli.py to gate all actions except `wk init`.
    """
    return os.environ.get("__WK_WRAPPED") == "1"
```

### Step 2: Implement generate_wrapper_zsh()

**File**: `src/wk/shell.py`

Return the full zsh function definition for the wk wrapper:

```python
def generate_wrapper_zsh() -> str:
    """Return the full zsh function definition for the wk wrapper.

    The function:
    - Exports __WK_WRAPPED=1
    - Runs the real wk binary, capturing stdout into a variable
    - Passes stderr through to the terminal (Textual renders there)
    - Evals the captured stdout (cd commands, launch commands, etc.)
    """
    return '''wk() {
    export __WK_WRAPPED=1
    local output
    output=$(command wk "$@" 3>&1 1>&2 2>&3 3>&-)
    local exit_code=$?
    unset __WK_WRAPPED
    if [[ $exit_code -eq 0 && -n "$output" ]]; then
        eval "$output"
    fi
}'''
```

The fd swap trick: `3>&1 1>&2 2>&3 3>&-` swaps stdout and stderr so the shell captures the commands (originally stdout) while TUI output (originally stderr) goes to the terminal.

### Step 3: Implement print_shell_commands()

**File**: `src/wk/shell.py`

Write shell commands to stdout, one per line:

```python
import sys

def print_shell_commands(commands: list[str]) -> None:
    """Write shell commands to stdout, one per line.

    The shell wrapper captures and evals this output.
    If commands is empty, prints nothing (clean no-op).
    """
    for cmd in commands:
        print(cmd, file=sys.stdout)
```

### Step 4: Implement run_setup_flow()

**File**: `src/wk/shell.py`

Interactive first-run setup flow:

```python
from pathlib import Path

def run_setup_flow() -> None:
    """Interactive first-run setup. Writes to stderr for all prompts/output.

    Flow:
    1. Check $SHELL ends with /zsh. If not, print "only zsh is supported" and return.
    2. Print explanation of what the wrapper does.
    3. Ask "Install shell wrapper to ~/.zshrc? (y/n)" (read from /dev/tty).
    4. If yes:
       a. Show the exact lines that will be appended.
       b. Ask "Confirm? (y/n)".
       c. Append to ~/.zshrc.
       d. Print "Run `source ~/.zshrc` to activate."
    5. If no: print manual setup instructions (the eval line).
    """
```

Key implementation details:
- All prompts/output go to **stderr** (not stdout, which is reserved for shell commands)
- Read input from `/dev/tty` (not stdin, which may be piped)
- Check `$SHELL` env var for zsh support
- The wrapper line to append: `eval "$(wk init zsh)"`

## Tests

**File**: `tests/test_shell.py`

| Test Name | Description |
|-----------|-------------|
| `test_is_wrapped_true_when_env_set` | Set `os.environ["__WK_WRAPPED"] = "1"`, assert `is_wrapped()` returns `True` |
| `test_is_wrapped_false_when_env_unset` | Ensure env var unset, assert `is_wrapped()` returns `False` |
| `test_is_wrapped_false_when_env_not_one` | Set env var to "0" or other value, assert `False` |
| `test_generate_wrapper_zsh_contains_key_elements` | Assert output contains `wk()`, `__WK_WRAPPED`, `eval`, `command wk` |
| `test_generate_wrapper_zsh_is_valid_syntax` | Optionally pipe through `zsh -n` for syntax validation |
| `test_print_shell_commands_writes_to_stdout` | Capture stdout, call with `["cd /tmp", "echo hi"]`, assert both lines present |
| `test_print_shell_commands_empty_list` | Capture stdout, call with `[]`, assert stdout is empty |
| `test_print_shell_commands_single_command` | Call with single command, verify output |
| `test_run_setup_flow_non_zsh_shell` | Mock `$SHELL` to `/bin/bash`, capture stderr, assert mentions "zsh" and "not supported" |
| `test_run_setup_flow_appends_on_confirm` | Mock input to return "y" twice, use temp file as .zshrc, assert wrapper line appended |
| `test_run_setup_flow_shows_manual_on_decline` | Mock input to return "n", capture stderr, assert contains `eval "$(wk init zsh)"` |
| `test_run_setup_flow_reads_from_tty` | Verify prompts work when stdin is piped. Mock `/dev/tty` in tests |

### Test Setup/Teardown

For tests that modify `os.environ`, use fixtures or try/finally to ensure cleanup:

```python
import os
import pytest

@pytest.fixture
def clean_env():
    """Ensure __WK_WRAPPED is unset before and after test."""
    os.environ.pop("__WK_WRAPPED", None)
    yield
    os.environ.pop("__WK_WRAPPED", None)
```

## Completion Criteria

- [ ] `is_wrapped()` implemented
- [ ] `generate_wrapper_zsh()` implemented
- [ ] `print_shell_commands()` implemented
- [ ] `run_setup_flow()` implemented
- [ ] All test cases passing
- [ ] `uv run ./checks.sh` passes (format, lint, types, tests)
