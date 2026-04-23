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
from typing import Any

import yaml

from olik_font.generated.cjk_decomp_types import CJKDecomp

_PY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CJK_PATH = _PY_ROOT / "data" / "cjk-decomp.json"
DEFAULT_CJK_OVERRIDES = _PY_ROOT / "data" / "cjk_decomp_overrides.yaml"


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


def load_cjk_overrides(path: Path = DEFAULT_CJK_OVERRIDES) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"failed to read {path}: expected mapping")

    overrides: dict[str, dict[str, Any]] = {}
    for char, entry in raw.items():
        if not isinstance(char, str) or not char:
            raise ValueError(f"cjk override key must be a non-empty string: {char!r}")
        if not isinstance(entry, dict):
            raise ValueError(f"cjk override for {char!r} must be a mapping")
        if "operator" not in entry or "components" not in entry:
            raise ValueError(f"cjk override for {char!r} must include operator and components")

        operator = entry["operator"]
        if operator is not None and not isinstance(operator, str):
            raise ValueError(f"cjk override operator for {char!r} must be a string or null")

        components = entry["components"]
        if not isinstance(components, list) or any(
            not isinstance(component, str) or not component for component in components
        ):
            raise ValueError(f"cjk override components for {char!r} must be a list[str]")

        overrides[char] = {
            "operator": operator,
            "components": list(components),
        }
    return overrides


def load_cjk_entries(
    path: Path = DEFAULT_CJK_PATH,
    *,
    overrides_path: Path = DEFAULT_CJK_OVERRIDES,
) -> dict[str, dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = raw.get("entries", {})
    merged_entries = {
        char: dict(entry) for char, entry in entries.items() if isinstance(entry, dict)
    }

    for char, entry in load_cjk_overrides(overrides_path).items():
        merged_entries[char] = dict(entry)

    def build_component_tree(component_char: str, seen: frozenset[str]) -> dict[str, Any]:
        if component_char in seen:
            return {"char": component_char, "components": []}

        child_entry = merged_entries.get(component_char)
        raw_children = child_entry.get("components", []) if isinstance(child_entry, dict) else []
        if not isinstance(raw_children, list) or not raw_children:
            return {"char": component_char, "components": []}

        next_seen = seen | {component_char}
        return {
            "char": component_char,
            "operator": child_entry.get("operator"),
            "components": [build_component_tree(child, next_seen) for child in raw_children],
        }

    enriched: dict[str, dict[str, Any]] = {}
    for char, entry in merged_entries.items():
        components = entry.get("components", []) if isinstance(entry, dict) else []
        enriched[char] = {
            **entry,
            "component_tree": [
                build_component_tree(comp, frozenset({char})) for comp in components
            ],
        }
    return enriched
