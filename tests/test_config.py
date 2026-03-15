"""Tests for config.py."""

from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import pytest

from wk.config import ConfigError, WkConfig, load_config


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
