"""animCJK source adapter.

Parses animCJK's `graphicsZhHant.txt` and `dictionaryZhHant.txt` snapshot
into the same `MmhChar` / `MmhDictEntry` dataclasses used for MMH.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from olik_font.sources.makemeahanzi import MmhDictEntry, load_mmh_graphics

_IDC_ARITY = {
    "⿰": 2,
    "⿱": 2,
    "⿲": 3,
    "⿳": 3,
    "⿴": 2,
    "⿵": 2,
    "⿶": 2,
    "⿷": 2,
    "⿸": 2,
    "⿹": 2,
    "⿺": 2,
    "⿻": 2,
}


@dataclass(frozen=True, slots=True)
class _AcjkNode:
    label: str | None
    split: bool
    stroke_count: int | None = None
    children: tuple[_AcjkNode, ...] = ()


def load_animcjk_graphics(path: Path):
    """Parse animCJK graphics JSONL into the MMH `MmhChar` shape."""
    return load_mmh_graphics(path)


def _parse_int(text: str, pos: int) -> tuple[int, int]:
    start = pos
    while pos < len(text) and text[pos].isdigit():
        pos += 1
    if pos == start:
        raise ValueError(f"expected stroke count at offset {start}")
    return int(text[start:pos]), pos


def _parse_node(text: str, pos: int) -> tuple[_AcjkNode, int]:
    label: str | None = None
    split = False

    if pos < len(text) and text[pos] not in _IDC_ARITY and not text[pos].isdigit():
        label = text[pos]
        pos += 1
        while pos < len(text) and text[pos] in ".:":
            if text[pos] == ":":
                split = True
            pos += 1

    if pos >= len(text):
        raise ValueError("unexpected end of acjk decomposition")

    token = text[pos]
    if token.isdigit():
        stroke_count, pos = _parse_int(text, pos)
        return _AcjkNode(label=label, split=split, stroke_count=stroke_count), pos

    if token not in _IDC_ARITY:
        raise ValueError(f"unexpected acjk token {token!r} at offset {pos}")

    pos += 1
    children: list[_AcjkNode] = []
    for _ in range(_IDC_ARITY[token]):
        child, pos = _parse_node(text, pos)
        children.append(child)
    return _AcjkNode(label=label, split=split, children=tuple(children)), pos


def _paths_for_node(node: _AcjkNode, path: tuple[int, ...]) -> list[list[int]]:
    if node.stroke_count is not None:
        return [list(path) for _ in range(node.stroke_count)]

    shared_slots: dict[str, int] = {}
    next_slot = 0
    matches: list[list[int]] = []
    for child in node.children:
        if child.split and child.label is not None:
            slot = shared_slots.setdefault(child.label, next_slot)
            if slot == next_slot:
                next_slot += 1
        else:
            slot = next_slot
            next_slot += 1
        matches.extend(_paths_for_node(child, (*path, slot)))
    return matches


def _matches_from_acjk(acjk: str | None) -> list[list[int] | None]:
    if not acjk:
        return []
    node, pos = _parse_node(acjk, 0)
    if pos != len(acjk):
        raise ValueError(f"unexpected trailing acjk content at offset {pos}")
    return _paths_for_node(node, ())


def load_animcjk_dictionary(path: Path) -> dict[str, MmhDictEntry]:
    """Parse animCJK dictionary JSONL into the MMH `MmhDictEntry` shape."""
    out: dict[str, MmhDictEntry] = {}
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            ch = obj["character"]
            try:
                matches = _matches_from_acjk(obj.get("acjk"))
            except ValueError:
                # animCJK split/share notation is richer than the subset we
                # need for current fallback coverage. Keep the row loadable and
                # use measured matches where the acjk string is simple enough
                # to translate directly.
                matches = []
            out[ch] = MmhDictEntry(
                character=ch,
                definition=obj.get("definition"),
                pinyin=list(obj.get("pinyin", [])),
                decomposition=obj.get("decomposition"),
                radical=obj.get("radical"),
                etymology=None,
                matches=matches,
            )
    return out
