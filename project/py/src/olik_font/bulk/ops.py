"""cjk-decomp operator → olik compose mode LUT."""

from __future__ import annotations

# Mapping of cjk-decomp operator codes to olik compose Preset names.
# Unmapped operators → None (treated as unsupported_op by the planner).
OP_TO_MODE: dict[str, str] = {
    "a": "left_right",  # 左右並列
    "d": "top_bottom",  # 上下並列
    "s": "enclose",  # 全包圍
    "r3tr": "repeat_triangle",  # 品字形三疊
}

SUPPORTED_MODES: frozenset[str] = frozenset(OP_TO_MODE.values())


def resolve_mode(op: str) -> str | None:
    return OP_TO_MODE.get(op)
