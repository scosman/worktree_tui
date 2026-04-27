"""Linear ticket status via GraphQL API.

Matches worktree names to Linear tickets by extracting ticket IDs
from branch names (e.g., "KIL-123/description" -> "KIL-123").
"""

import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass

LINEAR_API_URL = "https://api.linear.app/graphql"

# Matches ticket IDs like "KIL-123" at the start of a worktree name
_TICKET_RE = re.compile(r"^([A-Z]+-\d+)")


@dataclass(frozen=True)
class LinearStatus:
    """Status of a Linear ticket.

    Attributes:
        ticket_id: The ticket identifier (e.g., "KIL-123").
        state_name: The workflow state name (e.g., "In Progress", "Done").
    """

    ticket_id: str
    state_name: str


def extract_ticket_id(worktree_name: str) -> str | None:
    """Extract a Linear ticket ID from a worktree name.

    Matches patterns like "KIL-123", "KIL-123/description",
    "KIL-123-description".

    Returns the ticket ID or None if no match.
    """
    match = _TICKET_RE.match(worktree_name)
    return match.group(1) if match else None


def _get_api_key(config_key: str | None = None) -> str | None:
    """Get the Linear API key from config or environment.

    Args:
        config_key: API key from wk.yml config (takes precedence).

    Returns the API key, or None if not configured.
    """
    if config_key:
        return config_key
    return os.environ.get("LINEAR_API_KEY")


def _parse_ticket(ticket_id: str) -> tuple[str, int] | None:
    """Parse 'KIL-123' into ('KIL', 123)."""
    parts = ticket_id.split("-", 1)
    if len(parts) == 2:
        try:
            return parts[0], int(parts[1])
        except ValueError:
            pass
    return None


def _fetch_issue_states(api_key: str, ticket_ids: list[str]) -> dict[str, str]:
    """Fetch workflow states for a list of ticket IDs from Linear API.

    Args:
        api_key: Linear API key.
        ticket_ids: List of ticket identifiers (e.g., ["KIL-123", "KIL-456"]).

    Returns:
        Dict mapping ticket ID to state name.
    """
    if not ticket_ids:
        return {}

    # Group tickets by team prefix
    teams: dict[str, list[int]] = {}
    for tid in ticket_ids:
        parsed = _parse_ticket(tid)
        if parsed:
            prefix, number = parsed
            teams.setdefault(prefix, []).append(number)

    if not teams:
        return {}

    # Build filter: number in [...] AND team key matches
    # For multiple teams, use OR filter
    team_filters = []
    for prefix, numbers in teams.items():
        team_filters.append(
            {"number": {"in": numbers}, "team": {"key": {"eq": prefix}}}
        )

    if len(team_filters) == 1:
        issue_filter = team_filters[0]
    else:
        issue_filter = {"or": team_filters}

    query = """
    query($filter: IssueFilter) {
        issues(filter: $filter) {
            nodes {
                identifier
                state {
                    name
                }
            }
        }
    }
    """
    variables = {"filter": issue_filter}

    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        LINEAR_API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": api_key,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return {}

    results: dict[str, str] = {}
    nodes = data.get("data", {}).get("issues", {}).get("nodes", [])
    for node in nodes:
        identifier = node.get("identifier", "")
        state_name = node.get("state", {}).get("name", "")
        if identifier and state_name:
            results[identifier] = state_name

    return results


def fetch_linear_statuses(
    worktree_names: list[str],
    api_key: str | None = None,
) -> dict[str, LinearStatus]:
    """Fetch Linear statuses for worktrees.

    Args:
        worktree_names: List of worktree names to check.
        api_key: Optional API key (falls back to env var).

    Returns:
        Dict mapping worktree name to LinearStatus.
        Only includes worktrees that have matching tickets.
    """
    key = _get_api_key(api_key)
    if not key:
        return {}

    # Extract ticket IDs from worktree names
    name_to_ticket: dict[str, str] = {}
    for name in worktree_names:
        ticket_id = extract_ticket_id(name)
        if ticket_id:
            name_to_ticket[name] = ticket_id

    if not name_to_ticket:
        return {}

    # Fetch states from Linear
    ticket_ids = list(set(name_to_ticket.values()))
    states = _fetch_issue_states(key, ticket_ids)

    # Map back to worktree names
    results: dict[str, LinearStatus] = {}
    for name, ticket_id in name_to_ticket.items():
        state_name = states.get(ticket_id)
        if state_name:
            results[name] = LinearStatus(
                ticket_id=ticket_id,
                state_name=state_name,
            )

    return results


class LinearStatusCache:
    """In-memory cache for Linear status with TTL."""

    def __init__(self, ttl: float = 60.0) -> None:
        self._ttl = ttl
        self._cache: dict[str, LinearStatus] = {}
        self._last_fetch: float = 0.0

    def get(
        self,
        worktree_names: list[str],
        api_key: str | None = None,
    ) -> dict[str, LinearStatus]:
        """Get cached Linear statuses, refreshing if stale."""
        now = time.monotonic()
        if now - self._last_fetch > self._ttl:
            self._cache = fetch_linear_statuses(worktree_names, api_key)
            self._last_fetch = now
        return self._cache

    def invalidate(self) -> None:
        """Force the next get() to refresh."""
        self._last_fetch = 0.0
