"""Tests for shell.py."""

import os
from io import StringIO
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from wk.shell import (
    generate_wrapper_zsh,
    is_wrapped,
    print_shell_commands,
    run_setup_flow,
)


@pytest.fixture
def clean_env():
    """Ensure __WK_WRAPPED is unset before and after test."""
    os.environ.pop("__WK_WRAPPED", None)
    yield
    os.environ.pop("__WK_WRAPPED", None)


class TestIsWrapped:
    """Tests for is_wrapped function."""

    def test_is_wrapped_true_when_env_set(self, clean_env: None) -> None:
        """is_wrapped should return True when __WK_WRAPPED=1."""
        os.environ["__WK_WRAPPED"] = "1"
        assert is_wrapped() is True

    def test_is_wrapped_false_when_env_unset(self, clean_env: None) -> None:
        """is_wrapped should return False when env var is unset."""
        assert is_wrapped() is False

    def test_is_wrapped_false_when_env_not_one(self, clean_env: None) -> None:
        """is_wrapped should return False for values other than '1'."""
        os.environ["__WK_WRAPPED"] = "0"
        assert is_wrapped() is False

    def test_is_wrapped_false_for_random_value(self, clean_env: None) -> None:
        """is_wrapped should return False for random string values."""
        os.environ["__WK_WRAPPED"] = "yes"
        assert is_wrapped() is False


class TestGenerateWrapperZsh:
    """Tests for generate_wrapper_zsh function."""

    def test_generate_wrapper_zsh_contains_wk_function(self) -> None:
        """Output should contain the wk() function definition."""
        result = generate_wrapper_zsh()
        assert "wk()" in result

    def test_generate_wrapper_zsh_contains_wrapped_env(self) -> None:
        """Output should set __WK_WRAPPED environment variable."""
        result = generate_wrapper_zsh()
        assert "__WK_WRAPPED" in result

    def test_generate_wrapper_zsh_contains_eval(self) -> None:
        """Output should eval the captured stdout."""
        result = generate_wrapper_zsh()
        assert "eval" in result

    def test_generate_wrapper_zsh_contains_command_wk(self) -> None:
        """Output should use 'command wk' to call the real binary."""
        result = generate_wrapper_zsh()
        assert "command wk" in result

    def test_generate_wrapper_zsh_contains_output_capture(self) -> None:
        """Output should capture stdout to a variable."""
        result = generate_wrapper_zsh()
        assert "output=" in result

    def test_generate_wrapper_zsh_is_valid_syntax(self) -> None:
        """Generated zsh should be syntactically valid."""
        result = generate_wrapper_zsh()
        # Basic syntax checks
        assert result.count("{") == result.count("}")
        assert result.endswith("}")


class TestPrintShellCommands:
    """Tests for print_shell_commands function."""

    def test_print_shell_commands_writes_to_stdout(self) -> None:
        """Should write each command to stdout on its own line."""
        commands = ["cd /tmp", "echo hi"]
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            print_shell_commands(commands)
            output = mock_stdout.getvalue()

        assert "cd /tmp\n" in output
        assert "echo hi\n" in output

    def test_print_shell_commands_empty_list(self) -> None:
        """Empty list should print nothing."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            print_shell_commands([])
            output = mock_stdout.getvalue()

        assert output == ""

    def test_print_shell_commands_single_command(self) -> None:
        """Single command should be printed correctly."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            print_shell_commands(["cd /home/user/project"])
            output = mock_stdout.getvalue()

        assert output == "cd /home/user/project\n"

    def test_print_shell_commands_preserves_command_content(self) -> None:
        """Should not modify command content."""
        commands = ['export FOO="bar baz"', "cd /tmp && ls -la"]
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            print_shell_commands(commands)
            output = mock_stdout.getvalue()

        assert 'export FOO="bar baz"\n' in output
        assert "cd /tmp && ls -la\n" in output


class TestRunSetupFlow:
    """Tests for run_setup_flow function."""

    def test_run_setup_flow_non_zsh_shell(self) -> None:
        """Should print error for non-zsh shells."""
        with patch.dict(os.environ, {"SHELL": "/bin/bash"}):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                run_setup_flow()
                output = mock_stderr.getvalue()

        assert "zsh" in output.lower()
        assert "not supported" in output.lower() or "only" in output.lower()

    def test_run_setup_flow_empty_shell_env(self) -> None:
        """Should print error when SHELL is not set."""
        with patch.dict(os.environ, {"SHELL": ""}, clear=False):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                run_setup_flow()
                output = mock_stderr.getvalue()

        assert "zsh" in output.lower()

    def test_run_setup_flow_appends_on_confirm(self, tmp_path: Path) -> None:
        """Should append wrapper line to .zshrc when confirmed."""
        zshrc = tmp_path / ".zshrc"
        zshrc.write_text("# existing content\n")

        inputs = iter(["y", "y"])  # Two confirmations

        real_open = open

        def open_side_effect(path, *args, **kwargs):
            if path == "/dev/tty":
                return mock_open(read_data=next(inputs)).return_value
            return real_open(path, *args, **kwargs)

        with patch.dict(os.environ, {"SHELL": "/bin/zsh"}):
            with patch("pathlib.Path.home", return_value=tmp_path):
                with patch("builtins.open", side_effect=open_side_effect):
                    with patch("sys.stderr", new_callable=StringIO):
                        run_setup_flow()

        # Check that wrapper function was appended
        content = zshrc.read_text()
        assert "wk() {" in content
        assert "__WK_WRAPPED" in content

    def test_run_setup_flow_shows_manual_on_decline(self) -> None:
        """Should show manual instructions when user declines."""
        with patch.dict(os.environ, {"SHELL": "/bin/zsh"}):
            with patch("builtins.open", mock_open(read_data="n")) as mock_file:
                # Handle /dev/tty specially
                def open_side_effect(path, *args, **kwargs):
                    if path == "/dev/tty":
                        return mock_open(read_data="n").return_value
                    return mock_file.return_value

                mock_file.side_effect = open_side_effect

                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    run_setup_flow()
                    output = mock_stderr.getvalue()

        assert "wk init zsh" in output

    def test_run_setup_flow_cancels_on_second_decline(self, tmp_path: Path) -> None:
        """Should cancel setup if user declines confirmation."""
        zshrc = tmp_path / ".zshrc"
        original_content = "# existing content\n"
        zshrc.write_text(original_content)

        inputs = iter(["y", "n"])  # Accept first, decline second

        real_open = open

        def open_side_effect(path, *args, **kwargs):
            if path == "/dev/tty":
                return mock_open(read_data=next(inputs)).return_value
            return real_open(path, *args, **kwargs)

        with patch.dict(os.environ, {"SHELL": "/bin/zsh"}):
            with patch("pathlib.Path.home", return_value=tmp_path):
                with patch("builtins.open", side_effect=open_side_effect):
                    with patch("sys.stderr", new_callable=StringIO):
                        run_setup_flow()

        # Content should be unchanged
        content = zshrc.read_text()
        assert content == original_content

    def test_run_setup_flow_reads_from_tty(self) -> None:
        """Should read from /dev/tty, not stdin."""
        tty_opened = False

        def track_tty_open(path, *args, **kwargs):
            nonlocal tty_opened
            if path == "/dev/tty":
                tty_opened = True
                return mock_open(read_data="n").return_value
            return mock_open(read_data="should not be used").return_value

        with patch.dict(os.environ, {"SHELL": "/bin/zsh"}):
            with patch("builtins.open", side_effect=track_tty_open):
                with patch("sys.stderr", new_callable=StringIO):
                    run_setup_flow()

        assert tty_opened
