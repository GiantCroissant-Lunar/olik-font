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

import requests


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


MMH_GRAPHICS_URL = (
    "https://raw.githubusercontent.com/skishore/makemeahanzi/master/graphics.txt"
)
MMH_DICTIONARY_URL = (
    "https://raw.githubusercontent.com/skishore/makemeahanzi/master/dictionary.txt"
)


def _http_get(url: str) -> bytes:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content


def fetch_mmh(cache_dir: Path) -> tuple[Path, Path]:
    """Ensure graphics.txt and dictionary.txt exist in cache_dir.

    Returns (graphics_path, dictionary_path). Downloads from upstream only when
    a target file is missing; re-running with a warm cache is a no-op.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    graphics = cache_dir / "graphics.txt"
    dictionary = cache_dir / "dictionary.txt"
    if not graphics.exists():
        graphics.write_bytes(_http_get(MMH_GRAPHICS_URL))
    if not dictionary.exists():
        dictionary.write_bytes(_http_get(MMH_DICTIONARY_URL))
    return graphics, dictionary
