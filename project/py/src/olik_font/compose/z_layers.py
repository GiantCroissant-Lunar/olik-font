"""Map (stroke role, order) to a z value in 0..99.

Pass-1 policy: every stroke lives in the `stroke_body` layer (10..49).
Per-role base offsets within that range keep strokes of different roles
distinguishable in LayerZDepth visualizations without fragmenting layers
that Plan 03 has no content for (edge / texture / damage).
"""

from __future__ import annotations

_ROLE_BASE = {
    "horizontal": 10,
    "vertical": 14,
    "dot": 18,
    "hook": 22,
    "slash": 26,
    "backslash": 30,
    "fold": 34,
    "other": 38,
}


def z_for_stroke(role: str, order: int) -> int:
    base = _ROLE_BASE.get(role, _ROLE_BASE["other"])
    return min(base + order, 49)
