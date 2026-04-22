#!/usr/bin/env python3
"""Demonstration — MMH `matches`-driven source_stroke_indices prefill.

Companion to `vault/plans/2026-04-22-borrow-mmh-matches-prefill.md` (Step 1).

Reads `project/py/data/mmh/{dictionary,graphics}.txt` (already fetched by the
main Python pipeline) and prints, for each seed character, how the MMH
`matches` field would auto-populate the `source_stroke_indices` field that
Plan 11 Task 2 adds to `GlyphNodePlan`.

Self-contained: does NOT import from `olik_font` — the Archon worktree for
Plan 11 owns those modules right now. The tiny JSONL loader below exists only
so this script is safe to run during the Plan 11 window.

Usage (from repo root):
    python vault/plans/2026-04-22-borrow-mmh-matches-prefill.py

Exits 0 on success; 1 if the MMH cache is missing.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

# --- Paths -------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
MMH_CACHE = REPO_ROOT / "project" / "py" / "data" / "mmh"
GRAPHICS = MMH_CACHE / "graphics.txt"
DICTIONARY = MMH_CACHE / "dictionary.txt"

# Plan 11 seed set.
SEEDS = ["明", "清", "國", "森"]


# --- Loaders -----------------------------------------------------------------


def load_jsonl_by_character(path: Path) -> dict[str, dict]:
    """Read a JSONL file keyed by the top-level `character` field."""
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            out[obj["character"]] = obj
    return out


# --- Core: group stroke indices by `matches` path ----------------------------


def group_indices_by_match_path(
    matches: list[list[int] | None],
) -> dict[tuple[int, ...], tuple[int, ...]]:
    """Group stroke indices by their full `matches` path.

    MMH's `matches` field, when present, is one entry per stroke — each entry
    a path (list of ints) down the decomposition tree to the component that
    owns that stroke. Grouping by path yields `{path → stroke_indices}`, which
    is exactly the `source_stroke_indices` assignment Plan 11 Task 2 needs.
    """
    grouped: dict[tuple[int, ...], list[int]] = defaultdict(list)
    for stroke_idx, path in enumerate(matches):
        if path is None:
            # Stroke belongs to the root / is unmatched. Bucket under ().
            grouped[()].append(stroke_idx)
        else:
            grouped[tuple(path)].append(stroke_idx)
    return {k: tuple(v) for k, v in grouped.items()}


def group_indices_by_top_level(
    matches: list[list[int] | None],
) -> dict[int | None, tuple[int, ...]]:
    """Coarser grouping — by the first step of the `matches` path.

    For a left-right char like 明, this usually splits strokes into "left
    component" vs "right component", which is the level the seed-set
    extraction_plan.yaml currently encodes.
    """
    grouped: dict[int | None, list[int]] = defaultdict(list)
    for stroke_idx, path in enumerate(matches):
        if path is None or not path:
            grouped[None].append(stroke_idx)
        else:
            grouped[path[0]].append(stroke_idx)
    return {k: tuple(v) for k, v in grouped.items()}


# --- Report ------------------------------------------------------------------


def report_char(ch: str, dict_entry: dict, graphics_entry: dict) -> None:
    print(f"=== {ch} ({dict_entry.get('definition', '?')}) ===")
    print(f"  decomposition : {dict_entry.get('decomposition')}")
    print(f"  radical       : {dict_entry.get('radical')}")

    strokes = graphics_entry.get("strokes", [])
    matches = dict_entry.get("matches")
    print(f"  stroke count  : {len(strokes)}")
    print(f"  matches       : {matches!r}")

    if matches is None:
        print("  (no `matches` field — cannot auto-prefill)\n")
        return

    by_top = group_indices_by_top_level(matches)
    print("  top-level groups (→ source_stroke_indices per level-1 instance):")
    for key in sorted(by_top, key=lambda k: (k is None, k)):
        print(f"    component[{key}] strokes={list(by_top[key])}")

    by_full = group_indices_by_match_path(matches)
    if any(len(path) > 1 for path in by_full):
        print("  full-path groups (→ source_stroke_indices for refined nodes):")
        for path in sorted(by_full, key=lambda p: (len(p), p)):
            print(f"    path={list(path) or '<root>'} strokes={list(by_full[path])}")
    print()


def main() -> int:
    if not GRAPHICS.exists() or not DICTIONARY.exists():
        print(
            f"MMH cache missing; expected {GRAPHICS} and {DICTIONARY}.\n"
            f"Run `python -m olik_font.sources.makemeahanzi` fetch (or the project CLI) first.",
            file=sys.stderr,
        )
        return 1

    graphics = load_jsonl_by_character(GRAPHICS)
    dictionary = load_jsonl_by_character(DICTIONARY)

    missing = [c for c in SEEDS if c not in graphics or c not in dictionary]
    if missing:
        print(f"Seed chars missing from MMH cache: {missing}", file=sys.stderr)
        return 1

    for ch in SEEDS:
        report_char(ch, dictionary[ch], graphics[ch])

    print(
        "Interpretation:\n"
        "  Each `top-level groups` line is what Plan 11 Task 2's\n"
        "  `source_stroke_indices` field on a level-1 `GlyphNodePlan` would\n"
        "  contain — derived automatically from MMH `matches` rather than\n"
        "  hand-authored in extraction_plan.yaml.\n"
        "  The `full-path groups` section shows the data available for\n"
        "  refined (depth >= 2) nodes, exercising 清's 青 → 生 + 月 case.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
