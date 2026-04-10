"""Tests for layout.py."""

from pathlib import Path
from unittest.mock import patch

from wk.config import WkConfig
from wk.layout import (
    generate_zellij_layout,
    is_inside_zellij,
    is_tmux_available,
    is_zellij_available,
)


class TestGenerateZellijLayout:
    """Tests for generate_zellij_layout."""

    def test_contains_pane_structure(self) -> None:
        config = WkConfig(repo_root=Path("/test/repo"))
        layout = generate_zellij_layout(config)
        assert "layout {" in layout
        assert 'split_direction="vertical"' in layout

    def test_contains_hub_command(self) -> None:
        config = WkConfig(repo_root=Path("/test/repo"))
        layout = generate_zellij_layout(config)
        assert '"hub"' in layout

    def test_contains_workspace_command(self) -> None:
        config = WkConfig(repo_root=Path("/test/repo"))
        layout = generate_zellij_layout(config)
        assert '"workspace"' in layout

    def test_contains_cwd(self) -> None:
        config = WkConfig(repo_root=Path("/my/project"))
        layout = generate_zellij_layout(config)
        assert "/my/project" in layout

    def test_size_proportions(self) -> None:
        config = WkConfig(repo_root=Path("/test/repo"))
        layout = generate_zellij_layout(config)
        assert 'size="40%"' in layout
        assert 'size="60%"' in layout


class TestIsInsideZellij:
    """Tests for is_inside_zellij."""

    def test_true_when_env_set(self, monkeypatch) -> None:
        monkeypatch.setenv("ZELLIJ", "1")
        assert is_inside_zellij() is True

    def test_false_when_env_not_set(self, monkeypatch) -> None:
        monkeypatch.delenv("ZELLIJ", raising=False)
        assert is_inside_zellij() is False


class TestToolAvailability:
    """Tests for is_tmux_available and is_zellij_available."""

    def test_tmux_available_when_installed(self) -> None:
        with patch("wk.layout.shutil.which", return_value="/usr/bin/tmux"):
            assert is_tmux_available() is True

    def test_tmux_not_available(self) -> None:
        with patch("wk.layout.shutil.which", return_value=None):
            assert is_tmux_available() is False

    def test_zellij_available_when_installed(self) -> None:
        with patch("wk.layout.shutil.which", return_value="/usr/bin/zellij"):
            assert is_zellij_available() is True

    def test_zellij_not_available(self) -> None:
        with patch("wk.layout.shutil.which", return_value=None):
            assert is_zellij_available() is False
