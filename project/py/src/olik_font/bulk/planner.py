"""Auto-plan a single character from its cjk-decomp entry + MMH data.

Placement comes from MMH's `matches` partition, not from any preset
vocabulary. For each top-level component the planner reads the stroke
indices the partition assigns to it, measures the union bbox of those
strokes (that is the slot), and emits a GlyphNodePlan carrying
`source_stroke_indices` directly. Compose later reads those indices
and derives the affine transform via `measure_instance_transform`.

The Hungarian matcher in `variant_match.py` is used only as an IoU
probe to decide canonical-reuse vs. variant-extraction; both sides of
that probe are measured (the canonical against the partitioned slot).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from olik_font.bulk import variant_match
from olik_font.bulk.mmh_partition import top_level_partition
from olik_font.bulk.reuse import ProtoIndex, decide_prototype
from olik_font.geom import bbox_of_paths, union_bbox
from olik_font.prototypes.extraction_plan import GlyphNodePlan, GlyphPlan, PrototypePlan
from olik_font.types import BBox


@dataclass(frozen=True)
class PlanOk:
    glyph_plan: GlyphPlan
    new_prototypes: list[PrototypePlan]
    variant_edges: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class PlanUnsupported:
    missing_op: str


@dataclass(frozen=True)
class PlanFailed:
    reason: str


PlanResult = PlanOk | PlanUnsupported | PlanFailed


def _extract_canonical_prototype(
    component_name: str,
    proto_id: str,
    mmh: dict,
) -> PrototypePlan:
    """Extract a canonical prototype from the component's OWN standalone
    MMH entry (Plan 09.1 correctness fix).
    """
    mmh_entry = mmh.get(component_name)
    if mmh_entry is None:
        raise RuntimeError(f"no standalone MMH entry for component '{component_name}'")
    stroke_count = len(_strokes_of(mmh_entry))
    return PrototypePlan(
        id=proto_id,
        name=component_name,
        from_char=component_name,
        stroke_indices=tuple(range(stroke_count)),
        roles=("meaning",),
        anchors={},
    )


def _extract_variant_prototype(
    component_name: str,
    context_char: str,
    proto_id: str,
    partition_indices: tuple[int, ...],
    context_strokes: list[str],
    slot: BBox,
    mmh: dict,
) -> tuple[PrototypePlan, variant_match.MatchResult]:
    """Mint a variant prototype using the MMH partition's own indices."""
    canonical_strokes = _strokes_of(mmh[component_name])
    partitioned_strokes = [context_strokes[i] for i in partition_indices]
    match = variant_match.match_in_slot(canonical_strokes, partitioned_strokes, slot)
    variant = PrototypePlan(
        id=proto_id,
        name=component_name,
        from_char=context_char,
        stroke_indices=tuple(partition_indices),
        roles=("meaning",),
        anchors={},
    )
    return variant, match


def _strokes_of(mmh_entry) -> list[str]:
    if isinstance(mmh_entry, dict):
        return list(mmh_entry["strokes"])
    return list(mmh_entry.strokes)


def _measure_slot(host_strokes: list[str], indices: tuple[int, ...]) -> BBox:
    if not indices:
        return (0.0, 0.0, 0.0, 0.0)
    return union_bbox(tuple(bbox_of_paths([host_strokes[i]]) for i in indices))


def plan_char(
    char: str,
    cjk_entry: dict,
    mmh: dict,
    matches: list[list[int] | None] | None,
    index: ProtoIndex,
    probe_iou: Callable[[str, str, BBox], float],
    gate: float,
    cap: int,
) -> PlanResult:
    """Return a PlanResult for one char without touching the DB.

    `matches` is the host char's MMH `matches` field (from dictionary.txt).
    Without it the planner cannot measure per-component slots and the
    char is returned as PlanFailed — caller can retry later when MMH
    coverage expands.
    """
    # Measured placement doesn't need an op whitelist: the MMH `matches`
    # partition IS the placement authority. The operator name stays as
    # metadata on the plan so downstream can surface structural intent,
    # but it does not gate planning. PlanUnsupported is reserved for the
    # narrow case where cjk-decomp itself has nothing to offer.
    if char not in mmh:
        return PlanFailed(reason=f"MMH missing {char}")

    components: list[str] = list(cjk_entry.get("components", []))
    if len(components) == 0:
        return PlanUnsupported(missing_op=cjk_entry.get("operator", "") or "<empty>")

    partition = top_level_partition(matches)
    if partition is None or len(partition) != len(components):
        return PlanFailed(reason=f"MMH partition shape mismatch for {char}: {partition}")

    host_strokes = _strokes_of(mmh[char])
    new_protos: list[PrototypePlan] = []
    variant_edges: list[tuple[str, str]] = []
    child_nodes: list[GlyphNodePlan] = []
    minted_variant_ids: set[str] = set()

    for i, comp_name in enumerate(components):
        partition_indices = tuple(partition[i])
        slot = _measure_slot(host_strokes, partition_indices)

        decision = decide_prototype(
            component_char=comp_name,
            context_char=char,
            slot=slot,
            index=index,
            probe_iou=probe_iou,
            gate=gate,
            cap=cap,
        )
        if decision.cap_exceeded:
            return PlanFailed(reason=f"variant cap exceeded for {comp_name}")

        if decision.is_new_canonical:
            try:
                proto = _extract_canonical_prototype(comp_name, decision.chosen_id, mmh)
            except RuntimeError as exc:
                return PlanFailed(reason=str(exc))
            new_protos.append(proto)
        elif decision.is_new_variant and decision.chosen_id not in minted_variant_ids:
            if comp_name not in mmh:
                return PlanFailed(reason=f"variant mint needs MMH entry for {comp_name}")
            variant, _match = _extract_variant_prototype(
                component_name=comp_name,
                context_char=char,
                proto_id=decision.chosen_id,
                partition_indices=partition_indices,
                context_strokes=host_strokes,
                slot=slot,
                mmh=mmh,
            )
            new_protos.append(variant)
            if decision.canonical_for_edge is not None:
                variant_edges.append((variant.id, decision.canonical_for_edge))
            minted_variant_ids.add(decision.chosen_id)

        child_nodes.append(
            GlyphNodePlan(
                prototype_ref=decision.chosen_id,
                mode="keep",
                source_stroke_indices=partition_indices,
            )
        )

    glyph_plan = GlyphPlan(children=tuple(child_nodes))
    return PlanOk(
        glyph_plan=glyph_plan,
        new_prototypes=new_protos,
        variant_edges=variant_edges,
    )
