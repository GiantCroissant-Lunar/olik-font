"""Orchestrator: select buckets -> plan -> compose -> gate -> upsert."""

from __future__ import annotations

import json
import platform
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from olik_font.bulk import variant_match
from olik_font.bulk.charlist import load_moe_4808, select_buckets
from olik_font.bulk.planner import PlanFailed, PlanUnsupported, plan_char
from olik_font.bulk.reuse import ProtoIndex
from olik_font.bulk.status import Status
from olik_font.compose.walk import compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.emit.record import build_glyph_record
from olik_font.prototypes.extract import extract_all_prototypes
from olik_font.prototypes.extraction_plan import ExtractionPlan, PrototypePlan
from olik_font.sink.surrealdb import (
    upsert_glyph,
    upsert_glyph_stub,
    upsert_prototype,
    upsert_variant_of_edge,
)
from olik_font.sources.makemeahanzi import (
    fetch_mmh,
    load_mmh_dictionary,
    load_mmh_graphics,
)
from olik_font.types import BBox, PrototypeLibrary

_PY_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_MMH_DIR = _PY_ROOT / "data" / "mmh"
_DEFAULT_CJK = _PY_ROOT / "data" / "cjk-decomp.json"
_DEFAULT_RULES = _PY_ROOT / "src" / "olik_font" / "rules" / "rules.yaml"
_GLYPH_BBOX = (0.0, 0.0, 1024.0, 1024.0)


@dataclass
class BatchReport:
    seed: int
    iou_gate: float
    selected: int = 0
    selected_chars: list[str] = field(default_factory=list)
    counts: Counter[Status] = field(default_factory=Counter)
    variants_minted: int = 0
    canonical_probe_rejections: int = 0

    def add(self, status: Status) -> None:
        self.counts[status] += 1


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


def _load_cjk_entries(path: Path = _DEFAULT_CJK) -> dict[str, dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = raw.get("entries", {})

    def build_component_tree(component_char: str, seen: frozenset[str]) -> dict[str, Any]:
        if component_char in seen:
            return {"char": component_char, "components": []}

        child_entry = entries.get(component_char)
        raw_children = child_entry.get("components", []) if isinstance(child_entry, dict) else []
        if not isinstance(raw_children, list) or not raw_children:
            return {"char": component_char, "components": []}

        next_seen = seen | {component_char}
        return {
            "char": component_char,
            "operator": child_entry.get("operator"),
            "components": [build_component_tree(child, next_seen) for child in raw_children],
        }

    enriched: dict[str, dict[str, Any]] = {}
    for char, entry in entries.items():
        components = entry.get("components", []) if isinstance(entry, dict) else []
        enriched[char] = {
            **entry,
            "component_tree": [
                build_component_tree(comp, frozenset({char})) for comp in components
            ],
        }
    return enriched


def _proto_index_from_db(db) -> ProtoIndex:
    rows = _query_rows(db.query("SELECT * FROM prototype;"))
    plans: list[PrototypePlan] = []
    for row in rows:
        # `source` on a prototype row is stored as a dict under the Plan 03
        # emitter contract: {"kind": "mmh-extract", "from_char": "…",
        # "stroke_indices": [..]}. Top-level from_char / stroke_indices are
        # used when Plan 09 mints a canonical directly.
        raw_source = row.get("source")
        source_dict = raw_source if isinstance(raw_source, dict) else {}
        from_char = str(row.get("from_char") or source_dict.get("from_char") or "")
        stroke_indices = row.get("stroke_indices") or source_dict.get("stroke_indices") or ()
        plans.append(
            PrototypePlan(
                id=_record_key(row["id"], "prototype"),
                name=str(row.get("name", "")),
                from_char=from_char,
                stroke_indices=tuple(stroke_indices),
                roles=tuple(row.get("roles", ("meaning",))),
                anchors=row.get("anchors", {}),
            )
        )
    return ProtoIndex(prototypes=plans)


def _create_extraction_run(db, seed: int, iou_gate: float) -> str:
    rows = _query_rows(
        db.query(
            "CREATE extraction_run CONTENT $data;",
            {
                "data": {
                    "seed": seed,
                    "iou_gate": iou_gate,
                    "host": platform.node(),
                }
            },
        )
    )
    return _record_key(rows[0]["id"], "extraction_run")


def _finalize_extraction_run(db, run_id: str, report: BatchReport) -> None:
    db.query(
        "UPDATE type::record('extraction_run', $id) MERGE {"
        "  finished_at: time::now(),"
        "  counts: $counts,"
        "  chars_processed: $chars,"
        "  variants_minted: $variants,"
        "  canonical_probe_rejections: $rejections"
        "};",
        {
            "id": run_id,
            "counts": {
                **{status.value: report.counts[status] for status in Status},
                "variants_minted": report.variants_minted,
                "canonical_probe_rejections": report.canonical_probe_rejections,
            },
            "chars": report.selected_chars,
            "variants": report.variants_minted,
            "rejections": report.canonical_probe_rejections,
        },
    )


def _make_probe(
    mmh: dict[str, dict[str, Any]],
    proto_index: ProtoIndex,
) -> Callable[[str, str, BBox], float]:
    """Build a probe closure backed by the Hungarian matcher.

    Caller passes a measured `slot` (union bbox of the host's partition
    strokes). No preset vocabulary enters here.
    """

    def _strokes(entry: Any) -> list[str]:
        if isinstance(entry, dict):
            return list(entry["strokes"])
        return list(entry.strokes)

    def probe(
        component_char: str,
        context_char: str,
        slot: BBox,
    ) -> float:
        canonical = proto_index.canonical_for(component_char)
        if canonical is None or component_char not in mmh or context_char not in mmh:
            return 0.0
        canonical_strokes = _strokes(mmh[component_char])
        context_strokes = _strokes(mmh[context_char])
        match = variant_match.match_in_slot(canonical_strokes, context_strokes, slot)
        if match.k_gt_m or match.below_floor:
            return 0.0
        return match.mean_iou

    return probe


def _counting_probe(
    base_probe: Callable[[str, str, BBox], float],
    proto_index: ProtoIndex,
    gate: float,
    report: BatchReport,
) -> Callable[[str, str, BBox], float]:
    """Wrap a probe so run-level provenance captures canonical fallbacks."""

    def probe(
        component_char: str,
        context_char: str,
        slot: BBox,
    ) -> float:
        score = base_probe(component_char, context_char, slot)
        if proto_index.canonical_for(component_char) is not None and score < gate:
            report.canonical_probe_rejections += 1
        return score

    return probe


def _db_record(char: str, record: dict[str, Any], iou: float, run_id: str) -> dict[str, Any]:
    return {
        "char": char,
        "stroke_count": len(record.get("stroke_instances", [])),
        "iou_mean": iou,
        "iou_report": record.get("metadata", {}).get("iou_report", {}),
        **record,
        "extraction_run": run_id,
    }


def run_batch(
    db,
    count: int,
    seed: int,
    iou_gate: float,
    cap: int = 2,
    dry_run: bool = False,
    *,
    mmh_dir: Path = _DEFAULT_MMH_DIR,
    cjk_path: Path = _DEFAULT_CJK,
    rules_path: Path = _DEFAULT_RULES,
) -> BatchReport:
    del rules_path

    graphics_path, dictionary_path = fetch_mmh(mmh_dir)
    mmh = load_mmh_graphics(graphics_path)
    mmh_dict = load_mmh_dictionary(dictionary_path)
    cjk = _load_cjk_entries(cjk_path)

    pool = load_moe_4808()
    filled = {row["char"] for row in _query_rows(db.query("SELECT char FROM glyph;"))}
    buckets = select_buckets(pool, already_filled=filled, count=count, seed=seed)

    report = BatchReport(
        seed=seed,
        iou_gate=iou_gate,
        selected=len(buckets),
        selected_chars=list(buckets),
    )
    run_id: str | None = None
    if not dry_run and buckets:
        run_id = _create_extraction_run(db, seed, iou_gate)

    index = _proto_index_from_db(db)
    probe = _counting_probe(_make_probe(mmh, index), index, iou_gate, report)

    for ch in buckets:
        entry = cjk.get(ch)
        if entry is None:
            if not dry_run and run_id is not None:
                upsert_glyph_stub(
                    db,
                    ch,
                    Status.FAILED_EXTRACTION.value,
                    extraction_error="cjk-decomp entry missing",
                    extraction_run=run_id,
                )
            report.add(Status.FAILED_EXTRACTION)
            continue

        # planner.py needs standalone MMH entries for the char itself AND
        # for every component named in the cjk-decomp decomposition,
        # because canonical prototypes are extracted from the component's
        # own standalone entry (Plan 09.1 correctness fix).
        planner_mmh: dict[str, dict[str, Any]] = {}
        needed = [ch, *entry.get("components", [])]
        for key in needed:
            if isinstance(key, str) and key in mmh:
                planner_mmh[key] = {
                    "character": mmh[key].character,
                    "strokes": mmh[key].strokes,
                    "medians": mmh[key].medians,
                }

        host_dict = mmh_dict.get(ch)
        host_matches = host_dict.matches if host_dict is not None else None

        result = plan_char(
            char=ch,
            cjk_entry=entry,
            mmh=planner_mmh,
            matches=host_matches,
            index=index,
            probe_iou=probe,
            gate=iou_gate,
            cap=cap,
        )

        if isinstance(result, PlanUnsupported):
            if not dry_run and run_id is not None:
                upsert_glyph_stub(
                    db,
                    ch,
                    Status.UNSUPPORTED_OP.value,
                    missing_op=result.missing_op,
                    extraction_run=run_id,
                )
            report.add(Status.UNSUPPORTED_OP)
            continue

        if isinstance(result, PlanFailed):
            if not dry_run and run_id is not None:
                upsert_glyph_stub(
                    db,
                    ch,
                    Status.FAILED_EXTRACTION.value,
                    extraction_error=result.reason,
                    extraction_run=run_id,
                )
            report.add(Status.FAILED_EXTRACTION)
            continue

        report.variants_minted += len(result.variant_edges)

        synthetic = ExtractionPlan(
            schema_version="0.1",
            prototypes=tuple(index.prototypes) + tuple(result.new_prototypes),
            glyphs={ch: result.glyph_plan},
        )
        library = PrototypeLibrary()
        try:
            extract_all_prototypes(synthetic, mmh, library)
            tree = build_instance_tree(ch, synthetic)
            resolved, constraints = compose_transforms(tree, glyph_bbox=_GLYPH_BBOX)
            record = build_glyph_record(
                ch,
                resolved,
                constraints,
                library,
                mmh_char=mmh[ch],
            )
        except Exception as exc:
            if not dry_run and run_id is not None:
                upsert_glyph_stub(
                    db,
                    ch,
                    Status.FAILED_EXTRACTION.value,
                    extraction_error=f"{type(exc).__name__}: {exc}",
                    extraction_run=run_id,
                )
            report.add(Status.FAILED_EXTRACTION)
            continue

        iou = float(record.get("metadata", {}).get("iou_report", {}).get("mean") or 0.0)
        status = Status.VERIFIED if iou >= iou_gate else Status.NEEDS_REVIEW
        report.add(status)

        if not dry_run and run_id is not None:
            for proto in result.new_prototypes:
                upsert_prototype(
                    db,
                    {
                        "id": proto.id,
                        "name": proto.name,
                        "from_char": proto.from_char,
                        "source": f"extracted from {proto.from_char}",
                        "stroke_indices": list(proto.stroke_indices),
                        "roles": list(proto.roles),
                        "anchors": proto.anchors,
                    },
                )
            for variant_id, canonical_id in result.variant_edges:
                upsert_variant_of_edge(db, variant_id, canonical_id)

            db_record = _db_record(ch, record, iou, run_id)
            db_record["status"] = status.value
            upsert_glyph(db, db_record)

        index = ProtoIndex(prototypes=[*index.prototypes, *result.new_prototypes])
        probe = _counting_probe(_make_probe(mmh, index), index, iou_gate, report)

    if not dry_run and run_id is not None:
        _finalize_extraction_run(db, run_id, report)

    return report
