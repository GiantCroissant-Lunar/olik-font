"""`olik` CLI: fetch -> extract -> decompose -> compose -> emit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from olik_font.compose.walk import compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.emit.library import library_to_dict
from olik_font.emit.record import build_glyph_record
from olik_font.emit.trace import trace_to_dict
from olik_font.prototypes.extract import extract_all_prototypes
from olik_font.prototypes.extraction_plan import load_extraction_plan
from olik_font.rules.engine import apply_first_match, load_rules
from olik_font.sources.makemeahanzi import fetch_mmh, load_mmh_graphics
from olik_font.types import PrototypeLibrary

_PY_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_MMH_DIR = _PY_ROOT / "data" / "mmh"
_DEFAULT_PLAN = _PY_ROOT / "data" / "extraction_plan.yaml"
_DEFAULT_RULES = _PY_ROOT / "src" / "olik_font" / "rules" / "rules.yaml"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="olik")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    build = subparsers.add_parser("build", help="build glyph records for one or more characters")
    build.add_argument("chars", nargs="+", help="characters to build")
    build.add_argument("-o", "--out", required=True, type=Path, help="output dir")
    build.add_argument("--mmh-dir", default=_DEFAULT_MMH_DIR, type=Path, help="MMH cache dir")
    build.add_argument("--plan", default=_DEFAULT_PLAN, type=Path, help="extraction plan yaml")
    build.add_argument("--rules", default=_DEFAULT_RULES, type=Path, help="rules yaml")

    return parser.parse_args(argv)


def main() -> int:
    args = _parse_args(sys.argv[1:])
    if args.cmd != "build":
        print(f"unknown cmd: {args.cmd}", file=sys.stderr)
        return 2

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    graphics, _ = fetch_mmh(args.mmh_dir)
    mmh_chars = load_mmh_graphics(graphics)
    plan = load_extraction_plan(args.plan)
    rule_set = load_rules(args.rules)

    library = PrototypeLibrary()
    extract_all_prototypes(plan, mmh_chars, library)
    (out / "prototype-library.json").write_text(
        json.dumps(library_to_dict(library), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    rules_obj = yaml.safe_load(args.rules.read_text(encoding="utf-8"))
    (out / "rules.json").write_text(
        json.dumps(rules_obj, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    exit_code = 0
    for ch in args.chars:
        if ch not in plan.glyphs:
            print(f"error: character not in extraction plan: {ch}", file=sys.stderr)
            exit_code = 1
            continue
        if ch not in mmh_chars:
            print(f"error: character not in MMH: {ch}", file=sys.stderr)
            exit_code = 1
            continue

        decomp_trace = apply_first_match(
            bucket=rule_set.decomposition,
            inputs={"char_in_extraction_plan": True},
            decision_id=f"d:{ch}:decomposition",
        )
        compose_trace = apply_first_match(
            bucket=rule_set.composition,
            inputs={"has_preset_in_plan": True, "preset": plan.glyphs[ch].preset},
            decision_id=f"d:{ch}:composition",
        )

        tree = build_instance_tree(ch, plan)
        resolved, constraints = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
        record = build_glyph_record(ch, resolved, constraints, library, mmh_char=mmh_chars[ch])

        (out / f"glyph-record-{ch}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out / f"rule-trace-{ch}.json").write_text(
            json.dumps(
                {"decisions": [trace_to_dict(decomp_trace), trace_to_dict(compose_trace)]},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"wrote {ch}: record + trace")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
