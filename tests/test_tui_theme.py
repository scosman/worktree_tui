"""Tests for tui/theme.py."""

import re

from wk.tui.theme import APP_CSS, ThemeColors


class TestThemeColors:
    """Tests for ThemeColors constants."""

    def test_accent_is_valid_hex_color(self):
        """ACCENT should be a valid hex color."""
        assert re.match(r"^#[0-9a-f]{6}$", ThemeColors.ACCENT, re.IGNORECASE)

    def test_text_is_valid_hex_color(self):
        """TEXT should be a valid hex color."""
        assert re.match(r"^#[0-9a-f]{6}$", ThemeColors.TEXT, re.IGNORECASE)

    def test_text_dim_is_valid_hex_color(self):
        """TEXT_DIM should be a valid hex color."""
        assert re.match(r"^#[0-9a-f]{6}$", ThemeColors.TEXT_DIM, re.IGNORECASE)

    def test_background_is_valid_hex_color(self):
        """BACKGROUND should be a valid hex color."""
        assert re.match(r"^#[0-9a-f]{6}$", ThemeColors.BACKGROUND, re.IGNORECASE)

    def test_selected_is_valid_hex_color(self):
        """SELECTED should be a valid hex color."""
        assert re.match(r"^#[0-9a-f]{6}$", ThemeColors.SELECTED, re.IGNORECASE)

    def test_error_is_valid_hex_color(self):
        """ERROR should be a valid hex color."""
        assert re.match(r"^#[0-9a-f]{6}$", ThemeColors.ERROR, re.IGNORECASE)

    def test_success_is_valid_hex_color(self):
        """SUCCESS should be a valid hex color."""
        assert re.match(r"^#[0-9a-f]{6}$", ThemeColors.SUCCESS, re.IGNORECASE)


class TestAppCss:
    """Tests for APP_CSS constant."""

    def test_app_css_is_non_empty_string(self):
        """APP_CSS should be a non-empty string."""
        assert isinstance(APP_CSS, str)
        assert len(APP_CSS) > 0

    def test_app_css_contains_screen_selector(self):
        """APP_CSS should style the Screen."""
        assert "Screen" in APP_CSS

    def test_app_css_contains_worktreelist_selector(self):
        """APP_CSS should style WorktreeList."""
        assert "WorktreeList" in APP_CSS
