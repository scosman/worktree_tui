"""Shell wrapper generation and detection."""

import os
import sys
from pathlib import Path


def is_wrapped() -> bool:
    """Return True if the __WK_WRAPPED=1 env var is set.

    Used by cli.py to gate all actions except `wk init`.
    """
    return os.environ.get("__WK_WRAPPED") == "1"


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
    return """wk() {
    if ! whence -p wk &> /dev/null; then
        echo "error: wk command not found" >&2
        return 1
    fi
    export __WK_WRAPPED=1
    local output
    output=$(command wk "$@")
    local exit_code=$?
    unset __WK_WRAPPED
    if [[ $exit_code -eq 0 && -n "$output" ]]; then
        eval "$output"
    fi
}"""


def print_shell_commands(commands: list[str]) -> None:
    """Write shell commands to stdout, one per line.

    The shell wrapper captures and evals this output.
    If commands is empty, prints nothing (clean no-op).
    """
    for cmd in commands:
        print(cmd, file=sys.stdout)


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
    shell = os.environ.get("SHELL", "")

    # Check if zsh is the current shell
    if not shell.endswith("/zsh"):
        print("Error: Only zsh is supported at this time.", file=sys.stderr)
        print(f"Current shell: {shell}", file=sys.stderr)
        return

    zshrc_path = Path.home() / ".zshrc"
    wrapper_content = generate_wrapper_zsh()

    # Print explanation
    print("\nwk Shell Wrapper Setup", file=sys.stderr)
    print("=" * 40, file=sys.stderr)
    print(
        "\nThe shell wrapper allows wk to change your current directory",
        file=sys.stderr,
    )
    print(
        "and run commands in your shell after you select a worktree.",
        file=sys.stderr,
    )
    print(
        "\nThis requires adding a wrapper function to your ~/.zshrc file.",
        file=sys.stderr,
    )

    # Ask to install
    prompt = f"\nInstall shell wrapper to {zshrc_path}? (y/n): "
    print(prompt, file=sys.stderr, end="", flush=True)

    try:
        with open("/dev/tty") as tty:
            response = tty.readline().strip().lower()
    except OSError:
        # Fallback to stdin if /dev/tty is not available
        response = input().strip().lower()

    if response != "y":
        print("\nManual setup instructions:", file=sys.stderr)
        print("  Run: wk init zsh", file=sys.stderr)
        print("  Then add the output to your ~/.zshrc", file=sys.stderr)
        print("\n  Then run: source ~/.zshrc", file=sys.stderr)
        return

    # Show what will be appended
    print("\nThe following will be appended to ~/.zshrc:", file=sys.stderr)
    for line in wrapper_content.splitlines():
        print(f"  {line}", file=sys.stderr)
    print("\nConfirm? (y/n): ", file=sys.stderr, end="", flush=True)

    try:
        with open("/dev/tty") as tty:
            response = tty.readline().strip().lower()
    except OSError:
        response = input().strip().lower()

    if response != "y":
        print("\nSetup cancelled.", file=sys.stderr)
        return

    # Append to .zshrc
    with open(zshrc_path, "a") as f:
        f.write(f"\n# wk worktree manager\n{wrapper_content}\n")

    print("\nShell wrapper installed successfully!", file=sys.stderr)
    print("Run `source ~/.zshrc` to activate.", file=sys.stderr)
