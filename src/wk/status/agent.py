"""Agent state detection via tmux pane output pattern matching.

Detects Claude Code agent states by pattern-matching the last 25 lines
of a tmux pane's output.
"""

import re
import subprocess

# Agent states
WORKING = "work"
WAITING = "wait"
IDLE = "idle"
OFF = "-"

# ANSI escape code stripper
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\x1b\[.*?[@-~]")

# Pattern for working state (searched across full output)
_WORKING_RE = re.compile(r"Thinking")

# Patterns for the last ❯ line only
_PROMPT_RE = re.compile(r"^❯(.*)$", re.MULTILINE)
_HAS_CONTENT_RE = re.compile(r"^\s+\S")


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return _ANSI_RE.sub("", text)


def detect_agent_state(pane_output: str) -> str:
    """Detect the agent state from tmux pane output.

    Args:
        pane_output: Raw text from tmux capture-pane (may contain ANSI codes).

    Returns:
        One of: "work", "wait", "idle", "-".
    """
    clean = _strip_ansi(pane_output)

    if _WORKING_RE.search(clean):
        return WORKING

    # Find the last ❯ line and check what follows it
    matches = list(_PROMPT_RE.finditer(clean))
    if matches:
        after = matches[-1].group(1)
        if _HAS_CONTENT_RE.match(after):
            return WAITING
        # Check if a recent line before the prompt ends with ?
        # Look back up to 5 non-empty lines for a question
        before_lines = clean[: matches[-1].start()].splitlines()
        checked = 0
        for line in reversed(before_lines):
            stripped = line.rstrip()
            if not stripped:
                continue
            if stripped.endswith("?"):
                return WAITING
            checked += 1
            if checked >= 5:
                break
        return IDLE

    return OFF


def _tmux_cmd(*args: str) -> subprocess.CompletedProcess[str]:
    """Run tmux on the wk socket."""
    return subprocess.run(
        ["tmux", "-L", "wk", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def detect_agent_state_for_session(session: str, window: str = "agent") -> str:
    """Detect agent state for a tmux session/window.

    Args:
        session: Tmux session name (e.g., "wk-KIL-123").
        window: Window name within the session.

    Returns:
        One of: "work", "idle", "-".
    """
    # Check if session exists
    result = _tmux_cmd("has-session", "-t", session)
    if result.returncode != 0:
        return OFF

    # Capture pane output
    result = _tmux_cmd("capture-pane", "-p", "-t", f"{session}:{window}", "-S", "-25")
    if result.returncode != 0:
        return OFF

    output = result.stdout
    if not output.strip():
        return OFF

    return detect_agent_state(output)
