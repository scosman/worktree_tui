"""Tests for CLI entry point."""

from wk.cli import main


def test_main_exists():
    """Verify main function exists and is callable."""
    assert callable(main)
