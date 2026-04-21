"""Auto-plan a single character from its cjk-decomp entry + MMH data."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from olik_font.bulk.ops import resolve_mode
from olik_font.bulk.reuse import ProtoIndex, decide_prototype
from olik_font.prototypes.extraction_plan import GlyphNodePlan, GlyphPlan, PrototypePlan


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


def _stroke_range_for_component(
    context_char: str,
    component_index: int,
    total_components: int,
    mmh_strokes: int,
) -> tuple[int, ...]:
    """Assign a naive contiguous MMH stroke slice to one component."""
    del context_char
    size = mmh_strokes // total_components
    start = component_index * size
    end = mmh_strokes if component_index == total_components - 1 else start + size
    return tuple(range(start, end))


def _extract_new_prototype(
    component_name: str,
    proto_id: str,
    context_char: str,
    index_in_context: int,
    total_components: int,
    mmh: dict,
) -> PrototypePlan:
    """Synthesize a prototype plan against the context char's MMH strokes."""
    mmh_entry = mmh.get(context_char)
    if mmh_entry is None:
        raise RuntimeError(f"missing MMH entry for {context_char}")
    stroke_count = len(mmh_entry["strokes"])
    strokes = _stroke_range_for_component(
        context_char,
        index_in_context,
        total_components,
        stroke_count,
    )
    return PrototypePlan(
        id=proto_id,
        name=component_name,
        from_char=context_char,
        stroke_indices=strokes,
        roles=("meaning",),
        anchors={},
    )


def plan_char(
    char: str,
    cjk_entry: dict,
    mmh: dict,
    index: ProtoIndex,
    probe_iou: Callable[[PrototypePlan], float],
    gate: float,
    cap: int,
) -> PlanResult:
    """Return a PlanResult for one char without touching the DB."""
    op = cjk_entry.get("operator", "")
    mode = resolve_mode(op)
    if mode is None:
        return PlanUnsupported(missing_op=op or "<empty>")

    if char not in mmh:
        return PlanFailed(reason=f"MMH missing {char}")

    components: list[str] = list(cjk_entry.get("components", []))
    if len(components) == 0:
        return PlanFailed(reason="cjk-decomp has no components")

    new_protos: list[PrototypePlan] = []
    variant_edges: list[tuple[str, str]] = []
    child_nodes: list[GlyphNodePlan] = []

    for i, comp_name in enumerate(components):
        decision = decide_prototype(
            component_char=comp_name,
            context_char=char,
            index=index,
            probe_iou=probe_iou,
            gate=gate,
            cap=cap,
        )
        if decision.cap_exceeded:
            return PlanFailed(reason=f"variant cap exceeded for {comp_name}")

        if decision.is_new_canonical:
            proto = _extract_new_prototype(
                comp_name,
                decision.chosen_id,
                char,
                i,
                len(components),
                mmh,
            )
            new_protos.append(proto)
        elif decision.is_new_variant:
            proto = _extract_new_prototype(
                comp_name,
                decision.chosen_id,
                char,
                i,
                len(components),
                mmh,
            )
            new_protos.append(proto)
            assert decision.canonical_for_edge is not None
            variant_edges.append((decision.chosen_id, decision.canonical_for_edge))

        child_nodes.append(GlyphNodePlan(prototype_ref=decision.chosen_id, mode="keep"))

    if mode == "repeat_triangle":
        proto_ref = child_nodes[0].prototype_ref
        glyph_plan = GlyphPlan(
            preset=mode,
            prototype_ref=proto_ref,
            count=len(components),
        )
    else:
        glyph_plan = GlyphPlan(preset=mode, children=tuple(child_nodes))

    return PlanOk(
        glyph_plan=glyph_plan,
        new_prototypes=new_protos,
        variant_edges=variant_edges,
    )
