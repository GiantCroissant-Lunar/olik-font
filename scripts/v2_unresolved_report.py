#!/usr/bin/env python3
# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY_ROOT = ROOT / "project" / "py"
if str(PY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PY_ROOT / "src"))

from olik_font.bulk.charlist import load_moe_4808
from olik_font.geom import bbox_of_paths
from olik_font.sink.connection import connect
from olik_font.sink.schema import ensure_schema
from olik_font.sources.unified import UnifiedLookup, load_unified_lookup

DEFAULT_OUT = ROOT / "vault" / "references" / "v2-unresolved.md"
DEFAULT_CJK = PY_ROOT / "data" / "cjk-decomp.json"
DEFAULT_MMH_DIR = PY_ROOT / "data" / "mmh"
DEFAULT_ANIMCJK_DIR = PY_ROOT / "data" / "animcjk"


@dataclass(frozen=True, slots=True)
class UnresolvedChar:
    char: str
    status: str
    reason: str
    iou_mean: float | None
    cjk_entry: dict[str, Any] | None
    geometry: str
    dictionary: str


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    db = connect()
    ensure_schema(db)
    lookup = load_unified_lookup(args.mmh_dir, args.animcjk_dir)
    cjk_entries = load_cjk_entries(args.cjk_path)
    pool = load_moe_4808(args.pool)
    unresolved = collect_unresolved(db, pool, lookup, cjk_entries)
    report = render_report(unresolved, pool, notes=args.note)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(args.out)
    print(f"unresolved {len(unresolved)} / {len(pool)}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pool", type=Path, default=None)
    parser.add_argument("--cjk-path", type=Path, default=DEFAULT_CJK)
    parser.add_argument("--mmh-dir", type=Path, default=DEFAULT_MMH_DIR)
    parser.add_argument("--animcjk-dir", type=Path, default=DEFAULT_ANIMCJK_DIR)
    parser.add_argument("--note", action="append", default=[])
    return parser.parse_args(argv)


def collect_unresolved(
    db,
    pool: list[str],
    lookup: UnifiedLookup,
    cjk_entries: dict[str, dict[str, Any]],
) -> list[UnresolvedChar]:
    rows = _query_rows(
        db.query(
            "SELECT char, status, iou_mean, missing_op, extraction_error FROM glyph ORDER BY char;"
        )
    )
    row_by_char = {str(row["char"]): row for row in rows if isinstance(row.get("char"), str)}

    unresolved: list[UnresolvedChar] = []
    for char in pool:
        row = row_by_char.get(char)
        if row is None:
            unresolved.append(
                UnresolvedChar(
                    char=char,
                    status="missing",
                    reason="no glyph row after bulk extract",
                    iou_mean=None,
                    cjk_entry=cjk_entries.get(char),
                    geometry=describe_geometry(char, lookup),
                    dictionary=describe_dictionary(char, lookup),
                )
            )
            continue

        status = str(row.get("status") or "")
        if status == "verified":
            continue
        unresolved.append(
            UnresolvedChar(
                char=char,
                status=status or "missing",
                reason=reason_for_row(row),
                iou_mean=_float_or_none(row.get("iou_mean")),
                cjk_entry=cjk_entries.get(char),
                geometry=describe_geometry(char, lookup),
                dictionary=describe_dictionary(char, lookup),
            )
        )
    return unresolved


def render_report(unresolved: list[UnresolvedChar], pool: list[str], *, notes: list[str]) -> str:
    counts = Counter(item.status for item in unresolved)
    lines = [
        "# v2 unresolved report",
        "",
        f"Pool size: {len(pool)}",
        f"Verified: {len(pool) - len(unresolved)}",
        f"Unresolved: {len(unresolved)}",
        "",
        "## Status counts",
        "",
    ]
    if counts:
        for status, count in sorted(counts.items()):
            lines.append(f"- `{status}`: {count}")
    else:
        lines.append("- none")

    if notes:
        lines.extend(["", "## Notes", ""])
        for note in notes:
            lines.append(f"- {note}")

    lines.extend(["", "## Per-char detail", ""])
    if not unresolved:
        lines.append("All pool chars are verified.")
        return "\n".join(lines) + "\n"

    for item in unresolved:
        lines.extend(
            [
                f"### {item.char}",
                "",
                f"- Status: `{item.status}`",
                f"- Reason: {item.reason}",
                f"- Geometry sample: {item.geometry}",
                f"- Dictionary sample: {item.dictionary}",
            ]
        )
        if item.iou_mean is not None:
            lines.append(f"- IoU mean: {item.iou_mean:.3f}")
        lines.extend(["- cjk-decomp entry:", "", "```json"])
        lines.append(json.dumps(item.cjk_entry, ensure_ascii=False, indent=2))
        lines.extend(["```", ""])
    return "\n".join(lines)


def reason_for_row(row: dict[str, Any]) -> str:
    status = str(row.get("status") or "missing")
    if status == "needs_review":
        iou = _float_or_none(row.get("iou_mean"))
        if iou is None:
            return "needs review"
        return f"iou_mean={iou:.3f} below verification gate"
    if status == "unsupported_op":
        missing_op = row.get("missing_op")
        return f"unsupported operator {missing_op!r}" if missing_op else "unsupported operator"
    if status == "failed_extraction":
        error = row.get("extraction_error")
        return str(error) if error else "failed extraction"
    return status


def describe_geometry(char: str, lookup: UnifiedLookup) -> str:
    entry = lookup.mmh_graphics.get(char)
    source = "mmh"
    if entry is None:
        entry = lookup.animcjk_graphics.get(char)
        source = "animcjk"
    if entry is None:
        return "no graphics entry in mmh or animcjk"
    bbox = tuple(round(value, 2) for value in bbox_of_paths(entry.strokes))
    return f"source={source} strokes={len(entry.strokes)} bbox={bbox}"


def describe_dictionary(char: str, lookup: UnifiedLookup) -> str:
    entry = lookup.mmh_dictionary.get(char)
    source = "mmh"
    if entry is None:
        entry = lookup.animcjk_dictionary.get(char)
        source = "animcjk"
    if entry is None:
        return "no dictionary entry in mmh or animcjk"
    matches = len(entry.matches)
    return (
        f"source={source} decomposition={entry.decomposition!r} "
        f"radical={entry.radical!r} matches={matches}"
    )


def load_cjk_entries(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries", {})
    if not isinstance(entries, dict):
        raise ValueError(f"invalid cjk payload: {path}")
    return {char: entry for char, entry in entries.items() if isinstance(entry, dict)}


def _float_or_none(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _query_rows(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and "result" in payload[0]:
            return payload[0]["result"]
        return payload
    if isinstance(payload, dict):
        return payload["result"]
    raise TypeError(f"unexpected query payload: {type(payload)!r}")


if __name__ == "__main__":
    raise SystemExit(main())
