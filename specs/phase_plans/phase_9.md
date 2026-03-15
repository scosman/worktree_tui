# Phase 9: Custom Commands

**Overview**: Add support for user-defined custom commands in the config file. Custom commands are keybindings that run arbitrary shell commands in the selected worktree's directory. This touches three layers: config parsing, action logic, and TUI binding/dispatch.

**Spec files**: `specs/components/config.md`, `specs/components/actions.md`, `specs/components/tui_app.md`

## Steps

### Step 1: Add `CustomCommand` dataclass to `config.py`

File: `src/wk/config.py`

Add a new frozen dataclass before `WkConfig`:

```python
@dataclass(frozen=True)
class CustomCommand:
    """A user-defined custom command bound to a key."""
    key: str
    name: str
    command: str
    confirm: bool = False
```

Update `WkConfig` to include custom commands:

```python
@dataclass(frozen=True)
class WkConfig:
    open_workspace_cmd: str | None = None
    restart_workspace_cmd: str | None = None
    custom_commands: tuple[CustomCommand, ...] = ()
    repo_root: Path = field(default_factory=lambda: Path("."))
```

Use a `tuple` (not `list`) since `WkConfig` is frozen/immutable.

### Step 2: Parse `custom_commands` in `load_config()`

File: `src/wk/config.py`

After extracting `open_cmd` and `restart_cmd` from the YAML data dict, parse the `custom_commands` key:

```python
custom_cmds_raw = data.get("custom_commands", {})
custom_commands = _parse_custom_commands(custom_cmds_raw)
```

Implement `_parse_custom_commands(raw) -> tuple[CustomCommand, ...]`:

1. If `raw` is falsy (None, empty), return `()`.
2. Validate `raw` is a `dict`. If not, raise `ConfigError`.
3. For each `key, entry` in `raw.items()`:
   - Validate `key` is a single character (`len(key) == 1`). Raise `ConfigError` if not.
   - Validate `entry` is a `dict`. Raise `ConfigError` if not.
   - Extract `name = entry.get("name")` — required, must be `str`. Raise `ConfigError` if missing or wrong type.
   - Extract `command = entry.get("command")` — required, must be `str`. Raise `ConfigError` if missing or wrong type.
   - Extract `confirm = entry.get("confirm", False)` — optional, must be `bool`. Raise `ConfigError` if wrong type.
   - Ignore unknown keys in the entry.
   - Create `CustomCommand(key=key, name=name, command=command, confirm=confirm)`.
4. Return tuple of all parsed commands.

Error messages should be descriptive, e.g.:
- `"custom_commands: key 'ab' must be a single character"`
- `"custom_commands['t']: missing required field 'name'"`
- `"custom_commands['t']: 'command' must be a string"`

Pass `custom_commands` to the `WkConfig` constructor.

### Step 3: Add `action_custom_command()` to `actions.py`

File: `src/wk/actions.py`

Add a new function:

```python
def action_custom_command(worktree: Worktree, command: str) -> list[str]:
    """Build shell commands to run a custom command in a worktree directory.

    Always cd's into the worktree first, then runs the command.

    Returns:
        - ["cd <path>", "<command>"]
    """
    cd_cmd = f"cd {shlex.quote(str(worktree.path))}"
    return [cd_cmd, command]
```

This follows the same pattern as `action_launch` and `action_restart`. The `command` string is passed through as-is (not shell-quoted) — it is a user-authored shell command.

### Step 4: Add dynamic bindings in `WkApp.__init__`

File: `src/wk/tui/app.py`

Update the `__init__` method to incorporate custom commands:

1. Build the list of built-in bindings as today.
2. For each `CustomCommand` in `config.custom_commands`:
   - Remove any existing binding with the same key from the list (this implements override).
   - Append `Binding(cmd.key, f"custom_{cmd.key}", cmd.name)`.
3. Store `config.custom_commands` for later lookup: `self._custom_commands = {cmd.key: cmd for cmd in config.custom_commands}`.
4. Set `self._bindings = BindingsMap(bindings)` as before.

The override logic: filter the bindings list to remove any entry whose key matches a custom command key before appending the custom binding.

```python
custom_keys = {cmd.key for cmd in config.custom_commands}
bindings = [b for b in bindings if b.key not in custom_keys]
for cmd in config.custom_commands:
    bindings.append(Binding(cmd.key, f"custom_{cmd.key}", cmd.name))
```

### Step 5: Add dynamic action dispatch

File: `src/wk/tui/app.py`

Textual resolves `Binding(key, "custom_t", ...)` by calling `self.action_custom_t()`. Since these action names are dynamic, override Textual's `action` dispatch.

Option A — override `_action`:  not recommended, it's internal API.

Option B — generate methods dynamically in `__init__`:

```python
for cmd in config.custom_commands:
    method_name = f"action_custom_{cmd.key}"
    setattr(self, method_name, self._make_custom_handler(cmd))

def _make_custom_handler(self, cmd: CustomCommand):
    def handler() -> None:
        self._run_custom_command(cmd)
    return handler
```

Implement `_run_custom_command(cmd: CustomCommand)`:

```python
def _run_custom_command(self, cmd: CustomCommand) -> None:
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
```

### Step 6: Add confirmation dialog for custom commands

File: `src/wk/tui/app.py`

Add a new modal screen (similar to `ConfirmDeleteScreen`):

```python
class ConfirmCustomCommandScreen(ButtonNavigationMixin, ModalScreen[bool]):
    """Modal screen for confirming a custom command execution."""

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
    # ... on_mount, on_button_pressed, on_key same pattern as ConfirmDeleteScreen
```

Add the callback:

```python
def _handle_custom_confirm(self, confirmed: bool | None) -> None:
    if not confirmed:
        return
    list_widget = self.query_one(WorktreeList)
    worktree = list_widget.selected_worktree
    if worktree is None:
        return
    cmd = self._pending_custom_cmd
    self.shell_commands = action_custom_command(worktree, cmd.command)
    self.exit()
```

Add import for `action_custom_command` at the top of the file.

### Step 7: Update imports

File: `src/wk/tui/app.py`

Add to the imports from `wk.actions`:
```python
from wk.actions import (
    action_custom_command,
    action_delete,
    action_jump,
    action_launch,
    action_new,
    action_restart,
)
```

Add to imports from `wk.config`:
```python
from wk.config import CustomCommand, WkConfig
```

## Tests

### File: `tests/test_config.py` (extend existing)

| # | Test Case | Details |
|---|-----------|---------|
| 1 | `test_custom_commands_parsed` | Config with two custom commands, assert `config.custom_commands` is a tuple of 2 `CustomCommand` objects with correct fields |
| 2 | `test_custom_commands_missing_name` | Entry without `name`, assert `ConfigError` with descriptive message |
| 3 | `test_custom_commands_missing_command` | Entry without `command`, assert `ConfigError` |
| 4 | `test_custom_commands_key_too_long` | Key `"ab"`, assert `ConfigError` mentioning single character |
| 5 | `test_custom_commands_confirm_default_false` | Entry without `confirm`, assert `cmd.confirm is False` |
| 6 | `test_custom_commands_confirm_true` | Entry with `confirm: true`, assert `cmd.confirm is True` |
| 7 | `test_custom_commands_absent_returns_empty` | Config without `custom_commands` key, assert `config.custom_commands == ()` |
| 8 | `test_custom_commands_ignores_unknown_fields` | Entry with extra field, no error, extra field ignored |
| 9 | `test_custom_commands_empty_map` | `custom_commands: {}`, assert `config.custom_commands == ()` |

### File: `tests/test_actions.py` (extend existing)

| # | Test Case | Details |
|---|-----------|---------|
| 1 | `test_action_custom_command_returns_cd_and_cmd` | Worktree + command string, assert `["cd <path>", "<command>"]` |
| 2 | `test_action_custom_command_quotes_path` | Path with spaces, assert cd is properly shell-quoted |

### File: `tests/test_tui_app.py` (extend existing)

| # | Test Case | Details |
|---|-----------|---------|
| 1 | `test_custom_command_triggers_and_exits` | Config with custom command `t`, press `t` on worktree row, assert `shell_commands` has cd + command |
| 2 | `test_custom_command_confirm_shows_dialog` | Config with `confirm: true` custom command, press key, assert confirmation dialog visible |
| 3 | `test_custom_command_confirm_accept_exits` | Press key, accept confirmation, assert `shell_commands` set |
| 4 | `test_custom_command_confirm_cancel_stays` | Press key, cancel confirmation, assert app still running |
| 5 | `test_custom_command_noop_on_new_worktree` | Navigate to "New Worktree", press custom key, assert no-op |
| 6 | `test_custom_command_overrides_builtin` | Config with custom command on key `d`, press `d`, assert custom command runs (not delete flow) |
| 7 | `test_multiple_custom_commands_in_footer` | Config with 2 custom commands, assert both names visible in footer bindings |

## Completion Criteria

- [x] `CustomCommand` dataclass in `config.py`
- [x] `load_config()` parses and validates `custom_commands` from YAML
- [x] `action_custom_command()` in `actions.py`
- [x] `WkApp` dynamically creates bindings for custom commands
- [x] Custom command keys override conflicting built-in bindings
- [x] Confirmation dialog shown when `confirm: true`
- [x] Custom commands are no-ops on "New Worktree" row
- [x] Custom command names appear in footer
- [x] All new tests pass
- [x] All existing tests still pass
- [x] `uv run ./checks.sh` passes (lint, format, types, tests)
