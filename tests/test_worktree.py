"""Tests for worktree.py."""

import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from wk.worktree import (
    Worktree,
    WtCommandError,
    _parse_worktree,
    create_worktree,
    find_worktree,
    list_worktrees,
    remove_worktree,
)

# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent


class TestWorktree:
    """Tests for Worktree dataclass."""

    def test_worktree_is_immutable(self) -> None:
        """Worktree should be frozen/immutable."""
        worktree = Worktree(
            name="test",
            path=Path("/test/path"),
            branch="test",
            created=datetime.now(UTC),
        )
        with pytest.raises(FrozenInstanceError):
            worktree.name = "changed"  # type: ignore[misc]

    def test_worktree_attributes(self) -> None:
        """Worktree should store all attributes correctly."""
        created = datetime(2025, 3, 10, 14, 30, 0, tzinfo=UTC)
        worktree = Worktree(
            name="my-feature",
            path=Path("/Users/me/project/.worktrees/my-feature"),
            branch="my-feature",
            created=created,
        )
        assert worktree.name == "my-feature"
        assert worktree.path == Path("/Users/me/project/.worktrees/my-feature")
        assert worktree.branch == "my-feature"
        assert worktree.created == created


class TestListWorktrees:
    """Tests for list_worktrees function."""

    def _mock_subprocess(
        self, stdout: str = "", returncode: int = 0, stderr: str = ""
    ) -> None:
        """Helper to mock subprocess.run."""
        self._mock_patcher = patch("subprocess.run")
        mock_run = self._mock_patcher.start()
        mock_run.return_value.stdout = stdout
        mock_run.return_value.returncode = returncode
        mock_run.return_value.stderr = stderr

    def teardown_method(self) -> None:
        """Stop any patchers."""
        if hasattr(self, "_mock_patcher"):
            self._mock_patcher.stop()

    def test_list_worktrees_parses_valid_json(self) -> None:
        """list_worktrees should parse valid JSON output."""
        json_output = json.dumps(
            [
                {
                    "name": "my-feature",
                    "path": "/Users/me/project/.worktrees/my-feature",
                    "branch": "my-feature",
                    "created": "2025-03-10T14:30:00Z",
                }
            ]
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = json_output
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            worktrees = list_worktrees()

        assert len(worktrees) == 1
        assert worktrees[0].name == "my-feature"
        assert worktrees[0].path == Path("/Users/me/project/.worktrees/my-feature")
        assert worktrees[0].branch == "my-feature"

    def test_list_worktrees_sorted_by_created_desc(self) -> None:
        """list_worktrees should return worktrees sorted by created date desc."""
        json_output = json.dumps(
            [
                {
                    "name": "old-feature",
                    "path": "/path/old",
                    "branch": "old-feature",
                    "created": "2025-03-01T10:00:00Z",
                },
                {
                    "name": "new-feature",
                    "path": "/path/new",
                    "branch": "new-feature",
                    "created": "2025-03-10T14:30:00Z",
                },
                {
                    "name": "mid-feature",
                    "path": "/path/mid",
                    "branch": "mid-feature",
                    "created": "2025-03-05T12:00:00Z",
                },
            ]
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = json_output
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            worktrees = list_worktrees()

        assert len(worktrees) == 3
        # Should be sorted newest first
        assert worktrees[0].name == "new-feature"
        assert worktrees[1].name == "mid-feature"
        assert worktrees[2].name == "old-feature"

    def test_list_worktrees_empty_list(self) -> None:
        """list_worktrees should return empty list when no worktrees."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "[]"
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            worktrees = list_worktrees()

        assert worktrees == []

    def test_list_worktrees_raises_on_failure(self) -> None:
        """list_worktrees should raise WtCommandError on failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "error: wt command failed"

            with pytest.raises(WtCommandError) as exc_info:
                list_worktrees()

        assert exc_info.value.returncode == 1
        assert "error: wt command failed" in exc_info.value.stderr

    def test_json_parser_handles_unknown_fields(self) -> None:
        """Parser should ignore unknown fields gracefully."""
        json_output = json.dumps(
            [
                {
                    "name": "my-feature",
                    "path": "/path/to/worktree",
                    "branch": "my-feature",
                    "created": "2025-03-10T14:30:00Z",
                    "unknown_field": "should be ignored",
                    "another_unknown": 12345,
                }
            ]
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = json_output
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            worktrees = list_worktrees()

        assert len(worktrees) == 1
        assert worktrees[0].name == "my-feature"


class TestCreateWorktree:
    """Tests for create_worktree function."""

    def test_create_worktree_runs_correct_command(self) -> None:
        """create_worktree should run wt switch --create <name> --base=@."""
        json_output = json.dumps(
            [
                {
                    "name": "new-branch",
                    "path": "/path/new-branch",
                    "branch": "new-branch",
                    "created": "2025-03-10T14:30:00Z",
                }
            ]
        )
        with patch("subprocess.run") as mock_run:
            # First call is create, second is list
            mock_run.return_value.stdout = json_output
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            result = create_worktree("new-branch")

            # Verify the command was called with correct args
            assert mock_run.call_count >= 1
            first_call_args = mock_run.call_args_list[0][0][0]
            expected = ["wt", "switch", "--create", "new-branch", "--base=@", "--yes"]
            assert first_call_args == expected

        assert result.name == "new-branch"

    def test_create_worktree_raises_on_duplicate(self) -> None:
        """create_worktree should raise WtCommandError on duplicate name."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "error: branch already exists"

            with pytest.raises(WtCommandError) as exc_info:
                create_worktree("existing-branch")

        assert exc_info.value.returncode == 1


class TestRemoveWorktree:
    """Tests for remove_worktree function."""

    def test_remove_worktree_runs_correct_command(self) -> None:
        """remove_worktree should run wt remove <name>."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            remove_worktree("test-branch")

            called_args = mock_run.call_args[0][0]
            assert called_args == ["wt", "remove", "test-branch", "--yes"]

    def test_remove_worktree_raises_on_failure(self) -> None:
        """remove_worktree should raise WtCommandError on failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "error: worktree not found"

            with pytest.raises(WtCommandError) as exc_info:
                remove_worktree("nonexistent")

        assert exc_info.value.returncode == 1


class TestFindWorktree:
    """Tests for find_worktree function."""

    def test_find_worktree_returns_match(self) -> None:
        """find_worktree should return matching worktree by name."""
        json_output = json.dumps(
            [
                {
                    "name": "feature-a",
                    "path": "/path/a",
                    "branch": "feature-a",
                    "created": "2025-03-10T10:00:00Z",
                },
                {
                    "name": "feature-b",
                    "path": "/path/b",
                    "branch": "feature-b",
                    "created": "2025-03-10T11:00:00Z",
                },
                {
                    "name": "feature-c",
                    "path": "/path/c",
                    "branch": "feature-c",
                    "created": "2025-03-10T12:00:00Z",
                },
            ]
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = json_output
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            result = find_worktree("feature-b")

        assert result is not None
        assert result.name == "feature-b"
        assert result.path == Path("/path/b")

    def test_find_worktree_returns_none(self) -> None:
        """find_worktree should return None for no match."""
        json_output = json.dumps(
            [
                {
                    "name": "feature-a",
                    "path": "/path/a",
                    "branch": "feature-a",
                    "created": "2025-03-10T10:00:00Z",
                },
            ]
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = json_output
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            result = find_worktree("nonexistent")

        assert result is None

    def test_find_worktree_case_sensitive(self) -> None:
        """find_worktree should be case-sensitive."""
        json_output = json.dumps(
            [
                {
                    "name": "Feature-A",
                    "path": "/path/a",
                    "branch": "Feature-A",
                    "created": "2025-03-10T10:00:00Z",
                },
            ]
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = json_output
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            # lowercase should not match
            result_lower = find_worktree("feature-a")
            # exact case should match
            result_exact = find_worktree("Feature-A")

        assert result_lower is None
        assert result_exact is not None
        assert result_exact.name == "Feature-A"


class TestWtCommandError:
    """Tests for WtCommandError exception."""

    def test_error_attributes(self) -> None:
        """WtCommandError should store command, stderr, and returncode."""
        error = WtCommandError(command="wt list", stderr="some error", returncode=1)
        assert error.command == "wt list"
        assert error.stderr == "some error"
        assert error.returncode == 1

    def test_error_message(self) -> None:
        """WtCommandError should have a descriptive message."""
        error = WtCommandError(
            command="wt remove foo", stderr="not found", returncode=1
        )
        assert "wt remove foo" in str(error)
        assert "1" in str(error)
        assert "not found" in str(error)


class TestRealWtListJson:
    """Tests using real wt list --format json output."""

    def test_parse_real_json_fixture(self) -> None:
        """Parser should handle real wt list --format json output."""
        fixture_path = FIXTURES_DIR / "example_wr_list.json"
        with open(fixture_path) as f:
            data = json.load(f)

        worktrees = [_parse_worktree(item) for item in data]

        # Should have parsed all worktrees without error
        assert len(worktrees) == 16

    def test_parse_uses_branch_as_name(self) -> None:
        """Parser should use branch as name when name field is absent."""
        fixture_path = FIXTURES_DIR / "example_wr_list.json"
        with open(fixture_path) as f:
            data = json.load(f)

        # First entry has branch but no name field
        main = _parse_worktree(data[0])

        assert main.name == "scosman/worktrees"
        assert main.branch == "scosman/worktrees"

    def test_parse_worktree_with_dash_in_name(self) -> None:
        """Parser should correctly parse worktrees with dashes in name."""
        fixture_path = FIXTURES_DIR / "example_wr_list.json"
        with open(fixture_path) as f:
            data = json.load(f)

        # Find my-feature-name worktree
        for item in data:
            if item["branch"] == "my-feature-name":
                wt = _parse_worktree(item)
                assert wt.name == "my-feature-name"
                assert wt.branch == "my-feature-name"
                break

    def test_parse_worktree_with_underscore_in_name(self) -> None:
        """Parser should correctly parse worktrees with underscores in name."""
        fixture_path = FIXTURES_DIR / "example_wr_list.json"
        with open(fixture_path) as f:
            data = json.load(f)

        # Find abstract_datamodel_store worktree
        for item in data:
            if item["branch"] == "abstract_datamodel_store":
                wt = _parse_worktree(item)
                assert wt.name == "abstract_datamodel_store"
                break

    def test_parse_worktree_with_slash_in_name(self) -> None:
        """Parser should correctly parse worktrees with slash in name."""
        fixture_path = FIXTURES_DIR / "example_wr_list.json"
        with open(fixture_path) as f:
            data = json.load(f)

        # First entry has branch scosman/worktrees (slash in name)
        wt = _parse_worktree(data[0])
        assert wt.name == "scosman/worktrees"
        assert wt.branch == "scosman/worktrees"

    def test_parse_timestamp_conversion(self) -> None:
        """Parser should convert Unix timestamp to datetime."""
        fixture_path = FIXTURES_DIR / "example_wr_list.json"
        with open(fixture_path) as f:
            data = json.load(f)

        # First entry has timestamp 1773543305
        main = _parse_worktree(data[0])

        # Verify created is a datetime
        assert isinstance(main.created, datetime)

    def test_parse_empty_commit_message(self) -> None:
        """Parser should handle empty commit message."""
        fixture_path = FIXTURES_DIR / "example_wr_list.json"
        with open(fixture_path) as f:
            data = json.load(f)

        # Find my-feature which has empty commit message
        for item in data:
            if item["branch"] == "my-feature":
                wt = _parse_worktree(item)
                assert wt.name == "my-feature"
                break

    def test_parse_zero_timestamp(self) -> None:
        """Parser should handle zero timestamp (uncommitted/orphan)."""
        fixture_path = FIXTURES_DIR / "example_wr_list.json"
        with open(fixture_path) as f:
            data = json.load(f)

        # Find my-feature which has timestamp 0
        for item in data:
            if item["branch"] == "my-feature":
                wt = _parse_worktree(item)
                # Should still produce a valid datetime (epoch)
                assert isinstance(wt.created, datetime)
                break

    def test_list_worktrees_with_real_fixture(self) -> None:
        """list_worktrees should work with real fixture data."""
        fixture_path = FIXTURES_DIR / "example_wr_list.json"
        with open(fixture_path) as f:
            json_output = f.read()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = json_output
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            worktrees = list_worktrees()

        assert len(worktrees) == 16
        # Should be sorted by created desc (most recent first)
        assert worktrees[0].name == "scosman/worktrees"

    def test_parse_all_variants_of_main_state(self) -> None:
        """Parser should handle all main_state variants."""
        fixture_path = FIXTURES_DIR / "example_wr_list.json"
        with open(fixture_path) as f:
            data = json.load(f)

        # Verify we can parse all entries regardless of main_state
        main_states_seen = set()
        for item in data:
            wt = _parse_worktree(item)
            assert isinstance(wt, Worktree)
            if "main_state" in item:
                main_states_seen.add(item["main_state"])

        # We should see various states
        assert "is_main" in main_states_seen
        assert "ahead" in main_states_seen
        assert "behind" in main_states_seen

    def test_parse_path_preserved(self) -> None:
        """Parser should preserve exact path from JSON."""
        fixture_path = FIXTURES_DIR / "example_wr_list.json"
        with open(fixture_path) as f:
            data = json.load(f)

        for item in data:
            wt = _parse_worktree(item)
            assert wt.path == Path(item["path"])
