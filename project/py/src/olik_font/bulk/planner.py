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


def _extract_canonical_prototype(
    component_name: str,
    proto_id: str,
    mmh: dict,
) -> PrototypePlan:
    """Extract a canonical prototype from the component's OWN standalone
    MMH entry.

    This is the correctness-critical step: a prototype meant to represent
    the component `component_name` must derive its strokes from MMH's
    standalone entry for `component_name`, not from some context char's
    strokes. MMH's `matches` field (which could have told us which
    strokes of a context char belong to which component) is uniformly
    null across all 9574 entries, so standalone extraction is the only
    reliable path.

    Raises RuntimeError if `component_name` has no MMH entry — the
    caller converts this to `PlanFailed`, leaving the glyph as a stub
    row rather than composing it with wrong stroke data.
    """
    mmh_entry = mmh.get(component_name)
    if mmh_entry is None:
        raise RuntimeError(f"no standalone MMH entry for component '{component_name}'")
    stroke_count = len(mmh_entry["strokes"])
    return PrototypePlan(
        id=proto_id,
        name=component_name,
        from_char=component_name,
        stroke_indices=tuple(range(stroke_count)),
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

    for _i, comp_name in enumerate(components):
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
            try:
                proto = _extract_canonical_prototype(comp_name, decision.chosen_id, mmh)
            except RuntimeError as exc:
                return PlanFailed(reason=str(exc))
            new_protos.append(proto)
        elif decision.is_new_variant:
            # Correct variant extraction needs MMH's `matches` field
            # (per-stroke component assignment) — which is null for all
            # 9574 MMH entries. Without it we have no reliable way to
            # isolate a component's strokes inside a context char. Rather
            # than mint a variant with wrong strokes, fail out and let
            # the glyph land in `needs_review`; a later plan can add
            # IoU-per-stroke matching for proper variant extraction.
            return PlanFailed(
                reason=(
                    f"canonical proto for {comp_name} fails IoU and MMH "
                    "lacks per-stroke matches for variant extraction"
                )
            )

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
