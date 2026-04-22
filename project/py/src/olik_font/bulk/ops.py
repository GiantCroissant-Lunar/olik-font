"""cjk-decomp operator support whitelist.

The operator tells us structural intent (binary left/right split, binary
top/bottom split, full enclosure, triple repeat). It does NOT tell us
placement — that comes from measuring the MMH `matches` partition. The
whitelist here only gates which decomposition shapes the bulk auto-
planner will accept; callers must still read the partition to place
components.
"""

from __future__ import annotations

SUPPORTED_OPS: frozenset[str] = frozenset({"a", "d", "s", "r3tr"})


def is_supported_op(op: str) -> bool:
    return op in SUPPORTED_OPS


def expected_component_count(op: str) -> int | None:
    """Structural arity hint used for validation, not for placement."""
    return {"a": 2, "d": 2, "s": 2, "r3tr": 3}.get(op)
