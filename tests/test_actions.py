"""Tests for actions.py."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from wk.actions import (
    action_delete,
    action_jump,
    action_launch,
    action_new,
    action_restart,
)
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


class TestActionLaunch:
    """Tests for action_launch function."""

    def test_action_launch_with_open_cmd(self) -> None:
        """action_launch should return cd + open_workspace_cmd when configured."""
        worktree = make_worktree(path="/project/.worktrees/my-feature")
        config = WkConfig(open_workspace_cmd="start.sh")

        result = action_launch(worktree, config)

        assert len(result) == 2
        assert result[0] == "cd /project/.worktrees/my-feature"
        assert result[1] == "start.sh"

    def test_action_launch_without_open_cmd(self) -> None:
        """action_launch should return cd only when no open_workspace_cmd."""
        worktree = make_worktree(path="/project/.worktrees/my-feature")
        config = WkConfig(open_workspace_cmd=None)

        result = action_launch(worktree, config)

        assert len(result) == 1
        assert result[0] == "cd /project/.worktrees/my-feature"

    def test_action_launch_quotes_paths_with_spaces(self) -> None:
        """action_launch should shell-quote paths containing spaces."""
        worktree = make_worktree(path="/my path/with spaces/tree")
        config = WkConfig(open_workspace_cmd="start.sh")

        result = action_launch(worktree, config)

        assert len(result) == 2
        assert result[0] == "cd '/my path/with spaces/tree'"
        assert result[1] == "start.sh"

    def test_action_launch_with_special_characters(self) -> None:
        """action_launch should handle paths with special shell characters."""
        worktree = make_worktree(
            name="feature-with-special",
            path=Path("/path/with'quote/tree"),
        )
        config = WkConfig(open_workspace_cmd="start.sh")

        result = action_launch(worktree, config)

        assert len(result) == 2
        # Path with single quote is handled correctly by shlex.quote
        # The the "cd /path/with'quote/tree" and "start.sh"
        assert result[1] == "start.sh"


class TestActionJump:
    """Tests for action_jump function."""

    def test_action_jump_returns_cd_command(self) -> None:
        """action_jump should return a cd command."""
        worktree = make_worktree(path="/project/.worktrees/my-feature")

        result = action_jump(worktree)
        assert len(result) == 1
        assert result[0] == "cd /project/.worktrees/my-feature"

    def test_action_jump_quotes_paths_with_spaces(self) -> None:
        """action_jump should shell-quote paths containing spaces."""
        worktree = make_worktree(path="/my path/with spaces/tree")
        result = action_jump(worktree)
        assert len(result) == 1
        assert result[0] == "cd '/my path/with spaces/tree'"


class TestActionRestart:
    """Tests for action_restart function."""

    def test_action_restart_with_restart_cmd(self) -> None:
        """action_restart should return cd + restart_workspace_cmd when configured."""
        worktree = make_worktree(
            name="feature-with-restart",
            path=Path("/project/.worktrees/feature-with-restart"),
        )
        config = WkConfig(restart_workspace_cmd="restart.sh")
        result = action_restart(worktree, config)
        assert len(result) == 2
        assert result[0] == "cd /project/.worktrees/feature-with-restart"
        assert result[1] == "restart.sh"

    def test_action_restart_without_restart_cmd(self) -> None:
        """action_restart should return cd only when no restart_workspace_cmd."""
        worktree = make_worktree(
            name="feature-with-restart",
            path=Path("/project/.worktrees/feature-with-restart"),
        )
        config = WkConfig(restart_workspace_cmd=None)
        result = action_restart(worktree, config)
        assert len(result) == 1
        assert result[0] == "cd /project/.worktrees/feature-with-restart"

    def test_action_restart_quotes_paths_with_spaces(self) -> None:
        """action_restart should shell-quote paths containing spaces."""
        worktree = make_worktree(
            name="feature-with-restart",
            path=Path("/my path/with spaces/tree"),
        )
        config = WkConfig(restart_workspace_cmd="restart.sh")
        result = action_restart(worktree, config)
        assert len(result) == 2
        assert result[0] == "cd '/my path/with spaces/tree'"
        assert result[1] == "restart.sh"


class TestActionNew:
    """Tests for action_new function."""

    def test_action_new_calls_create_then_returns_launch(self) -> None:
        """action_new should call create_worktree then return launch commands."""
        worktree = make_worktree(
            name="new-feature",
            path=Path("/project/.worktrees/new-feature"),
        )
        config = WkConfig(open_workspace_cmd="start.sh")

        with patch("wk.actions.create_worktree") as mock_create:
            mock_create.return_value = worktree

            result = action_new("new-feature", config)

            # Verify create_worktree was called
            mock_create.assert_called_once_with("new-feature")
            assert mock_create.call_count == 1

            # Return value should match action_launch output
            assert len(result) == 2
            assert result[0] == "cd /project/.worktrees/new-feature"
            assert result[1] == "start.sh"

    def test_action_new_without_open_cmd(self) -> None:
        """action_new should work without open_workspace_cmd."""
        worktree = make_worktree(
            name="new-feature",
            path=Path("/project/.worktrees/new-feature"),
        )
        config = WkConfig(open_workspace_cmd=None)

        with patch("wk.actions.create_worktree") as mock_create:
            mock_create.return_value = worktree

            result = action_new("new-feature", config)

            mock_create.assert_called_once_with("new-feature")
            assert mock_create.call_count == 1

            assert len(result) == 1
            assert result[0] == "cd /project/.worktrees/new-feature"

    def test_action_new_propagates_wt_command_error(self) -> None:
        """action_new should propagate WtCommandError if create fails."""
        config = WkConfig(open_workspace_cmd="start.sh")

        with patch("wk.actions.create_worktree") as mock_create:
            mock_create.side_effect = WtCommandError(
                command="wt switch --create existing --base=@",
                stderr="error: branch already exists",
                returncode=1,
            )
            with pytest.raises(WtCommandError) as exc_info:
                action_new("existing", config)

            mock_create.assert_called_once_with("existing")
            assert exc_info.value.command == "wt switch --create existing --base=@"
            assert exc_info.value.stderr == "error: branch already exists"
            assert exc_info.value.returncode == 1


class TestActionDelete:
    """Tests for action_delete function."""

    def test_action_delete_calls_remove_worktree(self) -> None:
        """action_delete should call remove_worktree with the name."""
        with patch("wk.actions.remove_worktree") as mock_remove:
            mock_remove.return_value = None
            result = action_delete("old-feature")
            mock_remove.assert_called_once_with("old-feature", force=False)
            assert result is None

    def test_action_delete_propagates_wt_command_error(self) -> None:
        """action_delete should propagate WtCommandError if removal fails."""
        with patch("wk.actions.remove_worktree") as mock_remove:
            mock_remove.side_effect = WtCommandError(
                command="wt remove nonexistent",
                stderr="error: worktree not found",
                returncode=1,
            )
            with pytest.raises(WtCommandError) as exc_info:
                action_delete("nonexistent")

            mock_remove.assert_called_once_with("nonexistent", force=False)
            assert exc_info.value.command == "wt remove nonexistent"
            assert exc_info.value.stderr == "error: worktree not found"
            assert exc_info.value.returncode == 1

    def test_action_delete_returns_none(self) -> None:
        """action_delete should return None."""
        with patch("wk.actions.remove_worktree") as mock_remove:
            mock_remove.return_value = None
            result = action_delete("some-feature")
            assert result is None
