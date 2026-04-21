# project/py/src/olik_font/sources/makemeahanzi.py
"""Make Me a Hanzi (MMH) source adapter.

Parses graphics.txt (JSONL) and dictionary.txt (JSONL) into typed records.
Both files are fetched into project/py/data/ by fetch_mmh(); loaders are
pure functions over the on-disk files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MmhChar:
    character: str
    strokes: list[str]
    medians: list[list[list[int]]]


@dataclass(frozen=True, slots=True)
class MmhDictEntry:
    character: str
    definition: str | None
    pinyin: list[str] = field(default_factory=list)
    decomposition: str | None = None
    radical: str | None = None
    matches: list[list[int] | None] = field(default_factory=list)


def load_mmh_graphics(path: Path) -> dict[str, MmhChar]:
    """Parse a graphics.txt-style JSONL file into a char → MmhChar map."""
    out: dict[str, MmhChar] = {}
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
            out[ch] = MmhChar(
                character=ch,
                strokes=list(obj["strokes"]),
                medians=[list(m) for m in obj["medians"]],
            )
    return out


def load_mmh_dictionary(path: Path) -> dict[str, MmhDictEntry]:
    """Parse a dictionary.txt-style JSONL file into a char → MmhDictEntry map."""
    out: dict[str, MmhDictEntry] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            ch = obj["character"]
            out[ch] = MmhDictEntry(
                character=ch,
                definition=obj.get("definition"),
                pinyin=list(obj.get("pinyin", [])),
                decomposition=obj.get("decomposition"),
                radical=obj.get("radical"),
                matches=list(obj.get("matches", [])),
            )
    return out
