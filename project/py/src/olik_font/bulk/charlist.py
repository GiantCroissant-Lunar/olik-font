"""Load the MoE 4808 char list + deterministic bucket selection."""

from __future__ import annotations

import random
from pathlib import Path

_DATA_ROOT = Path(__file__).resolve().parents[3] / "data"
_MOE_FILE = _DATA_ROOT / "moe_4808.txt"


def _is_cjk(ch: str) -> bool:
    return len(ch) == 1 and (
        "\u4e00" <= ch <= "\u9fff"  # CJK Unified
        or "\u3400" <= ch <= "\u4dbf"  # CJK Extension A
    )


def load_moe_4808(path: Path | None = None) -> list[str]:
    """Return the list of CJK chars in the MoE 4808 file, deduplicated,
    preserving first-occurrence order.
    """
    src = path or _MOE_FILE
    raw = src.read_text(encoding="utf-8")
    seen: set[str] = set()
    out: list[str] = []
    for token in raw.replace("\n", " ").split():
        for ch in token:
            if _is_cjk(ch) and ch not in seen:
                seen.add(ch)
                out.append(ch)
    return out


def select_buckets(
    pool: list[str],
    already_filled: set[str],
    count: int,
    seed: int,
) -> list[str]:
    """Pick up to `count` chars from `pool` that aren't in
    `already_filled`. Deterministic per seed — sorts candidates by their
    index in `pool` first so the same (pool, filled) yields the same
    shuffle for the same seed.
    """
    candidates = [ch for ch in pool if ch not in already_filled]
    rng = random.Random(seed)
    rng.shuffle(candidates)
    return candidates[:count]
