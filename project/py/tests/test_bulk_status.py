"""Status enum + transitions."""

from __future__ import annotations

from olik_font.bulk.status import Status, assert_transition


def test_status_values() -> None:
    assert Status.VERIFIED.value == "verified"
    assert Status.NEEDS_REVIEW.value == "needs_review"
    assert Status.UNSUPPORTED_OP.value == "unsupported_op"
    assert Status.FAILED_EXTRACTION.value == "failed_extraction"


def test_transition_unsupported_to_verified_ok() -> None:
    assert_transition(Status.UNSUPPORTED_OP, Status.VERIFIED)


def test_transition_verified_to_needs_review_ok() -> None:
    assert_transition(Status.VERIFIED, Status.NEEDS_REVIEW)


def test_transition_from_none_always_ok() -> None:
    """First-write transitions (prior=NONE) are always allowed."""
    for target in Status:
        assert_transition(None, target)


def test_transition_between_terminal_failures_ok() -> None:
    """A re-run can flip between the three failure states as the LUT grows."""
    assert_transition(Status.UNSUPPORTED_OP, Status.FAILED_EXTRACTION)
    assert_transition(Status.FAILED_EXTRACTION, Status.UNSUPPORTED_OP)
