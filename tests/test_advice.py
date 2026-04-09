"""Tests for ADVICE column computation."""

from wk.status.advice import (
    ADV_WORKING,
    CLEANUP,
    FIX_CI,
    INPUT,
    MERGE,
    REBASE,
    RESUME,
    REVIEWER,
    VIEW_PR,
    compute_advice,
)
from wk.status.agent import IDLE, OFF, WAITING, WORKING
from wk.status.ci import CIStatus


class TestComputeAdvice:
    """Tests for compute_advice priority rules."""

    def test_cleanup_when_merged(self) -> None:
        ci = CIStatus(is_merged=True, pr_url="url")
        assert compute_advice(ci, WORKING) == CLEANUP

    def test_cleanup_when_closed(self) -> None:
        ci = CIStatus(is_closed=True, pr_url="url")
        assert compute_advice(ci, WORKING) == CLEANUP

    def test_merge_when_approved_and_green(self) -> None:
        ci = CIStatus(
            check_status="success",
            review_decision="APPROVED",
            pr_url="url",
        )
        assert compute_advice(ci, IDLE) == MERGE

    def test_fix_ci_when_failing(self) -> None:
        ci = CIStatus(check_status="failure", pr_url="url")
        assert compute_advice(ci, IDLE) == FIX_CI

    def test_rebase_when_conflicts(self) -> None:
        assert compute_advice(None, IDLE, has_conflicts=True) == REBASE

    def test_input_when_agent_waiting(self) -> None:
        assert compute_advice(None, WAITING) == INPUT

    def test_reviewer_when_disconnected_with_pr(self) -> None:
        ci = CIStatus(check_status="pending", pr_url="url")
        assert compute_advice(ci, OFF) == REVIEWER

    def test_reviewer_when_no_reviewer(self) -> None:
        ci = CIStatus(
            check_status="success",
            has_reviewer=False,
            pr_url="url",
        )
        assert compute_advice(ci, "") == REVIEWER

    def test_working_when_agent_active(self) -> None:
        assert compute_advice(None, WORKING) == ADV_WORKING

    def test_resume_when_agent_idle(self) -> None:
        assert compute_advice(None, IDLE) == RESUME

    def test_view_pr_default(self) -> None:
        ci = CIStatus(
            check_status="pending",
            has_reviewer=True,
            pr_url="url",
        )
        assert compute_advice(ci, "") == VIEW_PR

    def test_empty_when_disconnected_no_pr(self) -> None:
        assert compute_advice(None, OFF) == ""

    def test_empty_when_nothing_matches(self) -> None:
        assert compute_advice(None, "") == ""

    def test_priority_cleanup_over_fix_ci(self) -> None:
        ci = CIStatus(
            check_status="failure",
            is_merged=True,
            pr_url="url",
        )
        assert compute_advice(ci, WORKING) == CLEANUP

    def test_priority_merge_over_input(self) -> None:
        ci = CIStatus(
            check_status="success",
            review_decision="APPROVED",
            pr_url="url",
        )
        assert compute_advice(ci, WAITING) == MERGE

    def test_priority_fix_ci_over_rebase(self) -> None:
        ci = CIStatus(check_status="failure", pr_url="url")
        assert compute_advice(ci, IDLE, has_conflicts=True) == FIX_CI

    def test_priority_reviewer_over_input(self) -> None:
        ci = CIStatus(check_status="pending", pr_url="url")
        assert compute_advice(ci, WAITING) == REVIEWER

    def test_priority_working_over_view_pr(self) -> None:
        ci = CIStatus(check_status="pending", has_reviewer=True, pr_url="url")
        assert compute_advice(ci, WORKING) == ADV_WORKING
