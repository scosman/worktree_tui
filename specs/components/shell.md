# Component: `shell.py`

**Location**: `src/wk/shell.py`

## Goal

Manage the shell wrapper lifecycle: detect if `wk` is running inside the wrapper, generate the wrapper function, handle the first-run setup flow, and provide the protocol for sending shell commands back to the parent shell via stdout.

## Public Interface

```python
def is_wrapped() -> bool:
    """Return True if the __WK_WRAPPED=1 env var is set.

    Used by cli.py to gate all actions except `wk init`.
    """

def generate_wrapper_zsh() -> str:
    """Return the full zsh function definition for the wk wrapper.

    The function:
    - Exports __WK_WRAPPED=1
    - Runs the real wk binary, capturing stdout into a variable
    - Passes stderr through to the terminal (Textual renders there)
    - Evals the captured stdout (cd commands, launch commands, etc.)

    Output is suitable for both:
    - `eval "$(wk init zsh)"` in .zshrc
    - Direct appending to .zshrc by the setup flow
    """

def print_shell_commands(commands: list[str]) -> None:
    """Write shell commands to stdout, one per line.

    The shell wrapper captures and evals this output.
    If commands is empty, prints nothing (clean no-op).
    """

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

## Shell Wrapper Function (generated output)

```zsh
wk() {
    export __WK_WRAPPED=1
    local output
    output=$(command wk "$@" 3>&1 1>&2 2>&3 3>&-)
    local exit_code=$?
    unset __WK_WRAPPED
    if [[ $exit_code -eq 0 && -n "$output" ]]; then
        eval "$output"
    fi
}
```

**fd swap trick**: The Python program writes TUI to stderr and shell commands to stdout. The wrapper swaps fd1/fd2 so the shell captures the commands while the TUI output goes to the terminal. 

*Note*: The actual fd redirect strategy needs validation during implementation. The key invariant is: **Textual renders to the terminal, shell commands are captured by the wrapper.**

## Design Patterns

- **Strategy (implicit)**: `generate_wrapper_zsh()` is the zsh strategy. Adding bash/fish later means adding `generate_wrapper_bash()` etc.
- **Separation of concerns**: this module owns *all* shell-integration logic. No other module writes to stdout or knows about the wrapper.

## Dependencies (internal)

None. This is a leaf module with no internal dependencies.

## Dependencies (external)

- `os` — env var access
- `pathlib.Path` — `~/.zshrc` path
- `sys` — stderr output

## Testing Strategy

### Test Cases

| # | Test Case | Method |
|---|-----------|--------|
| 1 | `is_wrapped()` returns `True` when env var set | Unit: set `os.environ["__WK_WRAPPED"] = "1"`, assert `True`. Clean up in teardown. |
| 2 | `is_wrapped()` returns `False` when env var absent | Unit: ensure env var unset, assert `False` |
| 3 | `generate_wrapper_zsh()` returns valid zsh syntax | Unit: assert output contains `wk()`, `__WK_WRAPPED`, `eval`. Optionally pipe through `zsh -n` for syntax check. |
| 4 | `print_shell_commands` writes to stdout | Unit: capture stdout, call with `["cd /tmp", "echo hi"]`, assert both lines present |
| 5 | `print_shell_commands` with empty list writes nothing | Unit: capture stdout, call with `[]`, assert stdout is empty |
| 6 | `run_setup_flow` with non-zsh shell prints unsupported | Unit: mock `$SHELL` to `/bin/bash`, capture stderr, assert "zsh" mentioned |
| 7 | `run_setup_flow` appends to .zshrc on confirm | Unit: mock input to return "y" twice, use a temp file as .zshrc, assert `eval "$(wk init zsh)"` was appended |
| 8 | `run_setup_flow` prints manual instructions on decline | Unit: mock input to return "n", capture stderr, assert contains `eval "$(wk init zsh)"` |
| 9 | Setup flow reads from `/dev/tty` not stdin | Verify prompts work even though stdin may be piped. Mock `/dev/tty` in tests. |
