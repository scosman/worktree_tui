"""Tests for CLI entry point."""

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from wk.cli import main
from wk.config import WkConfig
from wk.worktree import Worktree, WtCommandError


def make_worktree(name: str = "test", path: str | Path = "/test/path") -> Worktree:
    """Helper to create a Worktree for testing."""
    return Worktree(
        name=name,
        path=Path(path),
        branch=name,
        created=datetime.now(UTC),
    )


class TestInitZsh:
    """Tests for `wk init zsh` command."""

    def test_init_zsh_prints_wrapper_function(self) -> None:
        """`wk init zsh` should print the shell wrapper function."""
        result = subprocess.run(
            ["uv", "run", "wk", "init", "zsh"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "wk()" in result.stdout
        assert "__WK_WRAPPED" in result.stdout

    def test_init_zsh_works_without_wrapper_env(self) -> None:
        """`wk init zsh` should work without __WK_WRAPPED env var."""
        # Remove __WK_WRAPPED if present
        env = dict(os.environ)
        env.pop("__WK_WRAPPED", None)

        result = subprocess.run(
            ["uv", "run", "wk", "init", "zsh"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0
        assert "wk()" in result.stdout

    def test_init_bash_prints_error(self) -> None:
        """`wk init bash` should print an error (only zsh supported)."""
        result = subprocess.run(
            ["uv", "run", "wk", "init", "bash"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "zsh" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_init_without_shell_prints_usage(self) -> None:
        """`wk init` without shell arg should print usage."""
        result = subprocess.run(
            ["uv", "run", "wk", "init"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "Usage" in result.stderr or "usage" in result.stderr


class TestWrapperEnforcement:
    """Tests for shell wrapper enforcement."""

    def test_tui_without_wrapper_triggers_setup(self) -> None:
        """`wk` without wrapper should trigger setup flow."""
        env = dict(os.environ)
        env.pop("__WK_WRAPPED", None)

        result = subprocess.run(
            ["uv", "run", "wk"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode != 0
        # Setup flow prints to stderr
        assert (
            "Shell Wrapper Setup" in result.stderr or "wrapper" in result.stderr.lower()
        )


class TestNewCommand:
    """Tests for `wk new <name>` command."""

    def test_new_without_name_prints_usage(self) -> None:
        """`wk new` without name should print usage."""
        env = dict(os.environ)
        env["__WK_WRAPPED"] = "1"

        result = subprocess.run(
            ["uv", "run", "wk", "new"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode != 0
        assert "Usage" in result.stderr or "usage" in result.stderr

    def test_new_with_name_creates_and_launches(self) -> None:
        """`wk new <name>` should create worktree and print launch commands."""
        config = WkConfig(open_workspace_cmd="code .")

        with (
            patch("wk.cli.load_config") as mock_config,
            patch("wk.cli.actions.action_new") as mock_action,
        ):
            mock_config.return_value = config
            mock_action.return_value = ["cd /project/.worktrees/my-feature", "code ."]

            with patch.object(sys, "argv", ["wk", "new", "my-feature"]):
                with patch("wk.cli.is_wrapped", return_value=True):
                    with patch("wk.cli.print_shell_commands") as mock_print:
                        main()
                        mock_action.assert_called_once_with("my-feature", config)
                        mock_print.assert_called_once_with(
                            ["cd /project/.worktrees/my-feature", "code ."]
                        )

    def test_new_propagates_wt_command_error(self) -> None:
        """`wk new <name>` should print error on WtCommandError."""
        config = WkConfig(open_workspace_cmd="code .")

        with (
            patch("wk.cli.load_config") as mock_config,
            patch("wk.cli.actions.action_new") as mock_action,
        ):
            mock_config.return_value = config
            mock_action.side_effect = WtCommandError(
                command="wt switch --create my-feature --base=@ --yes",
                stderr="error: branch already exists",
                returncode=1,
            )

            with patch.object(sys, "argv", ["wk", "new", "my-feature"]):
                with patch("wk.cli.is_wrapped", return_value=True):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code != 0


class TestLaunchCommand:
    """Tests for `wk <name>` command."""

    def test_launch_existing_worktree(self) -> None:
        """`wk <name>` should launch existing worktree."""
        worktree = make_worktree(
            name="my-feature",
            path="/project/.worktrees/my-feature",
        )
        config = WkConfig(open_workspace_cmd="code .")

        with (
            patch("wk.cli.load_config") as mock_config,
            patch("wk.cli.find_worktree") as mock_find,
            patch("wk.cli.actions.action_launch") as mock_launch,
        ):
            mock_config.return_value = config
            mock_find.return_value = worktree
            mock_launch.return_value = ["cd /project/.worktrees/my-feature", "code ."]

            with patch.object(sys, "argv", ["wk", "my-feature"]):
                with patch("wk.cli.is_wrapped", return_value=True):
                    with patch("wk.cli.print_shell_commands") as mock_print:
                        main()
                        mock_find.assert_called_once_with("my-feature")
                        mock_launch.assert_called_once_with(worktree, config)
                        mock_print.assert_called_once_with(
                            ["cd /project/.worktrees/my-feature", "code ."]
                        )

    def test_launch_nonexistent_prints_error(self) -> None:
        """`wk <nonexistent>` should print error."""
        config = WkConfig(open_workspace_cmd="code .")

        with (
            patch("wk.cli.load_config") as mock_config,
            patch("wk.cli.find_worktree") as mock_find,
        ):
            mock_config.return_value = config
            mock_find.return_value = None

            with patch.object(sys, "argv", ["wk", "nonexistent"]):
                with patch("wk.cli.is_wrapped", return_value=True):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code != 0


class TestSelectorCommand:
    """Tests for `wk selector` command."""

    def test_selector_runs_app_in_persistent_mode(self) -> None:
        """`wk selector` should run TUI in persistent mode."""
        worktrees = [make_worktree(name="feature-1")]
        config = WkConfig(open_workspace_cmd="code .")

        with (
            patch("wk.cli.load_config") as mock_config,
            patch("wk.cli.list_worktrees") as mock_list,
            patch("wk.cli.run_app") as mock_run,
        ):
            mock_config.return_value = config
            mock_list.return_value = worktrees
            mock_run.return_value = []

            with patch.object(sys, "argv", ["wk", "selector"]):
                main()
                mock_run.assert_called_once_with(worktrees, config, persistent=True)

    def test_selector_does_not_require_wrapper(self) -> None:
        """`wk selector` should not require the shell wrapper."""
        with (
            patch("wk.cli.load_config") as mock_config,
            patch("wk.cli.list_worktrees") as mock_list,
            patch("wk.cli.run_app") as mock_run,
        ):
            mock_config.return_value = WkConfig()
            mock_list.return_value = []
            mock_run.return_value = []

            with patch.object(sys, "argv", ["wk", "selector"]):
                # Should not call is_wrapped or run_setup_flow
                main()
                mock_run.assert_called_once()



class TestTuiMode:
    """Tests for TUI mode (no arguments)."""

    def test_tui_runs_classic_without_zellij(self) -> None:
        """`wk` without zellij should run classic TUI."""
        worktrees = [make_worktree(name="feature-1")]
        config = WkConfig(open_workspace_cmd="code .")

        with (
            patch("wk.cli.load_config") as mock_config,
            patch("wk.cli.list_worktrees") as mock_list,
            patch("wk.cli.run_app") as mock_run,
            patch("wk.layout.is_zellij_available", return_value=False),
        ):
            mock_config.return_value = config
            mock_list.return_value = worktrees
            mock_run.return_value = ["cd /project/.worktrees/feature-1", "code ."]

            with patch.object(sys, "argv", ["wk"]):
                with patch("wk.cli.is_wrapped", return_value=True):
                    with patch("wk.cli.print_shell_commands") as mock_print:
                        main()
                        mock_run.assert_called_once_with(worktrees, config)
                        mock_print.assert_called_once_with(
                            ["cd /project/.worktrees/feature-1", "code ."]
                        )

    def test_tui_launches_zellij_when_available(self) -> None:
        """`wk` should launch Zellij dashboard when available."""
        config = WkConfig(repo_root=Path("/test/repo"))

        with (
            patch("wk.cli.load_config") as mock_config,
            patch("wk.layout.is_zellij_available", return_value=True),
            patch("wk.layout.is_inside_zellij", return_value=False),
            patch("wk.layout.launch_zellij") as mock_launch,
        ):
            mock_config.return_value = config
            mock_launch.return_value = ["zellij --layout /tmp/x.kdl"]

            with patch.object(sys, "argv", ["wk"]):
                with patch("wk.cli.is_wrapped", return_value=True):
                    with patch("wk.cli.print_shell_commands") as mock_print:
                        main()
                        mock_launch.assert_called_once_with(config)
                        mock_print.assert_called_once()

    def test_tui_falls_back_inside_zellij(self) -> None:
        """`wk` inside Zellij should fall back to classic TUI."""
        worktrees = [make_worktree(name="feature-1")]
        config = WkConfig()

        with (
            patch("wk.cli.load_config") as mock_config,
            patch("wk.cli.list_worktrees") as mock_list,
            patch("wk.cli.run_app") as mock_run,
            patch("wk.layout.is_zellij_available", return_value=True),
            patch("wk.layout.is_inside_zellij", return_value=True),
        ):
            mock_config.return_value = config
            mock_list.return_value = worktrees
            mock_run.return_value = []

            with patch.object(sys, "argv", ["wk"]):
                with patch("wk.cli.is_wrapped", return_value=True):
                    with patch("wk.cli.print_shell_commands"):
                        main()
                        mock_run.assert_called_once()
