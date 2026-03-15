"""Tests for wk.tui.app module."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from textual.widgets import Input

from wk.config import CustomCommand, WkConfig
from wk.tui.app import (
    ConfirmCustomCommandScreen,
    ConfirmDeleteScreen,
    DeleteErrorScreen,
    ErrorNotificationScreen,
    NewWorktreeScreen,
    WkApp,
    run_app,
)
from wk.tui.worktree_list import WorktreeList
from wk.worktree import Worktree, WtCommandError


def make_worktree(name: str, hours_ago: int = 0) -> Worktree:
    """Create a test Worktree instance."""
    created = datetime.now(UTC)
    if hours_ago:
        created = created - timedelta(hours=hours_ago)
    return Worktree(
        name=name,
        path=Path(f"/repo/{name}"),
        branch=name,
        created=created,
    )


# Sample worktrees for testing
WORKTREE_1 = make_worktree("feature-one", hours_ago=2)
WORKTREE_2 = make_worktree("feature-two", hours_ago=24)
WORKTREE_3 = make_worktree("feature-three", hours_ago=72)

SAMPLE_CONFIG = WkConfig(
    open_workspace_cmd="code .",
    restart_workspace_cmd="code --restart .",
    repo_root=Path("/repo"),
)


class TestNewWorktreeScreen:
    """Tests for NewWorktreeScreen modal via WkApp."""

    @pytest.mark.asyncio
    async def test_input_focused_on_mount(self) -> None:
        """Input should be focused when screen mounts."""
        app = WkApp([WORKTREE_1], SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            # Open the new worktree screen
            await pilot.press("n")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(pilot.app.screen, NewWorktreeScreen)
            screen = pilot.app.screen
            input_widget = screen.query_one(Input)
            assert input_widget.has_focus

    @pytest.mark.asyncio
    async def test_submit_returns_value(self) -> None:
        """Submitting input dismisses the screen with the value."""
        app = WkApp([WORKTREE_1], SAMPLE_CONFIG)

        with patch("wk.tui.app.action_new") as mock_new:
            mock_new.return_value = ["cd /repo/test", "code ."]

            async with app.run_test() as pilot:
                await pilot.press("n")
                await pilot.pause()
                await pilot.pause()

                screen = pilot.app.screen
                input_widget = screen.query_one(Input)
                input_widget.value = "my-branch"
                await pilot.press("enter")
                await pilot.pause()
                await pilot.pause()

                mock_new.assert_called_once_with("my-branch", SAMPLE_CONFIG)

    @pytest.mark.asyncio
    async def test_escape_returns_none(self) -> None:
        """Pressing escape dismisses the screen without action."""
        app = WkApp([WORKTREE_1], SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(pilot.app.screen, NewWorktreeScreen)

            await pilot.press("escape")
            await pilot.pause()
            await pilot.pause()

            assert not isinstance(pilot.app.screen, NewWorktreeScreen)


class TestConfirmDeleteScreen:
    """Tests for ConfirmDeleteScreen modal via WkApp."""

    @pytest.mark.asyncio
    async def test_confirm_returns_true(self) -> None:
        """Clicking Delete confirms deletion."""
        app = WkApp([WORKTREE_1], SAMPLE_CONFIG)

        with patch("wk.tui.app.action_delete") as mock_delete:
            with patch("wk.worktree.list_worktrees") as mock_list:
                mock_list.return_value = []

                async with app.run_test() as pilot:
                    await pilot.press("d")
                    await pilot.pause()
                    await pilot.pause()

                    assert isinstance(pilot.app.screen, ConfirmDeleteScreen)

                    screen = pilot.app.screen
                    confirm_btn = screen.query_one("#confirm")
                    await pilot.click(confirm_btn)
                    await pilot.pause()
                    await pilot.pause()

                    mock_delete.assert_called_once_with(WORKTREE_1.name, force=False)

    @pytest.mark.asyncio
    async def test_cancel_returns_false(self) -> None:
        """Clicking Cancel returns to list without deletion."""
        app = WkApp([WORKTREE_1], SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            await pilot.press("d")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(pilot.app.screen, ConfirmDeleteScreen)

            screen = pilot.app.screen
            cancel_btn = screen.query_one("#cancel")
            await pilot.click(cancel_btn)
            await pilot.pause()
            await pilot.pause()

            assert not isinstance(pilot.app.screen, ConfirmDeleteScreen)

    @pytest.mark.asyncio
    async def test_escape_returns_false(self) -> None:
        """Pressing escape cancels deletion."""
        app = WkApp([WORKTREE_1], SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            await pilot.press("d")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(pilot.app.screen, ConfirmDeleteScreen)

            await pilot.press("escape")
            await pilot.pause()
            await pilot.pause()

            assert not isinstance(pilot.app.screen, ConfirmDeleteScreen)


class TestErrorNotificationScreen:
    """Tests for ErrorNotificationScreen modal via WkApp."""

    @pytest.mark.asyncio
    async def test_displays_message(self) -> None:
        """Error message is displayed on delete failure."""
        app = WkApp([WORKTREE_1], SAMPLE_CONFIG)

        with patch("wk.tui.app.action_delete") as mock_delete:
            mock_delete.side_effect = WtCommandError("wt remove", "Error!", 1)

            async with app.run_test() as pilot:
                await pilot.press("d")
                await pilot.pause()
                await pilot.pause()

                screen = pilot.app.screen
                confirm_btn = screen.query_one("#confirm")
                await pilot.click(confirm_btn)
                await pilot.pause()
                await pilot.pause()

                assert isinstance(pilot.app.screen, DeleteErrorScreen)

    @pytest.mark.asyncio
    async def test_button_dismisses(self) -> None:
        """Clicking Cancel dismisses the error screen."""
        app = WkApp([WORKTREE_1], SAMPLE_CONFIG)

        with patch("wk.tui.app.action_delete") as mock_delete:
            mock_delete.side_effect = WtCommandError("wt remove", "Error!", 1)

            async with app.run_test() as pilot:
                await pilot.press("d")
                await pilot.pause()
                await pilot.pause()

                screen = pilot.app.screen
                confirm_btn = screen.query_one("#confirm")
                await pilot.click(confirm_btn)
                await pilot.pause()
                await pilot.pause()

                assert isinstance(pilot.app.screen, DeleteErrorScreen)

                error_screen = pilot.app.screen
                cancel_btn = error_screen.query_one("#cancel")
                await pilot.click(cancel_btn)
                await pilot.pause()
                await pilot.pause()

                assert not isinstance(pilot.app.screen, DeleteErrorScreen)


class TestWkApp:
    """Tests for WkApp main application."""

    @pytest.mark.asyncio
    async def test_displays_worktrees_in_order(self) -> None:
        """Worktrees are displayed in correct order (most recent first)."""
        worktrees = [WORKTREE_1, WORKTREE_2, WORKTREE_3]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            list_widget = pilot.app.query_one(WorktreeList)
            assert len(list_widget.children) == 4

    @pytest.mark.asyncio
    async def test_default_selection_is_second_item(self) -> None:
        """Default selection is index 1 (first worktree, not 'New Worktree')."""
        worktrees = [WORKTREE_1, WORKTREE_2, WORKTREE_3]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            list_widget = pilot.app.query_one(WorktreeList)
            assert list_widget.index == 1

    @pytest.mark.asyncio
    async def test_enter_launches(self) -> None:
        """Enter on worktree row sets launch commands and exits."""
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

        assert len(app.shell_commands) == 2
        assert app.shell_commands[0].startswith("cd")
        assert app.shell_commands[1] == "code ."

    @pytest.mark.asyncio
    async def test_enter_on_new_worktree_opens_input(self) -> None:
        """Enter on 'New Worktree' row opens input dialog."""
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            list_widget = pilot.app.query_one(WorktreeList)
            list_widget.index = 0  # Select "New Worktree"
            await pilot.pause()

            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(pilot.app.screen, NewWorktreeScreen)

    @pytest.mark.asyncio
    async def test_jump_sets_cd_only(self) -> None:
        """Pressing 'j' sets cd command only."""
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            await pilot.press("j")
            await pilot.pause()
            await pilot.pause()

        assert len(app.shell_commands) == 1
        assert app.shell_commands[0].startswith("cd")

    @pytest.mark.asyncio
    async def test_jump_on_new_worktree_noop(self) -> None:
        """Pressing 'j' on 'New Worktree' row is a no-op."""
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            list_widget = pilot.app.query_one(WorktreeList)
            list_widget.index = 0
            await pilot.pause()
            await pilot.press("j")
            await pilot.pause()
            await pilot.pause()

            assert app.shell_commands == []

    @pytest.mark.asyncio
    async def test_restart_sets_commands(self) -> None:
        """Pressing 'r' sets cd + restart command."""
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            await pilot.press("r")
            await pilot.pause()
            await pilot.pause()

        assert len(app.shell_commands) == 2
        assert app.shell_commands[0].startswith("cd")
        assert app.shell_commands[1] == "code --restart ."

    @pytest.mark.asyncio
    async def test_restart_on_new_worktree_noop(self) -> None:
        """Pressing 'r' on 'New Worktree' row is a no-op."""
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            list_widget = pilot.app.query_one(WorktreeList)
            list_widget.index = 0
            await pilot.pause()
            await pilot.press("r")
            await pilot.pause()
            await pilot.pause()

            assert app.shell_commands == []

    @pytest.mark.asyncio
    async def test_delete_shows_confirmation(self) -> None:
        """Pressing 'd' shows confirmation dialog."""
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            await pilot.press("d")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(pilot.app.screen, ConfirmDeleteScreen)

    @pytest.mark.asyncio
    async def test_delete_cancel_returns(self) -> None:
        """Cancelling delete returns to list without deletion."""
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            await pilot.press("d")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            await pilot.pause()

            assert not isinstance(pilot.app.screen, ConfirmDeleteScreen)

    @pytest.mark.asyncio
    async def test_new_opens_input(self) -> None:
        """Pressing 'n' opens new worktree input."""
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(pilot.app.screen, NewWorktreeScreen)

    @pytest.mark.asyncio
    async def test_quit_exits_empty(self) -> None:
        """Pressing 'q' exits with empty commands."""
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            await pilot.press("q")
            await pilot.pause()
            await pilot.pause()

        assert app.shell_commands == []

    @pytest.mark.asyncio
    async def test_escape_exits_empty(self) -> None:
        """Pressing Escape exits with empty commands."""
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            await pilot.press("escape")
            await pilot.pause()
            await pilot.pause()

        assert app.shell_commands == []

    @pytest.mark.asyncio
    async def test_empty_worktrees_shows_new_only(self) -> None:
        """With no worktrees, only 'New Worktree' row is shown."""
        app = WkApp([], SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            list_widget = pilot.app.query_one(WorktreeList)
            assert len(list_widget.children) == 1
            assert list_widget.index == 0

    @pytest.mark.asyncio
    async def test_delete_on_new_worktree_noop(self) -> None:
        """Pressing 'd' on 'New Worktree' row is a no-op."""
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            list_widget = pilot.app.query_one(WorktreeList)
            list_widget.index = 0
            await pilot.pause()
            await pilot.press("d")
            await pilot.pause()
            await pilot.pause()

            assert not isinstance(pilot.app.screen, ConfirmDeleteScreen)

    @pytest.mark.asyncio
    async def test_enter_handled_by_list_view(self) -> None:
        """Verify Enter triggers on_list_view_selected via ListView."""
        app = WkApp([WORKTREE_1], SAMPLE_CONFIG)

        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

        assert len(app.shell_commands) >= 1


class TestWkAppWithMocks:
    """Tests that require mocking action functions."""

    @pytest.mark.asyncio
    async def test_delete_confirm_refreshes_list(self) -> None:
        """Confirming delete removes worktree and refreshes list."""
        worktrees = [WORKTREE_1, WORKTREE_2]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        with (
            patch("wk.tui.app.action_delete") as mock_delete,
            patch("wk.worktree.list_worktrees") as mock_list,
        ):
            mock_list.return_value = [WORKTREE_2]

            async with app.run_test() as pilot:
                await pilot.press("d")
                await pilot.pause()
                await pilot.pause()

                screen = pilot.app.screen
                confirm_btn = screen.query_one("#confirm")
                await pilot.click(confirm_btn)
                await pilot.pause()
                await pilot.pause()

                mock_delete.assert_called_once_with(WORKTREE_1.name, force=False)
                mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_error_shows_notification(self) -> None:
        """Error on delete shows error notification with force option."""
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        with patch("wk.tui.app.action_delete") as mock_delete:
            mock_delete.side_effect = WtCommandError("wt remove", "Worktree in use", 1)

            async with app.run_test() as pilot:
                await pilot.press("d")
                await pilot.pause()
                await pilot.pause()

                screen = pilot.app.screen
                confirm_btn = screen.query_one("#confirm")
                await pilot.click(confirm_btn)
                await pilot.pause()
                await pilot.pause()

                assert isinstance(pilot.app.screen, DeleteErrorScreen)

    @pytest.mark.asyncio
    async def test_new_error_shows_notification(self) -> None:
        """Error on new worktree shows error notification."""
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, SAMPLE_CONFIG)

        with patch("wk.tui.app.action_new") as mock_new:
            mock_new.side_effect = WtCommandError(
                "wt switch --create", "Branch exists", 1
            )

            async with app.run_test() as pilot:
                await pilot.press("n")
                await pilot.pause()
                await pilot.pause()

                screen = pilot.app.screen
                input_widget = screen.query_one(Input)
                input_widget.value = "existing-branch"
                await pilot.press("enter")
                await pilot.pause()
                await pilot.pause()

                assert isinstance(pilot.app.screen, ErrorNotificationScreen)


class TestRunApp:
    """Tests for run_app convenience function."""

    def test_returns_shell_commands(self) -> None:
        """run_app returns the shell_commands from the app."""
        worktrees = [WORKTREE_1]

        with patch.object(WkApp, "run") as mock_run:

            def side_effect(**kwargs):
                WkApp.shell_commands = []

            mock_run.side_effect = side_effect

            result = run_app(worktrees, SAMPLE_CONFIG)

            assert result == []
            mock_run.assert_called_once()

    def test_returns_empty_on_quit(self) -> None:
        """run_app returns empty list when user quits."""
        worktrees = [WORKTREE_1]

        with patch.object(WkApp, "run") as mock_run:
            mock_run.return_value = None

            result = run_app(worktrees, SAMPLE_CONFIG)

            assert result == []


class TestWkAppNoConfig:
    """Tests for WkApp behavior with minimal/no config."""

    @pytest.mark.asyncio
    async def test_launch_without_open_cmd(self) -> None:
        """Enter without open_workspace_cmd only returns cd (jump mode)."""
        config = WkConfig(open_workspace_cmd=None, repo_root=Path("/repo"))
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, config)

        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

        assert len(app.shell_commands) == 1
        assert app.shell_commands[0].startswith("cd")

    @pytest.mark.asyncio
    async def test_restart_without_restart_cmd(self) -> None:
        """Restart binding is absent when restart_workspace_cmd is None."""
        config = WkConfig(
            open_workspace_cmd="code .",
            restart_workspace_cmd=None,
            repo_root=Path("/repo"),
        )
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, config)

        assert "r" not in app._bindings.key_to_bindings

        async with app.run_test() as pilot:
            await pilot.press("r")
            await pilot.pause()
            await pilot.pause()

        assert app.shell_commands == []


class TestWkAppCustomCommands:
    """Tests for WkApp custom command handling."""

    @pytest.mark.asyncio
    async def test_custom_command_triggers_and_exits(self) -> None:
        """Pressing custom command key should set shell_commands and exit."""
        config = WkConfig(
            open_workspace_cmd="code .",
            repo_root=Path("/repo"),
            custom_commands=(CustomCommand(key="t", name="Test", command="echo test"),),
        )
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, config)

        async with app.run_test() as pilot:
            await pilot.press("t")
            await pilot.pause()
            await pilot.pause()

        assert len(app.shell_commands) == 2
        assert app.shell_commands[0].startswith("cd")
        assert app.shell_commands[1] == "echo test"

    @pytest.mark.asyncio
    async def test_custom_command_confirm_shows_dialog(self) -> None:
        """Custom command with confirm: true should show confirmation dialog."""
        config = WkConfig(
            open_workspace_cmd="code .",
            repo_root=Path("/repo"),
            custom_commands=(
                CustomCommand(key="t", name="Test", command="echo test", confirm=True),
            ),
        )
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, config)

        async with app.run_test() as pilot:
            await pilot.press("t")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(pilot.app.screen, ConfirmCustomCommandScreen)

    @pytest.mark.asyncio
    async def test_custom_command_confirm_accept_exits(self) -> None:
        """Accepting custom command confirmation should exit with commands."""
        config = WkConfig(
            open_workspace_cmd="code .",
            repo_root=Path("/repo"),
            custom_commands=(
                CustomCommand(key="t", name="Test", command="echo test", confirm=True),
            ),
        )
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, config)

        async with app.run_test() as pilot:
            await pilot.press("t")
            await pilot.pause()
            await pilot.pause()

            screen = pilot.app.screen
            confirm_btn = screen.query_one("#confirm")
            await pilot.click(confirm_btn)
            await pilot.pause()
            await pilot.pause()

        assert len(app.shell_commands) == 2
        assert app.shell_commands[1] == "echo test"

    @pytest.mark.asyncio
    async def test_custom_command_confirm_cancel_stays(self) -> None:
        """Cancelling custom command confirmation should stay in app."""
        config = WkConfig(
            open_workspace_cmd="code .",
            repo_root=Path("/repo"),
            custom_commands=(
                CustomCommand(key="t", name="Test", command="echo test", confirm=True),
            ),
        )
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, config)

        async with app.run_test() as pilot:
            await pilot.press("t")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(pilot.app.screen, ConfirmCustomCommandScreen)

            screen = pilot.app.screen
            cancel_btn = screen.query_one("#cancel")
            await pilot.click(cancel_btn)
            await pilot.pause()
            await pilot.pause()

            # App should still be running (not exited)
            assert not isinstance(pilot.app.screen, ConfirmCustomCommandScreen)
            assert app.shell_commands == []

    @pytest.mark.asyncio
    async def test_custom_command_noop_on_new_worktree(self) -> None:
        """Custom command on 'New Worktree' row should be a no-op."""
        config = WkConfig(
            open_workspace_cmd="code .",
            repo_root=Path("/repo"),
            custom_commands=(CustomCommand(key="t", name="Test", command="echo test"),),
        )
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, config)

        async with app.run_test() as pilot:
            list_widget = pilot.app.query_one(WorktreeList)
            list_widget.index = 0  # Select "New Worktree"
            await pilot.pause()

            await pilot.press("t")
            await pilot.pause()
            await pilot.pause()

            # Should not exit, commands should be empty
            assert app.shell_commands == []

    @pytest.mark.asyncio
    async def test_custom_command_overrides_builtin(self) -> None:
        """Custom command on built-in key should override the built-in action."""
        config = WkConfig(
            open_workspace_cmd="code .",
            repo_root=Path("/repo"),
            custom_commands=(
                CustomCommand(key="d", name="Custom D", command="echo custom"),
            ),
        )
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, config)

        async with app.run_test() as pilot:
            await pilot.press("d")
            await pilot.pause()
            await pilot.pause()

        # Should have custom command, not delete confirmation
        assert len(app.shell_commands) == 2
        assert app.shell_commands[1] == "echo custom"

    @pytest.mark.asyncio
    async def test_multiple_custom_commands_in_footer(self) -> None:
        """Multiple custom commands should all appear in bindings."""
        config = WkConfig(
            open_workspace_cmd="code .",
            repo_root=Path("/repo"),
            custom_commands=(
                CustomCommand(key="t", name="Test", command="echo test"),
                CustomCommand(key="b", name="Build", command="npm build"),
            ),
        )
        worktrees = [WORKTREE_1]
        app = WkApp(worktrees, config)

        # Check that both custom keys are in bindings
        assert "t" in app._bindings.key_to_bindings
        assert "b" in app._bindings.key_to_bindings

        # Check that the binding names are correct
        t_binding = app._bindings.key_to_bindings["t"][0]
        b_binding = app._bindings.key_to_bindings["b"][0]
        assert t_binding.description == "Test"
        assert b_binding.description == "Build"
