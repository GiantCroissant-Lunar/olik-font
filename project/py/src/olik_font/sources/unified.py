"""Unified MMH + animCJK source lookup."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from olik_font.sources.animcjk import load_animcjk_dictionary, load_animcjk_graphics
from olik_font.sources.makemeahanzi import (
    MmhChar,
    MmhDictEntry,
    fetch_mmh,
    load_mmh_dictionary,
    load_mmh_graphics,
)

SourceMissLogger = Callable[[str, str], None]


@dataclass(frozen=True, slots=True)
class UnifiedLookup:
    mmh_graphics: dict[str, MmhChar]
    mmh_dictionary: dict[str, MmhDictEntry]
    animcjk_graphics: dict[str, MmhChar]
    animcjk_dictionary: dict[str, MmhDictEntry]
    on_miss: SourceMissLogger | None = None

    def char_graphics_lookup(self, char: str) -> MmhChar | None:
        entry = self.mmh_graphics.get(char)
        if entry is not None:
            return entry
        entry = self.animcjk_graphics.get(char)
        if entry is not None:
            return entry
        if self.on_miss is not None:
            self.on_miss("graphics", char)
        return None

    def char_dictionary_lookup(self, char: str) -> MmhDictEntry | None:
        entry = self.mmh_dictionary.get(char)
        if entry is not None:
            return entry
        entry = self.animcjk_dictionary.get(char)
        if entry is not None:
            return entry
        if self.on_miss is not None:
            self.on_miss("dictionary", char)
        return None

    def merged_graphics(self) -> dict[str, MmhChar]:
        return {**self.animcjk_graphics, **self.mmh_graphics}

    def merged_dictionary(self) -> dict[str, MmhDictEntry]:
        return {**self.animcjk_dictionary, **self.mmh_dictionary}


def load_unified_lookup(
    mmh_dir: Path,
    animcjk_dir: Path,
    *,
    on_miss: SourceMissLogger | None = None,
) -> UnifiedLookup:
    graphics_path, dictionary_path = fetch_mmh(mmh_dir)
    anim_graphics_path = animcjk_dir / "graphicsZhHant.txt"
    anim_dictionary_path = animcjk_dir / "dictionaryZhHant.txt"

    animcjk_graphics = (
        load_animcjk_graphics(anim_graphics_path) if anim_graphics_path.exists() else {}
    )
    animcjk_dictionary = (
        load_animcjk_dictionary(anim_dictionary_path) if anim_dictionary_path.exists() else {}
    )

    return UnifiedLookup(
        mmh_graphics=load_mmh_graphics(graphics_path),
        mmh_dictionary=load_mmh_dictionary(dictionary_path),
        animcjk_graphics=animcjk_graphics,
        animcjk_dictionary=animcjk_dictionary,
        on_miss=on_miss,
    )
