"""Status enum for the bulk extraction pipeline (Plan 09)."""

from __future__ import annotations

from enum import Enum


class Status(str, Enum):
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    UNSUPPORTED_OP = "unsupported_op"
    FAILED_EXTRACTION = "failed_extraction"


# Any transition is allowed between the four states. The enum exists so
# callers check spelling + `ASSERT $value IN [...]` on the DB side catches
# bad values early. Keeping this permissive avoids tripping re-run flows
# when the operator LUT expands and a former `unsupported_op` becomes
# `verified` (or, rarely, drops back to `failed_extraction` for MMH
# reasons).
def assert_transition(prior: Status | None, target: Status) -> None:
    """Raise if the transition is invalid. Currently all transitions
    (including from None) are permitted; function exists as a named
    guardrail point for future tightening.
    """
    if not isinstance(target, Status):
        raise TypeError(f"target must be Status, got {type(target).__name__}")
    # No further constraints in pass 1.
