"""Computed ADVICE column based on CI, Linear, and Agent status.

Returns a recommended next action for each worktree, based on priority rules.
"""

from wk.status.agent import IDLE, WAITING, WORKING
from wk.status.ci import CIStatus

# Advice values (in priority order)
CLEANUP = "CLEANUP"
MERGE = "MERGE"
FIX_CI = "FIX_CI"
REBASE = "REBASE"
INPUT = "INPUT"
RESUME = "RESUME"
BEGIN = "BEGIN"
REVIEWER = "REVIEWER"
IN_REVIEW = "IN_REVIEW"
ADV_WORKING = "WAIT"
VIEW_PR = "VIEW_PR"


def compute_advice(
    ci: CIStatus | None,
    agent_state: str,
    has_conflicts: bool = False,
    linear_state: str = "",
) -> str:
    """Compute the recommended next action for a worktree.

    Priority rules (first match wins):
     1. CLEANUP  — PR merged/closed
     2. MERGE    — PR approved + CI green
     3. FIX_CI   — CI failing
     4. REBASE   — merge conflicts
     5. INPUT    — Claude waiting for input
     6. RESUME   — Claude disconnected
     7. REVIEWER — PR exists but no reviewer
     8. WORKING  — Claude actively working
     9. RESUME   — Claude idle
    10. VIEW_PR  — PR exists (fallthrough)
    11. -        — Claude disconnected (no PR context)
    12. -        — nothing matches
    """
    # 1. PR merged or closed -> clean up
    if ci and (ci.is_merged or ci.is_closed):
        return CLEANUP

    # 2. PR approved + CI green -> merge
    if ci and ci.is_approved and ci.check_status == "success":
        return MERGE

    # 3. CI failing -> fix
    if ci and ci.check_status == "failure":
        return FIX_CI

    # 4. Merge conflicts
    if has_conflicts:
        return REBASE

    # 5. PR exists but no reviewer
    if ci and ci.pr_url and not ci.has_reviewer:
        return REVIEWER

    # 6. PR waiting on reviewer approval
    if ci and ci.pr_url and ci.has_reviewer and ci.review_decision == "REVIEW_REQUIRED":
        return IN_REVIEW

    # 7. Claude waiting for user input
    if agent_state == WAITING:
        return INPUT

    # 8. Claude actively working
    if agent_state == WORKING:
        return ADV_WORKING

    # 9. Claude idle at prompt
    if agent_state == IDLE:
        return RESUME

    # 10. PR exists -> view it
    if ci and ci.pr_url:
        return VIEW_PR

    # 11. Linear ticket in planned state
    if linear_state.lower() == "planned":
        return BEGIN

    # 12. Nothing matches
    return ""
