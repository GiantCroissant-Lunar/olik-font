# project/py/src/olik_font/sources/cjk_decomp.py
"""cjk-decomp adapter — loads the committed JSON snapshot at
``project/py/data/cjk-decomp.json``.

The on-disk shape is defined by ``project/schema/cjk-decomp.schema.json``.
Runtime types are quicktype-generated from that schema and live under
``olik_font.generated.cjk_decomp_types``. We wrap them in a small
project-native ``CjkDecompEntry`` dataclass for the rest of the codebase
so callers don't depend on generator-specific conventions.

Regeneration (two steps, both reproducible):

    task data:regen-cjk-decomp   # fetch upstream cjk-decomp.txt, write JSON
    task codegen:cjk-decomp      # regenerate Python + TS types from the schema

Neither step runs on a clone or in CI — the JSON is committed under
``project/py/data/`` (Apache-2.0 attributed via ``LICENSE-cjk-decomp``).
Runtime code never reaches out to the network for this dataset.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from olik_font.generated.cjk_decomp_types import CJKDecomp


@dataclass(frozen=True, slots=True)
class CjkDecompEntry:
    char: str
    operator: str | None  # single / multi-letter op; None means atomic
    components: tuple[str, ...]


def load_cjk_decomp(path: Path) -> dict[str, CjkDecompEntry]:
    """Load `cjk-decomp.json` into a char → entry table."""
    doc = CJKDecomp.from_dict(json.loads(path.read_text(encoding="utf-8")))
    return {
        char: CjkDecompEntry(
            char=char,
            operator=entry.operator,
            components=tuple(entry.components),
        )
        for char, entry in doc.entries.items()
    }


def decompose_once(table: dict[str, CjkDecompEntry], char: str) -> tuple[str, ...]:
    """One-level decomposition. Atomic chars return a 1-tuple (char,)."""
    entry = table[char]
    if entry.operator is None:
        return (char,)
    return entry.components


def decompose_recursive(
    table: dict[str, CjkDecompEntry],
    char: str,
    _seen: frozenset[str] = frozenset(),
) -> tuple[str, ...]:
    """Recursive decomposition down to atomic leaves. Cycle-safe."""
    if char in _seen:
        return (char,)
    entry = table.get(char)
    if entry is None or entry.operator is None:
        return (char,)
    out: list[str] = []
    next_seen = _seen | {char}
    for sub in entry.components:
        out.extend(decompose_recursive(table, sub, next_seen))
    return tuple(out)
