"""GitHub CI status via the `gh` CLI.

Fetches PR status checks and review decisions for worktree branches.
"""

import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CIStatus:
    """CI status for a single worktree/branch.

    Attributes:
        check_status: Overall check status: "success", "failure", "pending", or None.
        review_decision: Review decision: "APPROVED", "CHANGES_REQUESTED",
            "REVIEW_REQUIRED", or None.
        is_merged: Whether the PR has been merged.
        is_closed: Whether the PR has been closed (without merge).
        has_reviewer: Whether any reviewer is assigned.
        pr_url: URL of the PR, or None if no PR exists.
    """

    check_status: str | None = None
    review_decision: str | None = None
    is_merged: bool = False
    is_closed: bool = False
    has_reviewer: bool = False
    pr_url: str | None = None

    @property
    def display(self) -> str:
        """Return a display character for the CI column."""
        if self.pr_url is None:
            return "—"
        if self.is_merged:
            return "✓"
        if self.check_status == "success":
            return "✓"
        if self.check_status == "failure":
            return "✗"
        if self.check_status == "pending":
            return "⟳"
        return "—"

    @property
    def is_approved(self) -> bool:
        """Whether the PR is approved."""
        return self.review_decision == "APPROVED"


def _rollup_status(checks: list[dict] | None) -> str | None:
    """Compute overall status from statusCheckRollup list.

    Handles both CheckRun entries (status/conclusion fields) and
    StatusContext entries (state field) from the GitHub API.

    Returns "success", "failure", "pending", or None.
    """
    if not checks:
        return None

    has_pending = False
    for check in checks:
        # CheckRun: has "status" and "conclusion"
        status = check.get("status", "").upper()
        conclusion = check.get("conclusion", "").upper()

        if status == "COMPLETED":
            if conclusion in ("FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED"):
                return "failure"
            continue

        # StatusContext: has "state" instead of status/conclusion
        state = check.get("state", "").upper()
        if state in ("FAILURE", "ERROR"):
            return "failure"
        if state == "SUCCESS":
            continue
        if state == "PENDING":
            has_pending = True
            continue

        # CheckRun that isn't COMPLETED yet
        if status:
            has_pending = True

    if has_pending:
        return "pending"
    return "success"


def fetch_ci_statuses(repo_root: Path) -> dict[str, CIStatus]:
    """Fetch CI status for all open PRs in the repo.

    Args:
        repo_root: Path to the git repo root (used as cwd for gh).

    Returns:
        Dict mapping branch name to CIStatus.
        Empty dict if gh is not available or the command fails.
    """
    if not shutil.which("gh"):
        return {}

    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "all",
            "--limit",
            "100",
            "--json",
            "headRefName,statusCheckRollup,reviewDecision,"
            "mergedAt,closedAt,url,reviewRequests,assignees",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        check=False,
    )
    if result.returncode != 0:
        return {}

    try:
        prs = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}

    statuses: dict[str, CIStatus] = {}
    for pr in prs:
        branch = pr.get("headRefName", "")
        if not branch:
            continue

        check_status = _rollup_status(pr.get("statusCheckRollup"))
        review_decision = pr.get("reviewDecision") or None
        is_merged = bool(pr.get("mergedAt"))
        is_closed = bool(pr.get("closedAt")) and not is_merged
        has_reviewer = bool(pr.get("reviewRequests"))
        pr_url = pr.get("url")

        statuses[branch] = CIStatus(
            check_status=check_status,
            review_decision=review_decision,
            is_merged=is_merged,
            is_closed=is_closed,
            has_reviewer=has_reviewer,
            pr_url=pr_url,
        )

    return statuses


class CIStatusCache:
    """In-memory cache for CI status with TTL."""

    def __init__(self, ttl: float = 30.0) -> None:
        self._ttl = ttl
        self._cache: dict[str, CIStatus] = {}
        self._last_fetch: float = 0.0

    def get(self, repo_root: Path) -> dict[str, CIStatus]:
        """Get cached CI statuses, refreshing if stale."""
        now = time.monotonic()
        if now - self._last_fetch > self._ttl:
            result = fetch_ci_statuses(repo_root)
            if result or not self._cache:
                self._cache = result
            self._last_fetch = now
        return self._cache

    def invalidate(self) -> None:
        """Force the next get() to refresh."""
        self._last_fetch = 0.0
