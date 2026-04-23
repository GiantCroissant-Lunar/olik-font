"""`olik` CLI: fetch -> extract -> decompose -> compose -> emit / sync."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

import yaml

from olik_font.bulk.reuse import name_to_slug
from olik_font.compose.walk import compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.emit.library import library_to_dict
from olik_font.emit.record import build_glyph_record
from olik_font.emit.trace import trace_to_dict
from olik_font.prototypes.extract import extract_all_prototypes
from olik_font.prototypes.extraction_plan import load_extraction_plan
from olik_font.rules.engine import RuleSet, apply_first_match, load_rules
from olik_font.sources.makemeahanzi import (
    etymology as mmh_etymology,
)
from olik_font.sources.makemeahanzi import (
    fetch_mmh,
    load_mmh_dictionary,
    load_mmh_graphics,
)
from olik_font.sources.makemeahanzi import (
    radical as mmh_radical,
)
from olik_font.sources.unified import load_unified_lookup
from olik_font.styling import ComfyUIClient, stylize
from olik_font.types import PrototypeLibrary

_PY_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_MMH_DIR = _PY_ROOT / "data" / "mmh"
_DEFAULT_ANIMCJK_DIR = _PY_ROOT / "data" / "animcjk"
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

    db_sub.add_parser(
        "recompute-counts",
        help="recompute prototype productive_count values from uses edges",
    )

    ext = subparsers.add_parser("extract", help="bulk auto-extraction pipeline")
    ext_sub = ext.add_subparsers(dest="ext_cmd", required=True)

    ext_auto = ext_sub.add_parser("auto", help="pick random empty buckets and extract them")
    ext_auto.add_argument("--count", type=int, required=True)
    ext_auto.add_argument("--seed", type=int, default=42)
    ext_auto.add_argument("--iou-gate", type=float, default=0.90)
    ext_auto.add_argument("--dry-run", action="store_true")

    ext_sub.add_parser("report", help="print status breakdown")

    ext_back = ext_sub.add_parser(
        "backfill-status",
        help="set status on pre-Plan-09 rows",
    )
    ext_back.add_argument("--iou-gate", type=float, default=0.90)

    ext_list = ext_sub.add_parser("list", help="print chars in a status bucket")
    ext_list.add_argument(
        "--status",
        required=True,
        choices=["verified", "needs_review", "unsupported_op", "failed_extraction"],
    )
    ext_list.add_argument("--limit", type=int, default=50)

    ext_retry = ext_sub.add_parser("retry", help="re-extract chars in a status bucket")
    ext_retry.add_argument(
        "--status",
        required=True,
        choices=["unsupported_op", "needs_review", "failed_extraction"],
    )
    ext_retry.add_argument(
        "--chars",
        nargs="+",
        help="optional subset of chars to retry from the chosen status bucket",
    )
    ext_retry.add_argument("--iou-gate", type=float, default=0.90)
    style = subparsers.add_parser("style", help="batch stylize glyph records via ComfyUI")
    style.add_argument("chars", nargs="*")
    style.add_argument(
        "--all-verified",
        action="store_true",
        help="load every verified glyph from SurrealDB",
    )
    style.add_argument("--styles", required=True)
    style.add_argument("--seeds", type=int, default=1)
    style.add_argument("--max-concurrent", type=int, default=1)
    style.add_argument("--out", required=True, type=Path)

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
    lookup = load_unified_lookup(mmh_dir, _DEFAULT_ANIMCJK_DIR)
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
            inputs={"compose_source": "measured_transforms"},
            decision_id=f"d:{ch}:composition",
        )

        decomposition = lookup.char_decomposition_lookup(ch)
        tree = build_instance_tree(
            ch,
            plan,
            decomp_source={
                "char": ch,
                "adapter": decomposition.source if decomposition is not None else "extraction_plan",
                **({"confidence": decomposition.confidence} if decomposition is not None else {}),
            },
        )
        resolved, constraints = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
        records[ch] = build_glyph_record(
            ch,
            resolved,
            constraints,
            library,
            mmh_char=mmh_chars[ch],
            decomp_source=decomposition.source if decomposition is not None else "cjk-decomp",
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
        compute_productive_counts,
        upsert_glyph,
        upsert_has_kangxi,
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
        radical = mmh_radical(ch, dictionary=mmh_dict)
        glyph_etymology = mmh_etymology(ch, dictionary=mmh_dict)
        if radical is not None:
            kangxi_id = _kangxi_proto_id(radical)
            upsert_prototype(
                db,
                {
                    "id": kangxi_id,
                    "name": radical,
                    "source": "mmh:kangxi",
                },
            )
        upsert_glyph(db, _db_record(ch, rec, radical, glyph_etymology))
        if radical is not None:
            upsert_has_kangxi(db, ch, _kangxi_proto_id(radical))
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
    compute_productive_counts(db)
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


def _cmd_db_recompute_counts(_args: argparse.Namespace) -> int:
    from olik_font.sink.connection import connect
    from olik_font.sink.schema import ensure_schema
    from olik_font.sink.surrealdb import compute_productive_counts

    db = connect()
    ensure_schema(db)
    counts = compute_productive_counts(db)
    print(f"recomputed productive_count for {len(counts)} prototypes")
    for proto_id, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]:
        print(f"  {proto_id} {count}")
    return 0


def _cmd_db_export(args: argparse.Namespace) -> int:
    from olik_font.sink.connection import connect

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    db = connect()

    proto_rows = _query_rows(db.query("SELECT * FROM prototype;"))
    library = {
        "prototypes": {
            _record_key(row["id"], "prototype"): {
                k: _json_ready(v) for k, v in row.items() if k not in {"id"}
            }
            for row in proto_rows
        }
    }
    (out / "prototype-library.json").write_text(
        json.dumps(library, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    rule_rows = _query_rows(db.query("SELECT id, pattern, bucket, resolution FROM rule;"))
    (out / "rules.json").write_text(
        json.dumps(
            [
                {
                    **_json_ready(row),
                    "id": _record_key(row["id"], "rule"),
                }
                for row in rule_rows
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    glyph_rows = _query_rows(db.query("SELECT * FROM glyph;"))
    for g in glyph_rows:
        ch = g["char"]
        edges = _query_rows(
            db.query(
                "SELECT instance_id, position, placed_bbox, out AS prototype_ref "
                "FROM uses WHERE in = type::record('glyph', $char);",
                {"char": ch},
            )
        )
        export_row = {k: _json_ready(v) for k, v in g.items() if k not in {"id"}}
        export_row["component_instances"] = [
            {
                "id": e["instance_id"],
                "prototype_ref": _record_key(e["prototype_ref"], "prototype"),
                "position": e.get("position"),
                "placed_bbox": e.get("placed_bbox"),
            }
            for e in edges
        ]
        (out / f"glyph-record-{ch}.json").write_text(
            json.dumps(export_row, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    for g in glyph_rows:
        ch = g["char"]
        trace_rows = _query_rows(
            db.query(
                "SELECT rule, fired, order, alternative FROM rule_trace "
                "WHERE glyph = type::record('glyph', $char) ORDER BY order;",
                {"char": ch},
            )
        )
        simple = [
            {
                "rule_id": _record_key(t["rule"], "rule"),
                "fired": t["fired"],
                "order": t["order"],
                "alternative": t.get("alternative", False),
            }
            for t in trace_rows
        ]
        (out / f"rule-trace-{ch}.json").write_text(
            json.dumps(simple, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return 0


def _cmd_extract_auto(args: argparse.Namespace) -> int:
    from olik_font.bulk.batch import run_batch
    from olik_font.bulk.status import Status
    from olik_font.sink.connection import connect
    from olik_font.sink.schema import ensure_schema

    db = connect()
    ensure_schema(db)
    report = run_batch(
        db=db,
        count=args.count,
        seed=args.seed,
        iou_gate=args.iou_gate,
        dry_run=args.dry_run,
    )
    print(f"selected {report.selected} buckets (seed={report.seed})")
    for status in Status:
        print(f"  {status.value:20s} {report.counts[status]}")
    return 0


def _cmd_extract_report(_args: argparse.Namespace) -> int:
    from olik_font.bulk.charlist import load_moe_4808
    from olik_font.bulk.status import Status
    from olik_font.sink.connection import connect
    from olik_font.sink.schema import ensure_schema

    db = connect()
    ensure_schema(db)
    total_pool = len(load_moe_4808())
    filled_rows = _query_rows(db.query("SELECT count() AS count FROM glyph GROUP ALL;"))
    n_filled = int(filled_rows[0]["count"]) if filled_rows else 0
    print(f"filled {n_filled} / {total_pool}")

    grouped_rows = _query_rows(
        db.query("SELECT status, count() AS count FROM glyph GROUP BY status ORDER BY status;")
    )
    counts = {str(row.get("status") or ""): int(row.get("count", 0)) for row in grouped_rows}
    for status in Status:
        print(f"  {status.value:20s} {counts.get(status.value, 0)}")

    ops = _query_rows(
        db.query(
            "SELECT missing_op, count() AS count FROM glyph "
            "WHERE status = 'unsupported_op' GROUP BY missing_op;"
        )
    )
    if ops:
        print("unsupported-op histogram:")
        for row in ops:
            print(f"  {row['missing_op']:10s} {row['count']}")
    return 0


def _cmd_extract_backfill(args: argparse.Namespace) -> int:
    from olik_font.sink.connection import connect
    from olik_font.sink.schema import ensure_schema

    db = connect()
    ensure_schema(db)
    gate = args.iou_gate
    db.query(
        "UPDATE glyph SET status = 'verified' "
        "WHERE (status = NONE OR status = '') AND iou_mean >= $g;",
        {"g": gate},
    )
    db.query(
        "UPDATE glyph SET status = 'needs_review' "
        "WHERE (status = NONE OR status = '') AND iou_mean < $g AND iou_mean > 0;",
        {"g": gate},
    )
    return 0


def _cmd_extract_list(args: argparse.Namespace) -> int:
    from olik_font.sink.connection import connect
    from olik_font.sink.schema import ensure_schema

    db = connect()
    ensure_schema(db)
    rows = _query_rows(
        db.query(
            "SELECT char, iou_mean, missing_op, extraction_error "
            "FROM glyph WHERE status = $s ORDER BY char LIMIT $n;",
            {"s": args.status, "n": args.limit},
        )
    )
    for row in rows:
        extra = ""
        if args.status == "unsupported_op" and row.get("missing_op"):
            extra = f"  ({row['missing_op']})"
        elif args.status == "failed_extraction" and row.get("extraction_error"):
            extra = f"  ({row['extraction_error']})"
        elif args.status == "needs_review" and row.get("iou_mean") is not None:
            extra = f"  (iou={row['iou_mean']:.3f})"
        print(f"{row['char']}{extra}")
    return 0


def _cmd_extract_retry(args: argparse.Namespace) -> int:
    import olik_font.bulk.batch as batch_mod
    from olik_font.bulk import charlist as cl
    from olik_font.sink.connection import connect
    from olik_font.sink.schema import ensure_schema

    db = connect()
    ensure_schema(db)
    rows = _query_rows(
        db.query(
            "SELECT char FROM glyph WHERE status = $s;",
            {"s": args.status},
        )
    )
    chars = [row["char"] for row in rows]
    if args.chars:
        wanted = set(args.chars)
        chars = [char for char in chars if char in wanted]
    if not chars:
        print(f"no chars with status = {args.status}")
        return 0
    for ch in chars:
        db.query("DELETE FROM glyph WHERE char = $c;", {"c": ch})

    orig_pool = cl.load_moe_4808
    orig_batch_pool = batch_mod.load_moe_4808
    cl.load_moe_4808 = lambda path=None: chars
    batch_mod.load_moe_4808 = lambda path=None: chars
    try:
        report = batch_mod.run_batch(
            db=db,
            count=len(chars),
            seed=0,
            iou_gate=args.iou_gate,
        )
    finally:
        cl.load_moe_4808 = orig_pool
        batch_mod.load_moe_4808 = orig_batch_pool

    print(f"retried {report.selected} chars")
    for status, count in report.counts.items():
        print(f"  {status.value:20s} {count}")
    return 0


def _cmd_style(args: argparse.Namespace) -> int:
    if args.all_verified and args.chars:
        print("style accepts explicit chars or --all-verified, not both", file=sys.stderr)
        return 2
    if not args.all_verified and not args.chars:
        print("style requires one or more chars or --all-verified", file=sys.stderr)
        return 2

    glyph_records: dict[str, dict[str, Any]] | None = None
    chars = args.chars
    if args.all_verified:
        glyph_records = _load_verified_glyph_records()
        chars = list(glyph_records)
        if not chars:
            print("no verified glyphs found")
            return 0

    styles = [style.strip() for style in args.styles.split(",") if style.strip()]
    report = stylize(
        chars=chars,
        styles=styles,
        out_dir=args.out,
        seeds_per_style=args.seeds,
        client=ComfyUIClient(),
        glyph_records=glyph_records,
        max_concurrent=args.max_concurrent,
    )
    print(
        "styled "
        f"requested={report.requested} generated={report.generated} "
        f"skipped={report.skipped} failed={report.failed}"
    )
    return 0 if report.failed == 0 else 1


def _load_verified_glyph_records() -> dict[str, dict[str, Any]]:
    from olik_font.sink.connection import connect
    from olik_font.sink.schema import ensure_schema

    db = connect()
    ensure_schema(db)
    rows = _query_rows(db.query("SELECT * FROM glyph WHERE status = 'verified' ORDER BY char;"))
    return {
        row["char"]: {k: _json_ready(v) for k, v in row.items() if k != "id"}
        for row in rows
        if isinstance(row.get("char"), str)
    }


def _query_rows(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and "result" in payload[0]:
            return payload[0]["result"]
        return payload
    if isinstance(payload, dict):
        return payload["result"]
    raise TypeError(f"unexpected query payload: {type(payload)!r}")


def _record_key(value: object, table: str) -> str:
    if getattr(value, "table_name", None) == table and isinstance(getattr(value, "id", None), str):
        return value.id
    text = str(value)
    prefix = f"{table}:"
    if text.startswith(prefix):
        return text[len(prefix) :].removeprefix("⟨").removesuffix("⟩")
    return text


def _json_ready(value: object) -> object:
    table_name = getattr(value, "table_name", None)
    record_id = getattr(value, "id", None)
    if isinstance(table_name, str) and isinstance(record_id, str):
        return f"{table_name}:{record_id}"
    if isinstance(value, dict):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


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


def _db_record(
    char: str,
    record: dict[str, Any],
    radical: str | None,
    glyph_etymology: str | None,
) -> dict[str, Any]:
    iou_report = record.get("metadata", {}).get("iou_report", {})
    return {
        "char": char,
        "stroke_count": len(record.get("stroke_instances", [])),
        "radical": radical,
        "etymology": glyph_etymology,
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


def _kangxi_proto_id(radical: str) -> str:
    return f"proto:kangxi_{name_to_slug(radical)}"


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
        if args.db_cmd == "recompute-counts":
            return _cmd_db_recompute_counts(args)
    if args.cmd == "extract":
        if args.ext_cmd == "auto":
            return _cmd_extract_auto(args)
        if args.ext_cmd == "report":
            return _cmd_extract_report(args)
        if args.ext_cmd == "backfill-status":
            return _cmd_extract_backfill(args)
        if args.ext_cmd == "list":
            return _cmd_extract_list(args)
        if args.ext_cmd == "retry":
            return _cmd_extract_retry(args)
    if args.cmd == "style":
        return _cmd_style(args)
    print(f"unknown cmd: {args.cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
