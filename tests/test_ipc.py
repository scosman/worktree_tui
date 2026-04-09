"""Tests for ipc.py."""

from pathlib import Path

from wk.ipc import (
    Selection,
    clear_state,
    read_selection,
    state_file_path,
    write_selection,
)


class TestStateFilePath:
    """Tests for state_file_path."""

    def test_returns_path_under_temp(self, tmp_path: Path, monkeypatch) -> None:
        """State file should be in a temp directory."""
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        path = state_file_path(tmp_path)
        assert path.name == "state.json"
        assert "wk" in str(path)

    def test_uses_xdg_runtime_dir(self, tmp_path: Path, monkeypatch) -> None:
        """Should prefer XDG_RUNTIME_DIR when set."""
        runtime_dir = tmp_path / "runtime"
        runtime_dir.mkdir()
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime_dir))
        path = state_file_path(Path("/some/repo"))
        assert str(path).startswith(str(runtime_dir))

    def test_different_repos_different_paths(self, monkeypatch) -> None:
        """Different repo roots should produce different state paths."""
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        path_a = state_file_path(Path("/repo/a"))
        path_b = state_file_path(Path("/repo/b"))
        assert path_a != path_b


class TestWriteReadSelection:
    """Tests for write_selection and read_selection."""

    def test_roundtrip(self, tmp_path: Path, monkeypatch) -> None:
        """Writing then reading should return the same selection."""
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        repo = Path("/test/repo")
        selection = Selection(
            worktree_name="feature-x",
            worktree_path="/path/to/feature-x",
        )
        write_selection(repo, selection)
        result = read_selection(repo)
        assert result == selection

    def test_read_nonexistent_returns_none(self, tmp_path: Path, monkeypatch) -> None:
        """Reading when no state file exists should return None."""
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        result = read_selection(Path("/nonexistent/repo"))
        assert result is None

    def test_overwrite(self, tmp_path: Path, monkeypatch) -> None:
        """Writing again should overwrite the previous selection."""
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        repo = Path("/test/repo")
        sel1 = Selection(worktree_name="a", worktree_path="/a")
        sel2 = Selection(worktree_name="b", worktree_path="/b")
        write_selection(repo, sel1)
        write_selection(repo, sel2)
        result = read_selection(repo)
        assert result == sel2

    def test_read_malformed_json_returns_none(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Malformed JSON in state file should return None."""
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        repo = Path("/test/repo")
        path = state_file_path(repo)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json")
        result = read_selection(repo)
        assert result is None


class TestClearState:
    """Tests for clear_state."""

    def test_removes_file(self, tmp_path: Path, monkeypatch) -> None:
        """clear_state should remove the state file."""
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        repo = Path("/test/repo")
        write_selection(repo, Selection("a", "/a"))
        clear_state(repo)
        assert read_selection(repo) is None

    def test_no_error_when_missing(self, tmp_path: Path, monkeypatch) -> None:
        """clear_state should not error if file doesn't exist."""
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        clear_state(Path("/nonexistent"))  # Should not raise
