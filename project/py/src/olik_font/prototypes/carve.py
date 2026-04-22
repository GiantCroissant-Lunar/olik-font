"""Carve missing component graphics from containing hosts via measured matches."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from olik_font.sources.makemeahanzi import MmhChar

GraphicsLookup = Callable[[str], MmhChar | dict[str, Any] | None]
DictionaryLookup = Callable[[str], Any | None]

_PY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CARVED_COMPONENTS = _PY_ROOT / "data" / "carved_components.json"


def load_carved_components(path: Path = DEFAULT_CARVED_COMPONENTS) -> dict[str, MmhChar]:
    """Load the carved-component cache into the MMH graphics shape."""
    if not path.exists():
        return {}

    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = raw.get("components", raw)
    if not isinstance(entries, dict):
        return {}

    out: dict[str, MmhChar] = {}
    for char, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        strokes = entry.get("strokes")
        medians = entry.get("medians")
        if not isinstance(strokes, list) or not isinstance(medians, list):
            continue
        out[char] = MmhChar(
            character=str(entry.get("character") or char),
            strokes=[str(stroke) for stroke in strokes],
            medians=[
                [
                    [int(point[0]), int(point[1])]
                    for point in median
                    if isinstance(point, list) and len(point) == 2
                ]
                for median in medians
                if isinstance(median, list)
            ],
        )
    return out


def carve_component(
    component_name: str,
    cjk_entries: dict[str, dict[str, Any]],
    *,
    graphics_lookup: GraphicsLookup,
    dictionary_lookup: DictionaryLookup,
    cache_path: Path = DEFAULT_CARVED_COMPONENTS,
) -> MmhChar:
    cached = load_carved_components(cache_path).get(component_name)
    if cached is not None:
        return cached

    candidates: list[tuple[int, str, tuple[int, ...], MmhChar, tuple[int, ...]]] = []
    for host_char in sorted(cjk_entries):
        if host_char == component_name:
            continue
        host_path = _find_component_path_in_entry(component_name, host_char, cjk_entries)
        if host_path is None:
            continue

        host_graphics = _coerce_graphics(graphics_lookup(host_char))
        if host_graphics is None:
            continue

        host_dict = dictionary_lookup(host_char)
        host_matches = _matches_of(host_dict)
        stroke_indices = _stroke_indices_for_path(host_matches, host_path)
        if not stroke_indices:
            continue

        candidates.append((len(host_path), host_char, host_path, host_graphics, stroke_indices))

    if not candidates:
        raise RuntimeError(
            f"no containing host with measured matches for component '{component_name}'"
        )

    _depth, host_char, host_path, host_graphics, stroke_indices = min(
        candidates,
        key=lambda item: (item[0], item[1]),
    )
    carved = MmhChar(
        character=component_name,
        strokes=[host_graphics.strokes[i] for i in stroke_indices],
        medians=[host_graphics.medians[i] for i in stroke_indices],
    )
    _write_cached_component(
        cache_path,
        component_name,
        carved,
        host_char=host_char,
        host_path=host_path,
        stroke_indices=stroke_indices,
    )
    return carved


def _write_cached_component(
    path: Path,
    component_name: str,
    carved: MmhChar,
    *,
    host_char: str,
    host_path: tuple[int, ...],
    stroke_indices: tuple[int, ...],
) -> None:
    raw: dict[str, Any]
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raw = {}
    else:
        raw = {}

    components = raw.get("components")
    if not isinstance(components, dict):
        components = {}
        raw["components"] = components

    components[component_name] = {
        "character": carved.character,
        "strokes": list(carved.strokes),
        "medians": carved.medians,
        "source": {
            "host_char": host_char,
            "path": list(host_path),
            "stroke_indices": list(stroke_indices),
        },
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _coerce_graphics(entry: MmhChar | dict[str, Any] | None) -> MmhChar | None:
    if entry is None:
        return None
    if isinstance(entry, MmhChar):
        return entry
    strokes = entry.get("strokes")
    medians = entry.get("medians")
    if not isinstance(strokes, list) or not isinstance(medians, list):
        return None
    return MmhChar(
        character=str(entry.get("character") or ""),
        strokes=[str(stroke) for stroke in strokes],
        medians=[list(median) for median in medians],
    )


def _matches_of(entry: Any) -> list[list[int] | None] | None:
    if entry is None:
        return None
    matches = entry.get("matches") if isinstance(entry, dict) else getattr(entry, "matches", None)
    if not isinstance(matches, list):
        return None
    out: list[list[int] | None] = []
    for assignment in matches:
        if assignment is None:
            out.append(None)
            continue
        if not isinstance(assignment, list):
            out.append(None)
            continue
        out.append([int(part) for part in assignment])
    return out


def _stroke_indices_for_path(
    matches: list[list[int] | None] | None,
    path: tuple[int, ...],
) -> tuple[int, ...]:
    if not matches or not path:
        return ()

    out = [
        stroke_idx
        for stroke_idx, assignment in enumerate(matches)
        if assignment is not None
        and len(assignment) >= len(path)
        and tuple(int(part) for part in assignment[: len(path)]) == path
    ]
    return tuple(out)


def _find_component_path_in_entry(
    component_name: str,
    host_char: str,
    cjk_entries: dict[str, dict[str, Any]],
) -> tuple[int, ...] | None:
    tree = _component_tree_for_char(host_char, cjk_entries, seen=frozenset({host_char}))
    return _find_component_path(component_name, tree, ())


def _component_tree_for_char(
    char: str,
    cjk_entries: dict[str, dict[str, Any]],
    *,
    seen: frozenset[str],
) -> list[dict[str, Any]]:
    entry = cjk_entries.get(char)
    if not isinstance(entry, dict):
        return []

    existing_tree = entry.get("component_tree")
    if isinstance(existing_tree, list):
        return [node for node in existing_tree if isinstance(node, dict)]

    raw_components = entry.get("components")
    if not isinstance(raw_components, list):
        return []

    next_seen = seen | {char}
    tree: list[dict[str, Any]] = []
    for component in raw_components:
        component_char = str(component)
        if component_char in next_seen:
            tree.append({"char": component_char, "components": []})
            continue
        tree.append(
            {
                "char": component_char,
                "components": _component_tree_for_char(
                    component_char,
                    cjk_entries,
                    seen=next_seen,
                ),
            }
        )
    return tree


def _find_component_path(
    component_name: str,
    nodes: list[dict[str, Any]],
    path: tuple[int, ...],
) -> tuple[int, ...] | None:
    for idx, node in enumerate(nodes):
        node_path = (*path, idx)
        node_char = str(node.get("char") or "")
        if node_char == component_name:
            return node_path
        children = node.get("components")
        if not isinstance(children, list):
            continue
        child_path = _find_component_path(
            component_name,
            [child for child in children if isinstance(child, dict)],
            node_path,
        )
        if child_path is not None:
            return child_path
    return None
