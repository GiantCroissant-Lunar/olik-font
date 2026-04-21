"""`olik` CLI: fetch -> extract -> decompose -> compose -> emit / sync."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

import yaml

from olik_font.compose.walk import compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.emit.library import library_to_dict
from olik_font.emit.record import build_glyph_record
from olik_font.emit.trace import trace_to_dict
from olik_font.prototypes.extract import extract_all_prototypes
from olik_font.prototypes.extraction_plan import load_extraction_plan
from olik_font.rules.engine import RuleSet, apply_first_match, load_rules
from olik_font.sources.makemeahanzi import fetch_mmh, load_mmh_dictionary, load_mmh_graphics
from olik_font.types import PrototypeLibrary

_PY_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_MMH_DIR = _PY_ROOT / "data" / "mmh"
_DEFAULT_PLAN = _PY_ROOT / "data" / "extraction_plan.yaml"
_DEFAULT_RULES = _PY_ROOT / "src" / "olik_font" / "rules" / "rules.yaml"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="olik")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    build = subparsers.add_parser("build", help="build glyph records for one or more characters")
    build.add_argument("chars", nargs="+")
    build.add_argument("-o", "--out", required=True, type=Path)
    build.add_argument("--mmh-dir", default=_DEFAULT_MMH_DIR, type=Path)
    build.add_argument("--plan", default=_DEFAULT_PLAN, type=Path)
    build.add_argument("--rules", default=_DEFAULT_RULES, type=Path)

    db = subparsers.add_parser("db", help="SurrealDB sink operations")
    db_sub = db.add_subparsers(dest="db_cmd", required=True)

    db_sync = db_sub.add_parser("sync", help="build + push records into SurrealDB")
    db_sync.add_argument("chars", nargs="+")
    db_sync.add_argument("--mmh-dir", default=_DEFAULT_MMH_DIR, type=Path)
    db_sync.add_argument("--plan", default=_DEFAULT_PLAN, type=Path)
    db_sync.add_argument("--rules", default=_DEFAULT_RULES, type=Path)

    db_reset = db_sub.add_parser("reset", help="drop + recreate the olik schema")
    db_reset.add_argument(
        "--yes",
        action="store_true",
        help="required - confirms you really want to drop data",
    )

    db_export = db_sub.add_parser("export", help="dump DB back to JSON")
    db_export.add_argument("--out", required=True, type=Path)

    return parser.parse_args(argv)


def _build_artifacts(
    chars: list[str],
    mmh_dir: Path,
    plan_path: Path,
    rules_path: Path,
) -> tuple[
    dict[str, dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, list[dict[str, Any]]]
]:
    """Produce build artifacts for the requested glyphs.

    Returns `(records_by_char, library_dict, raw_rules_doc, traces_by_char)`.
    Invalid characters are reported to stderr and omitted from the result maps.
    """
    graphics_path, _dictionary_path = fetch_mmh(mmh_dir)
    mmh_chars = load_mmh_graphics(graphics_path)
    plan = load_extraction_plan(plan_path)
    rules = load_rules(rules_path)
    rules_doc = yaml.safe_load(rules_path.read_text(encoding="utf-8"))

    library = PrototypeLibrary()
    extract_all_prototypes(plan, mmh_chars, library)

    records: dict[str, dict[str, Any]] = {}
    traces: dict[str, list[dict[str, Any]]] = {}
    for ch in chars:
        if ch not in plan.glyphs:
            print(f"error: character not in extraction plan: {ch}", file=sys.stderr)
            continue
        if ch not in mmh_chars:
            print(f"error: character not in MMH: {ch}", file=sys.stderr)
            continue

        decomp_trace = apply_first_match(
            bucket=rules.decomposition,
            inputs={"char_in_extraction_plan": True},
            decision_id=f"d:{ch}:decomposition",
        )
        compose_trace = apply_first_match(
            bucket=rules.composition,
            inputs={"has_preset_in_plan": True, "preset": plan.glyphs[ch].preset},
            decision_id=f"d:{ch}:composition",
        )

        tree = build_instance_tree(ch, plan)
        resolved, constraints = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
        records[ch] = build_glyph_record(
            ch,
            resolved,
            constraints,
            library,
            mmh_char=mmh_chars[ch],
        )
        traces[ch] = [trace_to_dict(decomp_trace), trace_to_dict(compose_trace)]

    return records, library_to_dict(library), rules_doc, traces


def _cmd_build(args: argparse.Namespace) -> int:
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    records, library, rules_doc, traces = _build_artifacts(
        args.chars,
        args.mmh_dir,
        args.plan,
        args.rules,
    )

    (out / "prototype-library.json").write_text(
        json.dumps(library, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "rules.json").write_text(
        json.dumps(rules_doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for ch, rec in records.items():
        (out / f"glyph-record-{ch}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (out / f"rule-trace-{ch}.json").write_text(
            json.dumps({"decisions": traces[ch]}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {ch}: record + trace")

    return 0 if len(records) == len(args.chars) else 1


def _cmd_db_sync(args: argparse.Namespace) -> int:
    from olik_font.sink.connection import connect
    from olik_font.sink.schema import ensure_schema
    from olik_font.sink.surrealdb import (
        upsert_glyph,
        upsert_prototype,
        upsert_rule_trace,
        upsert_rules,
    )

    records, library, _, traces = _build_artifacts(
        args.chars,
        args.mmh_dir,
        args.plan,
        args.rules,
    )
    _, dictionary_path = fetch_mmh(args.mmh_dir)
    mmh_dict = load_mmh_dictionary(dictionary_path)
    rule_set = load_rules(args.rules)

    db = connect()
    ensure_schema(db)

    for proto_id, proto in library.get("prototypes", {}).items():
        upsert_prototype(db, {"id": proto_id, **proto})

    upsert_rules(db, _rules_catalog(rule_set))

    for ch, rec in records.items():
        radical = mmh_dict.get(ch).radical if ch in mmh_dict else None
        upsert_glyph(db, _db_record(ch, rec, radical))
        upsert_rule_trace(db, ch, _db_trace(traces[ch]))

    db.query(
        "CREATE extraction_run CONTENT $data;",
        {
            "data": {
                "chars_processed": args.chars,
                "olik_version": _olik_version(),
                "mmh_dir": str(args.mmh_dir),
                "plan": str(args.plan),
                "host": platform.node(),
            }
        },
    )
    return 0 if len(records) == len(args.chars) else 1


def _cmd_db_reset(args: argparse.Namespace) -> int:
    from olik_font.sink.connection import DbConfig, connect
    from olik_font.sink.schema import ensure_schema

    if not args.yes:
        print("refusing to reset without --yes", file=sys.stderr)
        return 2

    cfg = DbConfig.from_env()
    if "127.0.0.1" not in cfg.url and "localhost" not in cfg.url:
        print(f"refusing to reset non-local DB ({cfg.url})", file=sys.stderr)
        return 2

    db = connect(cfg)
    db.query(f"REMOVE DATABASE {cfg.database};")
    db.query(f"DEFINE DATABASE {cfg.database};")
    db.use(cfg.namespace, cfg.database)
    ensure_schema(db)
    return 0


def _cmd_db_export(args: argparse.Namespace) -> int:
    raise NotImplementedError("db export - implemented in Task 6")


def _rules_catalog(rule_set: RuleSet) -> list[dict[str, str]]:
    catalog: list[dict[str, str]] = []
    for bucket_name in ("decomposition", "composition", "prototype_extraction"):
        for rule in getattr(rule_set, bucket_name):
            catalog.append(
                {
                    "id": rule.id,
                    "pattern": json.dumps(rule.when, ensure_ascii=False, sort_keys=True),
                    "bucket": bucket_name,
                    "resolution": _rule_resolution(rule.action),
                }
            )
    return catalog


def _rule_resolution(action: dict[str, Any]) -> str:
    for key in ("adapter", "mode", "source", "delegate", "carve"):
        if key in action:
            return str(action[key])
    return json.dumps(action, ensure_ascii=False, sort_keys=True)


def _db_record(char: str, record: dict[str, Any], radical: str | None) -> dict[str, Any]:
    iou_report = record.get("metadata", {}).get("iou_report", {})
    return {
        "char": char,
        "stroke_count": len(record.get("stroke_instances", [])),
        "radical": radical,
        "iou_mean": float(iou_report.get("mean", 0.0)),
        "iou_report": iou_report,
        **record,
    }


def _db_trace(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    order = 0
    for decision in decisions:
        rows.append(
            {
                "rule_id": decision["rule_id"],
                "fired": True,
                "order": order,
                "alternative": False,
            }
        )
        order += 1
        for alt in decision.get("alternatives", []):
            rows.append(
                {
                    "rule_id": alt["rule_id"],
                    "fired": False,
                    "order": order,
                    "alternative": True,
                }
            )
            order += 1
    return rows


def _olik_version() -> str:
    try:
        from importlib.metadata import version

        return version("olik-font")
    except Exception:
        return "unknown"


def main() -> int:
    args = _parse_args(sys.argv[1:])
    if args.cmd == "build":
        return _cmd_build(args)
    if args.cmd == "db":
        if args.db_cmd == "sync":
            return _cmd_db_sync(args)
        if args.db_cmd == "reset":
            return _cmd_db_reset(args)
        if args.db_cmd == "export":
            return _cmd_db_export(args)
    print(f"unknown cmd: {args.cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
