"""Textual application for wk TUI."""

import random

from textual.app import App, Binding
from textual.binding import BindingsMap
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListView,
    LoadingIndicator,
    Static,
)
from textual.worker import Worker, WorkerState

from wk.actions import (
    action_custom_command,
    action_delete,
    action_jump,
    action_launch,
    action_new,
    action_restart,
)
from wk.config import CustomCommand, WkConfig
from wk.ipc import Selection, write_selection
from wk.status.advice import compute_advice
from wk.status.agent import detect_agent_state_for_session
from wk.status.ci import CIStatusCache
from wk.status.linear import LinearStatusCache
from wk.tui.theme import APP_CSS
from wk.tui.worktree_list import RowStatus, WorktreeList
from wk.worktree import Worktree, WtCommandError


class DialogMixin:
    """Mixin for dialogs with shared navigation and key handling."""

    def handle_escape(self, event) -> bool:
        """Handle escape key to close dialog.

        Returns True if the event was handled.
        """
        if event.key == "escape":
            event.stop()
            self.dismiss(None)  # type: ignore[attr-defined]
            return True
        return False

    def navigate_buttons(self, event) -> bool:
        """Handle left/right arrow key navigation between buttons.

        Returns True if the event was handled.
        """
        if event.key not in ("left", "right"):
            return False

        event.stop()
        buttons = list(self.query(Button))  # type: ignore[attr-defined]
        if len(buttons) < 2:
            return True

        focused = self.focused  # type: ignore[attr-defined]
        if focused not in buttons:
            buttons[0].focus()
            return True

        idx = buttons.index(focused)
        if event.key == "right":
            buttons[(idx + 1) % len(buttons)].focus()
        else:
            buttons[(idx - 1) % len(buttons)].focus()
        return True

    def handle_dialog_keys(self, event) -> None:
        """Handle escape and arrow navigation for dialogs."""
        if self.handle_escape(event):
            return
        self.navigate_buttons(event)


class LoadingScreen(ModalScreen[None]):
    """Modal screen showing a loading spinner during long operations."""

    DEFAULT_CSS = """
    LoadingScreen {
        align: center middle;
    }

    LoadingScreen > Vertical {
        width: auto;
        height: auto;
        background: $background;
        border: thick $accent;
        padding: 1 3;
    }

    LoadingScreen LoadingIndicator {
        width: 3;
        height: 1;
    }
    """

    def __init__(self, message: str = "Working...") -> None:
        super().__init__()
        self._message = message

    def compose(self):
        with Vertical():
            yield Label(self._message)
            yield LoadingIndicator()


class NewWorktreeScreen(ModalScreen[str | None], DialogMixin):
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
        """Handle escape key to cancel. No left right so text box still works."""
        self.handle_escape(event)


class ConfirmDeleteScreen(ModalScreen[bool], DialogMixin):
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

    def on_mount(self) -> None:
        """Focus the first button on mount."""
        buttons = list(self.query(Button))
        if buttons:
            buttons[0].focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_key(self, event) -> None:
        """Handle escape key and arrow navigation."""
        self.handle_dialog_keys(event)


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


class DeleteErrorScreen(ModalScreen[bool], DialogMixin):
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

    def on_mount(self) -> None:
        """Focus the first button on mount."""
        buttons = list(self.query(Button))
        if buttons:
            buttons[0].focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        self.dismiss(event.button.id == "force")

    def on_key(self, event) -> None:
        """Handle escape key and arrow navigation."""
        self.handle_dialog_keys(event)


class ConfirmCustomCommandScreen(ModalScreen[bool], DialogMixin):
    """Modal screen for confirming a custom command execution.

    Returns True on confirm, False on cancel.
    """

    DEFAULT_CSS = """
    ConfirmCustomCommandScreen {
        align: center middle;
    }

    ConfirmCustomCommandScreen > Vertical {
        width: 50;
        height: auto;
        background: $background;
        border: thick $accent;
        padding: 1 2;
    }

    ConfirmCustomCommandScreen Label {
        margin-bottom: 1;
    }

    ConfirmCustomCommandScreen .buttons {
        layout: horizontal;
        width: 100%;
        height: auto;
    }

    ConfirmCustomCommandScreen Button {
        width: 1fr;
        margin: 0 1;
    }
    """

    def __init__(self, command_name: str, worktree_name: str) -> None:
        super().__init__()
        self._command_name = command_name
        self._worktree_name = worktree_name

    def compose(self):
        with Vertical():
            yield Label(f"Run '{self._command_name}' on '{self._worktree_name}'?")
            with Vertical(classes="buttons"):
                yield Button("Run", variant="primary", id="confirm")
                yield Button("Cancel", variant="default", id="cancel")

    def on_mount(self) -> None:
        """Focus the first button on mount."""
        buttons = list(self.query(Button))
        if buttons:
            buttons[0].focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_key(self, event) -> None:
        """Handle escape key and arrow navigation."""
        self.handle_dialog_keys(event)


_WK_TITLES = [
    "wk it out",
    "wk through it",
    "Whistle while you wk",
    "wk in progress",
    "wk of art",
    "Nice wk if you can get it",
    "All in a day's wk",
    "wk hard, play hard",
    "wk smarter, not harder",
]


class WkApp(App):
    """Main wk TUI application.

    Args:
        worktrees: List of Worktree objects to display.
        config: WkConfig for workspace launching.

    After the app exits, check `shell_commands` for commands to eval.
    """

    CSS = APP_CSS

    shell_commands: list[str]
    _worktrees: list[Worktree]

    def __init__(
        self,
        worktrees: list[Worktree],
        config: WkConfig,
        persistent: bool = False,
    ) -> None:
        super().__init__()
        self.title = random.choice(_WK_TITLES)
        self._worktrees = worktrees
        self._config = config
        self._persistent = persistent
        self.shell_commands = []

        # Store custom commands for lookup
        self._custom_commands = {cmd.key: cmd for cmd in config.custom_commands}
        self._pending_custom_cmd: CustomCommand | None = None

        # Status caches (used in persistent mode)
        self._ci_cache = CIStatusCache(ttl=30.0)
        self._linear_cache = LinearStatusCache(ttl=60.0)

        # Per-worktree display state — written by individual workers,
        # combined into RowStatus by _rebuild_statuses()
        self._ci_display: dict[str, str] = {}
        self._linear_display: dict[str, str] = {}
        self._agent_display: dict[str, str] = {}

        bindings = [
            Binding("j", "jump", "Jump", show=False),
            Binding("d", "delete", "Delete"),
            Binding("n", "new", "New"),
        ]
        if not self._persistent:
            bindings.insert(0, Binding("q", "quit", "Quit"))
            bindings.insert(1, Binding("escape", "quit", "Quit", show=False))
            bindings.insert(2, Binding("slash", "filter", "Filter"))
            if config.open_workspace_cmd:
                bindings.append(Binding("l", "launch", "Launch"))
        if config.restart_workspace_cmd or self._persistent:
            bindings.append(Binding("r", "restart", "Restart"))
        if self._persistent:
            bindings.append(Binding("R", "refresh", "Refresh"))

        # Remove bindings that conflict with custom commands
        custom_keys = set(self._custom_commands.keys())
        bindings = [b for b in bindings if b.key not in custom_keys]

        # Add custom command bindings
        for cmd in config.custom_commands:
            bindings.append(Binding(cmd.key, f"custom_{cmd.key}", cmd.name))

        self._bindings = BindingsMap(bindings)

        # Create dynamic action handlers for custom commands
        for cmd in config.custom_commands:
            method_name = f"action_custom_{cmd.key}"
            setattr(self, method_name, self._make_custom_handler(cmd))

    def compose(self):
        """Build the main screen layout."""
        yield Header()
        yield Static("", id="filter-indicator")
        if self._persistent:
            header = (
                f"{'NAME':<20s} "
                f"{'STATUS':<8s} "
                f"{'CI':<2s} "
                f"{'ADVICE':<9s} "
                f"{'AGENT':<5s} "
                f"DATE"
            )
            yield Static(header, id="column-header")
        yield WorktreeList(self._worktrees)
        yield Footer()

    def on_mount(self) -> None:
        """Start periodic status refresh in persistent mode."""
        if self._persistent:
            # Write the initial selection so the workspace pane has something
            # to attach to without waiting for the user to move the cursor.
            # Textual's ListView.Highlighted only fires on cursor *change*,
            # not on initial mount, so we have to seed it ourselves.
            if self._worktrees:
                first = self._worktrees[0]
                write_selection(
                    self._config.repo_root,
                    Selection(
                        worktree_name=first.name,
                        worktree_path=str(first.path),
                    ),
                )

            self._refresh_statuses()
            self.set_interval(30, self._refresh_statuses)
            self.set_interval(5, self._refresh_agent_status)
            self.set_interval(30, self._refresh_worktree_list_worker)

    def _refresh_statuses(self) -> None:
        """Fetch CI status and update the worktree list columns."""
        self.run_worker(self._fetch_statuses, thread=True, name="status_refresh")

    def _fetch_statuses(self) -> dict[str, RowStatus]:
        """Background worker: fetch CI + Linear status data.

        Wrapped in try/except so transient network errors don't crash
        the TUI — Textual treats an unhandled worker exception as fatal.
        """
        try:
            ci_data = self._ci_cache.get(self._config.repo_root)

            wt_names = [wt.name for wt in self._worktrees]
            linear_data = self._linear_cache.get(wt_names, self._config.linear_api_key)

            statuses: dict[str, RowStatus] = {}
            for wt in self._worktrees:
                if wt.branch in ("main", "master"):
                    statuses[wt.name] = RowStatus(ci="", linear="")
                    continue
                ci = ci_data.get(wt.branch)
                linear = linear_data.get(wt.name)
                statuses[wt.name] = RowStatus(
                    ci=ci.display if ci else "—",
                    linear=linear.state_name if linear else "—",
                )
            return statuses
        except Exception:
            return {}

    def _refresh_agent_status(self) -> None:
        """Fetch agent status more frequently than CI/Linear."""
        self.run_worker(self._fetch_agent_statuses, thread=True, name="agent_refresh")

    def _refresh_worktree_list_worker(self) -> None:
        """Reload the worktree list from disk in a background thread."""
        self.run_worker(self._fetch_worktree_list, thread=True, name="list_refresh")

    def _fetch_worktree_list(self) -> list[Worktree] | None:
        """Background worker: reload worktrees via `wt list`."""
        from wk.worktree import list_worktrees

        try:
            return list_worktrees()
        except Exception:
            return None

    def _fetch_agent_statuses(self) -> dict[str, str]:
        """Background worker: fetch agent states for all worktrees."""
        try:
            agent_states: dict[str, str] = {}
            for wt in self._worktrees:
                if wt.branch in ("main", "master"):
                    continue
                from wk.layout import tmux_session_name

                session_name = tmux_session_name(wt.name)
                agent_states[wt.name] = detect_agent_state_for_session(session_name)
            return agent_states
        except Exception:
            return {}

    def _rebuild_statuses(self) -> None:
        """Combine per-field display dicts into RowStatus and push to UI."""
        list_widget = self.query_one(WorktreeList)
        ci_data = self._ci_cache._cache

        for wt in self._worktrees:
            ci_str = self._ci_display.get(wt.name, "—")
            linear_str = self._linear_display.get(wt.name, "—")
            agent_state = self._agent_display.get(wt.name, "")
            ci = ci_data.get(wt.branch)
            advice = (
                compute_advice(
                    ci,
                    agent_state,
                    linear_state=linear_str,
                )
                if agent_state
                else ""
            )
            list_widget._statuses[wt.name] = RowStatus(
                ci=ci_str,
                linear=linear_str,
                agent=agent_state,
                advice=advice,
            )
        list_widget.update_statuses(list_widget._statuses)

    def on_worktree_list_filter_changed(
        self, event: WorktreeList.FilterChanged
    ) -> None:
        """Update filter indicator when filter changes."""
        indicator = self.query_one("#filter-indicator", Static)
        if event.filtering:
            indicator.update(f"Filter: {event.filter_text}")
            indicator.add_class("visible")
        else:
            indicator.update("")
            indicator.remove_class("visible")

    def on_worktree_list_highlight_changed(
        self, event: WorktreeList.HighlightChanged
    ) -> None:
        """Write selection to IPC when highlight changes in persistent mode."""
        if self._persistent and event.worktree is not None:
            write_selection(
                self._config.repo_root,
                Selection(
                    worktree_name=event.worktree.name,
                    worktree_path=str(event.worktree.path),
                ),
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle Enter/click on the worktree list."""
        worktree = self.query_one(WorktreeList).selected_worktree
        if worktree is None:
            self._show_new_input()
        elif self._persistent:
            self._switch_to_worktree(worktree)
        elif self._config.open_workspace_cmd:
            self.shell_commands = action_launch(worktree, self._config)
            self.exit()
        else:
            self.shell_commands = action_jump(worktree)
            self.exit()

    def _switch_to_worktree(self, worktree: Worktree) -> None:
        """Switch the workspace pane to the given worktree."""
        write_selection(
            self._config.repo_root,
            Selection(
                worktree_name=worktree.name,
                worktree_path=str(worktree.path),
            ),
        )
        from wk.layout import _tmux

        _tmux("detach-client")

    def action_launch(self) -> None:
        """Launch selected worktree (l) - always runs open_workspace_cmd."""
        list_widget = self.query_one(WorktreeList)
        worktree = list_widget.selected_worktree
        if worktree is not None:
            if self._persistent:
                return  # No-op in persistent mode (right pane handles workspace)
            self.shell_commands = action_launch(worktree, self._config)
            self.exit()

    def action_jump(self) -> None:
        """Jump to selected worktree (j)."""
        list_widget = self.query_one(WorktreeList)
        worktree = list_widget.selected_worktree
        if worktree is not None:
            if self._persistent:
                return  # No-op in persistent mode
            self.shell_commands = action_jump(worktree)
            self.exit()

    def action_restart(self) -> None:
        """Restart selected worktree (r)."""
        list_widget = self.query_one(WorktreeList)
        worktree = list_widget.selected_worktree
        if worktree is not None:
            if self._persistent:
                from wk.layout import restart_tmux_session, tmux_session_name

                session_name = tmux_session_name(worktree.name)
                restart_tmux_session(session_name, worktree.path, self._config)
                return
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

    def action_filter(self) -> None:
        """Enter filter mode (/)."""
        list_widget = self.query_one(WorktreeList)
        list_widget.start_filter()

    def action_refresh(self) -> None:
        """Reload the worktree list from disk (R)."""
        self._refresh_worktree_list_worker()

    def _make_custom_handler(self, cmd: CustomCommand):
        """Create a handler function for a custom command."""

        def handler() -> None:
            self._run_custom_command(cmd)

        return handler

    def _run_custom_command(self, cmd: CustomCommand) -> None:
        """Execute a custom command on the selected worktree."""
        list_widget = self.query_one(WorktreeList)
        worktree = list_widget.selected_worktree
        if worktree is None:
            return  # No-op on "New Worktree" row

        if cmd.confirm:
            self._pending_custom_cmd = cmd
            self.push_screen(
                ConfirmCustomCommandScreen(cmd.name, worktree.name),
                self._handle_custom_confirm,
            )
        else:
            self.shell_commands = action_custom_command(worktree, cmd.command)
            self.exit()

    def _handle_custom_confirm(self, confirmed: bool | None) -> None:
        """Handle result from custom command confirmation dialog."""
        if not confirmed:
            return

        list_widget = self.query_one(WorktreeList)
        worktree = list_widget.selected_worktree
        if worktree is None:
            return

        cmd = self._pending_custom_cmd
        if cmd is None:
            return

        self.shell_commands = action_custom_command(worktree, cmd.command)
        self.exit()

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

        self._pending_new_name = name
        self.push_screen(LoadingScreen("Creating worktree..."))
        self.run_worker(self._do_create, thread=True, name="create")

    def _do_create(self) -> tuple[bool, list[str] | str]:
        """Execute worktree creation in background thread.

        Returns (success, commands_or_error).
        """
        try:
            commands = action_new(self._pending_new_name, self._config)
            return (True, commands)
        except WtCommandError as e:
            return (False, e.stderr.strip())

    async def _on_create_done(self, success: bool, data: list[str] | str) -> None:
        """Handle create worker completion on main thread."""
        # Only pop if we have more than just the base screen
        if len(self.screen_stack) > 1:
            self.pop_screen()  # Remove loading screen
        if success:
            if self._persistent:
                # Refresh the list instead of exiting
                await self._refresh_worktree_list_async()
            else:
                # On success, data is always list[str]
                self.shell_commands = data if isinstance(data, list) else []
                self.exit()
        else:
            # On error, data is the error message string
            self._show_error(f"Failed to create worktree: {data}")

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

        self._pending_delete_force = force
        self._pending_delete_worktree_name = worktree.name
        self.push_screen(LoadingScreen("Deleting worktree..."))
        self.run_worker(self._do_delete, thread=True, name="delete")

    def _do_delete(self) -> tuple[bool, str | None, list[Worktree] | None]:
        """Execute worktree deletion in background thread.

        Returns (success, error_message, updated_worktrees).
        """
        try:
            action_delete(
                self._pending_delete_worktree_name, force=self._pending_delete_force
            )
            from wk.worktree import list_worktrees

            return (True, None, list_worktrees())
        except WtCommandError as e:
            return (False, e.stderr.strip(), None)

    async def _on_delete_done(
        self, success: bool, error_msg: str | None, worktrees: list[Worktree] | None
    ) -> None:
        """Handle delete worker completion on main thread."""
        # Only pop if we have more than just the base screen
        if len(self.screen_stack) > 1:
            self.pop_screen()  # Remove loading screen
        if success:
            # worktrees is never None on success
            if worktrees is not None:
                self._worktrees = worktrees
                await self._refresh_worktree_list()
        else:
            # error_msg is never None on failure
            self._show_delete_error(
                self._pending_delete_worktree_name, error_msg or "Unknown error"
            )

    def _show_delete_error(self, worktree_name: str, error_msg: str) -> None:
        """Show delete error with force option."""
        self.push_screen(
            DeleteErrorScreen(f"Failed to delete: {error_msg}"),
            self._handle_force_delete_result,
        )

    def _handle_force_delete_result(self, force: bool | None) -> None:
        """Handle result from delete error screen (force or cancel)."""
        if not force:
            return  # Cancelled

        self.push_screen(LoadingScreen("Force deleting worktree..."))
        self.run_worker(self._do_force_delete, thread=True, name="force_delete")

    def _do_force_delete(self) -> tuple[bool, str | None, list[Worktree] | None]:
        """Execute force delete in background thread.

        Returns (success, error_message, updated_worktrees).
        """
        try:
            action_delete(self._pending_delete_worktree_name, force=True)
            from wk.worktree import list_worktrees

            return (True, None, list_worktrees())
        except WtCommandError as e:
            return (False, e.stderr.strip(), None)

    async def _on_force_delete_done(
        self, success: bool, error_msg: str | None, worktrees: list[Worktree] | None
    ) -> None:
        """Handle force delete worker completion on main thread."""
        # Only pop if we have more than just the base screen
        if len(self.screen_stack) > 1:
            self.pop_screen()  # Remove loading screen
        if success:
            # worktrees is never None on success
            if worktrees is not None:
                self._worktrees = worktrees
                await self._refresh_worktree_list()
        else:
            self._show_error(f"Force delete failed: {error_msg or 'Unknown error'}")

    async def _refresh_worktree_list(self) -> None:
        """Refresh the worktree list in place."""
        list_widget = self.query_one(WorktreeList)
        list_widget._all_worktrees = self._worktrees
        await list_widget._refresh_list(select_first=False)

    async def _refresh_worktree_list_async(self) -> None:
        """Reload worktrees from disk and refresh the list."""
        from wk.worktree import list_worktrees

        self._worktrees = list_worktrees()
        await self._refresh_worktree_list()

    def _show_error(self, message: str) -> None:
        """Show an error notification."""
        self.push_screen(ErrorNotificationScreen(message))

    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        worker = event.worker
        if worker.state != WorkerState.SUCCESS:
            return  # Only handle successful completion

        result = worker.result
        if result is None:
            return  # Should not happen for our workers

        if worker.name == "create" and isinstance(result, tuple):
            success, data = result
            await self._on_create_done(success, data)
        elif worker.name == "delete" and isinstance(result, tuple):
            success, error_msg, worktrees = result
            await self._on_delete_done(success, error_msg, worktrees)
        elif worker.name == "force_delete" and isinstance(result, tuple):
            success, error_msg, worktrees = result
            await self._on_force_delete_done(success, error_msg, worktrees)
        elif worker.name == "status_refresh" and isinstance(result, dict):
            # Store CI/Linear display strings, then rebuild all rows
            for name, new in result.items():
                self._ci_display[name] = new.ci
                self._linear_display[name] = new.linear
            self._rebuild_statuses()
        elif worker.name == "agent_refresh" and isinstance(result, dict):
            # Store agent states, then rebuild all rows
            for name, state in result.items():
                self._agent_display[name] = state
            self._rebuild_statuses()
        elif worker.name == "list_refresh" and isinstance(result, list):
            await self._on_list_refresh_done(result)

    async def _on_list_refresh_done(self, new_list: list[Worktree]) -> None:
        """Reconcile a freshly-fetched worktree list with the current UI."""
        old_keys = {(w.name, str(w.path)) for w in self._worktrees}
        new_keys = {(w.name, str(w.path)) for w in new_list}
        if old_keys == new_keys:
            return
        self._worktrees = new_list
        await self._refresh_worktree_list()
        # Set of worktrees changed — kick fresh status fetches so newly
        # added entries don't sit on stale "—" placeholders for 30s.
        self._refresh_statuses()
        self._refresh_agent_status()


def run_app(
    worktrees: list[Worktree],
    config: WkConfig,
    persistent: bool = False,
) -> list[str]:
    """Convenience function: create and run WkApp, return shell commands.

    Args:
        worktrees: List of worktrees to display.
        config: WkConfig for workspace launching.
        persistent: If True, run in persistent mode (no exit on select).

    Returns the shell_commands set by the app (empty list if user quit).
    Note: stdout redirection is handled at the CLI level.
    """
    app = WkApp(worktrees, config, persistent=persistent)
    app.run()
    return app.shell_commands
