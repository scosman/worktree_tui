"""Tests for config.py."""

from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import pytest

from wk.config import ConfigError, CustomCommand, WkConfig, load_config


class TestWkConfig:
    """Tests for WkConfig dataclass."""

    def test_config_is_immutable(self) -> None:
        """WkConfig should be frozen/immutable."""
        config = WkConfig()
        with pytest.raises(FrozenInstanceError):
            config.open_workspace_cmd = "test"  # type: ignore[misc]

    def test_default_values(self) -> None:
        """WkConfig should have None defaults for commands."""
        config = WkConfig()
        assert config.open_workspace_cmd is None
        assert config.restart_workspace_cmd is None

    def test_custom_values(self) -> None:
        """WkConfig should accept custom values."""
        config = WkConfig(
            open_workspace_cmd=".config/wt/start.sh",
            restart_workspace_cmd=".config/wt/restart.sh",
            repo_root=Path("/some/path"),
        )
        assert config.open_workspace_cmd == ".config/wt/start.sh"
        assert config.restart_workspace_cmd == ".config/wt/restart.sh"
        assert config.repo_root == Path("/some/path")


class TestLoadConfig:
    """Tests for load_config function."""

    def test_valid_config_loads(self, tmp_path: Path) -> None:
        """Valid config file should load correctly."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text(
            "open_workspace_cmd: .config/wt/start.sh\n"
            "restart_workspace_cmd: .config/wt/restart.sh\n"
        )

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            config = load_config()

        assert config.open_workspace_cmd == ".config/wt/start.sh"
        assert config.restart_workspace_cmd == ".config/wt/restart.sh"
        assert config.repo_root == tmp_path

    def test_missing_config_returns_defaults(self, tmp_path: Path) -> None:
        """Missing config file should return defaults."""
        with patch("wk.config._find_repo_root", return_value=tmp_path):
            config = load_config()

        assert config.open_workspace_cmd is None
        assert config.restart_workspace_cmd is None
        assert config.repo_root == tmp_path

    def test_empty_config_returns_defaults(self, tmp_path: Path) -> None:
        """Empty config file should return defaults."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text("")

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            config = load_config()

        assert config.open_workspace_cmd is None
        assert config.restart_workspace_cmd is None

    def test_unknown_keys_ignored(self, tmp_path: Path) -> None:
        """Unknown keys in config should be silently ignored."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text(
            "open_workspace_cmd: start.sh\n"
            "unknown_key: ignored_value\n"
            "another_unknown: 123\n"
        )

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            config = load_config()

        assert config.open_workspace_cmd == "start.sh"
        assert config.restart_workspace_cmd is None

    def test_malformed_yaml_raises_config_error(self, tmp_path: Path) -> None:
        """Malformed YAML should raise ConfigError."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text("{{{invalid\n")

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            with pytest.raises(ConfigError, match="Malformed YAML"):
                load_config()

    def test_repo_root_set_correctly(self, tmp_path: Path) -> None:
        """repo_root should be set to the actual git root."""
        with patch("wk.config._find_repo_root", return_value=tmp_path):
            config = load_config()

        assert config.repo_root == tmp_path


class TestFindRepoRoot:
    """Tests for _find_repo_root function."""

    def test_not_in_git_repo_raises_config_error(self) -> None:
        """Not in a git repo should raise ConfigError."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 128
            mock_run.return_value.stderr = "fatal: not a git repository"

            with pytest.raises(ConfigError, match="Not in a git repository"):
                load_config()

    def test_git_root_found(self) -> None:
        """Should return the git root path when in a repo."""
        expected_path = Path("/path/to/repo")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "/path/to/repo\n"

            # Also need to mock that the config file doesn't exist
            with patch("pathlib.Path.exists", return_value=False):
                config = load_config()

        assert config.repo_root == expected_path


class TestCustomCommand:
    """Tests for CustomCommand dataclass."""

    def test_custom_command_is_immutable(self) -> None:
        """CustomCommand should be frozen/immutable."""
        cmd = CustomCommand(key="t", name="Test", command="echo test")
        with pytest.raises(FrozenInstanceError):
            cmd.name = "changed"  # type: ignore[misc]

    def test_custom_command_default_confirm(self) -> None:
        """CustomCommand should default confirm to False."""
        cmd = CustomCommand(key="t", name="Test", command="echo test")
        assert cmd.confirm is False

    def test_custom_command_with_confirm(self) -> None:
        """CustomCommand should accept confirm=True."""
        cmd = CustomCommand(key="t", name="Test", command="echo test", confirm=True)
        assert cmd.confirm is True


class TestParseCustomCommands:
    """Tests for custom_commands parsing in load_config()."""

    def test_custom_commands_parsed(self, tmp_path: Path) -> None:
        """Config with two custom commands should parse correctly."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text(
            "custom_commands:\n"
            "  t:\n"
            "    name: Test\n"
            "    command: echo test\n"
            "  r:\n"
            "    name: Run\n"
            "    command: ./run.sh\n"
        )

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            config = load_config()

        assert len(config.custom_commands) == 2
        cmd_t = next(c for c in config.custom_commands if c.key == "t")
        assert cmd_t.name == "Test"
        assert cmd_t.command == "echo test"
        assert cmd_t.confirm is False

        cmd_r = next(c for c in config.custom_commands if c.key == "r")
        assert cmd_r.name == "Run"
        assert cmd_r.command == "./run.sh"

    def test_custom_commands_missing_name(self, tmp_path: Path) -> None:
        """Entry without name should raise ConfigError."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text("custom_commands:\n  t:\n    command: echo test\n")

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            with pytest.raises(ConfigError, match="missing required field 'name'"):
                load_config()

    def test_custom_commands_missing_command(self, tmp_path: Path) -> None:
        """Entry without command should raise ConfigError."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text("custom_commands:\n  t:\n    name: Test\n")

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            with pytest.raises(ConfigError, match="missing required field 'command'"):
                load_config()

    def test_custom_commands_key_too_long(self, tmp_path: Path) -> None:
        """Key with multiple characters should raise ConfigError."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text(
            "custom_commands:\n  ab:\n    name: Test\n    command: echo test\n"
        )

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            with pytest.raises(ConfigError, match="must be a single character"):
                load_config()

    def test_custom_commands_confirm_default_false(self, tmp_path: Path) -> None:
        """Entry without confirm should default to False."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text(
            "custom_commands:\n  t:\n    name: Test\n    command: echo test\n"
        )

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            config = load_config()

        assert config.custom_commands[0].confirm is False

    def test_custom_commands_confirm_true(self, tmp_path: Path) -> None:
        """Entry with confirm: true should parse correctly."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text(
            "custom_commands:\n"
            "  t:\n"
            "    name: Test\n"
            "    command: echo test\n"
            "    confirm: true\n"
        )

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            config = load_config()

        assert config.custom_commands[0].confirm is True

    def test_custom_commands_absent_returns_empty(self, tmp_path: Path) -> None:
        """Config without custom_commands key should return empty tuple."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text("open_workspace_cmd: code .\n")

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            config = load_config()

        assert config.custom_commands == ()

    def test_custom_commands_ignores_unknown_fields(self, tmp_path: Path) -> None:
        """Entry with extra field should not error and ignore the extra."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text(
            "custom_commands:\n"
            "  t:\n"
            "    name: Test\n"
            "    command: echo test\n"
            "    unknown_field: ignored\n"
        )

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            config = load_config()

        assert len(config.custom_commands) == 1
        assert config.custom_commands[0].name == "Test"

    def test_custom_commands_empty_map(self, tmp_path: Path) -> None:
        """custom_commands: {} should return empty tuple."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text("custom_commands: {}\n")

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            config = load_config()

        assert config.custom_commands == ()

    def test_custom_commands_confirm_not_bool(self, tmp_path: Path) -> None:
        """Entry with non-bool confirm should raise ConfigError."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text(
            "custom_commands:\n"
            "  t:\n"
            "    name: Test\n"
            "    command: echo test\n"
            "    confirm: 'yes'\n"
        )

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            with pytest.raises(ConfigError, match="'confirm' must be a boolean"):
                load_config()

    def test_custom_commands_entry_not_dict(self, tmp_path: Path) -> None:
        """Entry that's not a dict should raise ConfigError."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text("custom_commands:\n  t: not a dict\n")

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            with pytest.raises(ConfigError, match="must be a mapping"):
                load_config()

    def test_custom_commands_not_dict(self, tmp_path: Path) -> None:
        """custom_commands that's not a dict should raise ConfigError."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        config_file = config_dir / "wk.yml"
        config_file.write_text("custom_commands:\n  - item1\n  - item2\n")

        with patch("wk.config._find_repo_root", return_value=tmp_path):
            with pytest.raises(ConfigError, match="must be a mapping"):
                load_config()
