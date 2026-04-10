"""Tests for agent state detection."""

from wk.status.agent import (
    IDLE,
    OFF,
    WAITING,
    WORKING,
    _strip_ansi,
    detect_agent_state,
)


class TestStripAnsi:
    """Tests for ANSI stripping."""

    def test_strips_color_codes(self) -> None:
        assert _strip_ansi("\x1b[32mgreen\x1b[0m") == "green"

    def test_preserves_plain_text(self) -> None:
        assert _strip_ansi("hello world") == "hello world"

    def test_strips_mixed(self) -> None:
        result = _strip_ansi("\x1b[1m\x1b[31mError:\x1b[0m failed")
        assert result == "Error: failed"


class TestDetectAgentState:
    """Tests for detect_agent_state pattern matching."""

    def test_working_thinking(self) -> None:
        """Should detect 'Thinking' as WORKING."""
        assert detect_agent_state("Thinking") == WORKING
        assert detect_agent_state("Thinking...") == WORKING

    def test_waiting_question(self) -> None:
        """Should detect ❯ with content after as WAITING."""
        assert detect_agent_state("❯ 1. Yes") == WAITING
        assert detect_agent_state("❯ Do you want to proceed?") == WAITING

    def test_waiting_question_before_prompt(self) -> None:
        """Should detect question mark before bare ❯ as WAITING."""
        output = "Do the changes look good?\n\n❯"
        assert detect_agent_state(output) == WAITING
        output = "looks good?\n✻ Worked for 2m\n\n❯"
        assert detect_agent_state(output) == WAITING

    def test_no_question_before_prompt(self) -> None:
        """No question mark before bare ❯ should be IDLE."""
        output = "All done.\n\n❯"
        assert detect_agent_state(output) == IDLE

    def test_idle_bare_prompt(self) -> None:
        """Should detect bare ❯ as IDLE."""
        assert detect_agent_state("❯") == IDLE
        assert detect_agent_state("❯ ") == IDLE

    def test_idle_prompt_not_indented(self) -> None:
        """Indented ❯ should not match idle (it's a menu selector)."""
        assert detect_agent_state("  ❯ Option 1") == OFF

    def test_unknown_defaults_to_off(self) -> None:
        """Unknown output should default to OFF."""
        assert detect_agent_state("some random output") == OFF

    def test_ansi_codes_stripped(self) -> None:
        """Should detect patterns even with ANSI codes."""
        output = "\x1b[32mThinking\x1b[0m"
        assert detect_agent_state(output) == WORKING

    def test_priority_working_over_waiting(self) -> None:
        """Thinking should take priority over waiting."""
        output = "Thinking\n❯ 1. Yes"
        assert detect_agent_state(output) == WORKING

    def test_last_prompt_wins(self) -> None:
        """Only the last ❯ line determines state."""
        # Old waiting prompt followed by bare prompt = idle
        assert detect_agent_state("❯ 1. Yes\n❯") == IDLE
        # Old bare prompt followed by waiting prompt = waiting
        assert detect_agent_state("❯\n❯ 1. Yes") == WAITING
