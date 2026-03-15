"""Textual application for wk TUI."""

from textual.app import App, Binding
from textual.binding import BindingsMap
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, ListView

from wk.actions import (
    action_delete,
    action_jump,
    action_launch,
    action_new,
    action_restart,
)
from wk.config import WkConfig
from wk.tui.theme import APP_CSS
from wk.tui.worktree_list import WorktreeList
from wk.worktree import Worktree, WtCommandError


class NewWorktreeScreen(ModalScreen[str | None]):
    """Modal screen for entering a new worktree name.

    Returns the entered name on submit, or None on cancel.
    """

    DEFAULT_CSS = """
    NewWorktreeScreen {
        align: center middle;
    }

    NewWorktreeScreen > Vertical {
        width: 50;
        height: auto;
        background: $background;
        border: thick $accent;
        padding: 1 2;
    }

    NewWorktreeScreen Label {
        margin-bottom: 1;
    }

    NewWorktreeScreen Input {
        width: 100%;
        margin-bottom: 1;
    }

    NewWorktreeScreen Button {
        width: 100%;
    }
    """

    def compose(self):
        with Vertical():
            yield Label("New Worktree Name:")
            yield Input(placeholder="feature/my-branch")
            yield Button("Create", variant="primary")

    def on_mount(self) -> None:
        """Focus the input on mount."""
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        self.dismiss(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle create button."""
        input_widget = self.query_one(Input)
        if input_widget.value:
            self.dismiss(input_widget.value)

    def on_key(self, event) -> None:
        """Handle escape key to cancel."""
        if event.key == "escape":
            event.stop()
            self.dismiss(None)


class ConfirmDeleteScreen(ModalScreen[bool]):
    """Modal screen for confirming worktree deletion.

    Returns True on confirm, False on cancel.
    """

    DEFAULT_CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }

    ConfirmDeleteScreen > Vertical {
        width: 50;
        height: auto;
        background: $background;
        border: thick $error;
        padding: 1 2;
    }

    ConfirmDeleteScreen Label {
        margin-bottom: 1;
    }

    ConfirmDeleteScreen .buttons {
        layout: horizontal;
        width: 100%;
        height: auto;
    }

    ConfirmDeleteScreen Button {
        width: 1fr;
        margin: 0 1;
    }
    """

    def __init__(self, worktree_name: str) -> None:
        super().__init__()
        self._worktree_name = worktree_name

    def compose(self):
        with Vertical():
            yield Label(f"Delete worktree '{self._worktree_name}'?")
            with Vertical(classes="buttons"):
                yield Button("Delete", variant="error", id="confirm")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_key(self, event) -> None:
        """Handle escape key to cancel."""
        if event.key == "escape":
            event.stop()
            self.dismiss(False)


class ErrorNotificationScreen(ModalScreen[None]):
    """Modal screen for displaying error messages.

    Dismisses on any key press or button click.
    """

    DEFAULT_CSS = """
    ErrorNotificationScreen {
        align: center middle;
    }

    ErrorNotificationScreen > Vertical {
        width: 60;
        height: auto;
        background: $background;
        border: thick $error;
        padding: 1 2;
    }

    ErrorNotificationScreen Label {
        margin-bottom: 1;
        color: $error;
    }

    ErrorNotificationScreen Button {
        width: 100%;
    }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self):
        with Vertical():
            yield Label(self._message)
            yield Button("OK", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle OK button."""
        self.dismiss(None)

    def on_key(self, event) -> None:
        """Handle any key to dismiss."""
        event.stop()
        self.dismiss(None)


class DeleteErrorScreen(ModalScreen[bool]):
    """Modal screen for delete errors with force option.

    Returns True to force delete, False to cancel.
    """

    DEFAULT_CSS = """
    DeleteErrorScreen {
        align: center middle;
    }

    DeleteErrorScreen > Vertical {
        width: 60;
        height: auto;
        background: $background;
        border: thick $error;
        padding: 1 2;
    }

    DeleteErrorScreen Label {
        margin-bottom: 1;
        color: $error;
    }

    DeleteErrorScreen .buttons {
        layout: horizontal;
        width: 100%;
        height: auto;
    }

    DeleteErrorScreen Button {
        width: 1fr;
        margin: 0 1;
    }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self):
        with Vertical():
            yield Label(self._message)
            with Vertical(classes="buttons"):
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("Force Delete", variant="error", id="force")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        self.dismiss(event.button.id == "force")

    def on_key(self, event) -> None:
        """Handle escape key to cancel."""
        if event.key == "escape":
            event.stop()
            self.dismiss(False)


class WkApp(App):
    """Main wk TUI application.

    Args:
        worktrees: List of Worktree objects to display.
        config: WkConfig for workspace launching.

    After the app exits, check `shell_commands` for commands to eval.
    """

    CSS = APP_CSS

    shell_commands: list[str]

    def __init__(self, worktrees: list[Worktree], config: WkConfig) -> None:
        super().__init__()
        self._worktrees = worktrees
        self._config = config
        self.shell_commands = []

        bindings = [
            Binding("q", "quit", "Quit"),
            Binding("escape", "quit", "Quit", show=False),
            Binding("j", "jump", "Jump", show=False),
            Binding("d", "delete", "Delete"),
            Binding("n", "new", "New"),
        ]
        if config.open_workspace_cmd:
            bindings.append(Binding("l", "launch", "Launch"))
        if config.restart_workspace_cmd:
            bindings.append(Binding("r", "restart", "Restart"))

        self._bindings = BindingsMap(bindings)

    def compose(self):
        """Build the main screen layout."""
        yield Header()
        yield WorktreeList(self._worktrees)
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle Enter key on the worktree list."""
        worktree = self.query_one(WorktreeList).selected_worktree
        if worktree is None:
            self._show_new_input()
        elif self._config.open_workspace_cmd:
            self.shell_commands = action_launch(worktree, self._config)
            self.exit()
        else:
            self.shell_commands = action_jump(worktree)
            self.exit()

    def action_launch(self) -> None:
        """Launch selected worktree (l) - always runs open_workspace_cmd."""
        list_widget = self.query_one(WorktreeList)
        worktree = list_widget.selected_worktree
        if worktree is not None:
            self.shell_commands = action_launch(worktree, self._config)
            self.exit()

    def action_jump(self) -> None:
        """Jump to selected worktree (j)."""
        list_widget = self.query_one(WorktreeList)
        worktree = list_widget.selected_worktree
        if worktree is not None:
            self.shell_commands = action_jump(worktree)
            self.exit()

    def action_restart(self) -> None:
        """Restart selected worktree (r)."""
        list_widget = self.query_one(WorktreeList)
        worktree = list_widget.selected_worktree
        if worktree is not None:
            self.shell_commands = action_restart(worktree, self._config)
            self.exit()

    def action_delete(self) -> None:
        """Delete selected worktree (d)."""
        list_widget = self.query_one(WorktreeList)
        worktree = list_widget.selected_worktree
        if worktree is not None:
            self._show_delete_confirm(worktree)

    def action_new(self) -> None:
        """Create new worktree (n)."""
        self._show_new_input()

    async def action_quit(self) -> None:
        """Exit with empty commands."""
        self.shell_commands = []
        self.exit()

    def _show_new_input(self) -> None:
        """Show the new worktree input dialog."""
        self.push_screen(NewWorktreeScreen(), self._handle_new_result)

    def _handle_new_result(self, name: str | None) -> None:
        """Handle result from new worktree input."""
        if name is None:
            return  # Cancelled

        try:
            self.shell_commands = action_new(name, self._config)
            self.exit()
        except WtCommandError as e:
            self._show_error(f"Failed to create worktree: {e.stderr.strip()}")

    def _show_delete_confirm(self, worktree: Worktree) -> None:
        """Show delete confirmation dialog."""
        self.push_screen(ConfirmDeleteScreen(worktree.name), self._handle_delete_result)

    def _handle_delete_result(
        self, confirmed: bool | None, force: bool = False
    ) -> None:
        """Handle result from delete confirmation.

        Args:
            confirmed: True if user confirmed, False/None if cancelled.
            force: If True, use --force flag for deletion.
        """
        if not confirmed:
            return  # Cancelled

        list_widget = self.query_one(WorktreeList)
        worktree = list_widget.selected_worktree
        if worktree is None:
            return

        try:
            action_delete(worktree.name, force=force)
            # Refresh the list by re-fetching worktrees
            from wk.worktree import list_worktrees

            self._worktrees = list_worktrees()
            # Defer DOM manipulation to avoid hanging inside push_screen callback
            self.call_later(self._refresh_worktree_list)
        except WtCommandError as e:
            self._show_delete_error(worktree.name, e.stderr.strip())

    def _show_delete_error(self, worktree_name: str, error_msg: str) -> None:
        """Show delete error with force option."""
        self._pending_delete_name = worktree_name
        self.push_screen(
            DeleteErrorScreen(f"Failed to delete: {error_msg}"),
            self._handle_force_delete_result,
        )

    def _handle_force_delete_result(self, force: bool | None) -> None:
        """Handle result from delete error screen (force or cancel)."""
        if not force:
            return  # Cancelled

        list_widget = self.query_one(WorktreeList)
        worktree = list_widget.selected_worktree
        if worktree is None:
            return

        try:
            action_delete(worktree.name, force=True)
            # Refresh the list by re-fetching worktrees
            from wk.worktree import list_worktrees

            self._worktrees = list_worktrees()
            self.call_later(self._refresh_worktree_list)
        except WtCommandError as e:
            # Force also failed, show generic error
            self._show_error(f"Force delete failed: {e.stderr.strip()}")

    def _refresh_worktree_list(self) -> None:
        """Replace the worktree list widget with a fresh one."""
        list_widget = self.query_one(WorktreeList)
        list_widget.remove()
        self.mount(WorktreeList(self._worktrees), after=0)

    def _show_error(self, message: str) -> None:
        """Show an error notification."""
        self.push_screen(ErrorNotificationScreen(message))


def run_app(worktrees: list[Worktree], config: WkConfig) -> list[str]:
    """Convenience function: create and run WkApp, return shell commands.

    Returns the shell_commands set by the app (empty list if user quit).
    Note: stdout redirection is handled at the CLI level.
    """
    app = WkApp(worktrees, config)
    app.run()
    return app.shell_commands
