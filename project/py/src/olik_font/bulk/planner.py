"""Auto-plan a single character from its cjk-decomp entry + MMH data."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from olik_font.bulk import variant_match
from olik_font.bulk.ops import resolve_mode
from olik_font.bulk.reuse import ProtoIndex, decide_prototype
from olik_font.constraints.presets import slot_bbox
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
    MMH entry (Plan 09.1 correctness fix).

    Raises RuntimeError if `component_name` has no MMH entry.
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


def _extract_variant_prototype(
    component_name: str,
    context_char: str,
    proto_id: str,
    preset: str,
    n_components: int,
    slot_idx: int,
    mmh: dict,
) -> tuple[PrototypePlan, variant_match.MatchResult]:
    """Run Hungarian matching and mint a variant PrototypePlan.

    Returns (prototype, match). Caller inspects `match.k_gt_m` and
    `match.below_floor` to decide PlanFailed vs PlanOk.
    """
    canonical_strokes = mmh[component_name]["strokes"]
    context_strokes = mmh[context_char]["strokes"]
    slot = slot_bbox(preset, n_components, slot_idx)
    match = variant_match.match_in_slot(canonical_strokes, context_strokes, slot)
    if match.k_gt_m or match.below_floor:
        placeholder = PrototypePlan(
            id=proto_id,
            name=component_name,
            from_char=context_char,
            stroke_indices=(),
            roles=("meaning",),
            anchors={},
        )
        return placeholder, match
    indices = tuple(p.context_idx for p in match.pairs)
    variant = PrototypePlan(
        id=proto_id,
        name=component_name,
        from_char=context_char,
        stroke_indices=indices,
        roles=("meaning",),
        anchors={},
    )
    return variant, match


def plan_char(
    char: str,
    cjk_entry: dict,
    mmh: dict,
    index: ProtoIndex,
    probe_iou: Callable[[str, str, str, int, int], float],
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

    n = len(components)
    new_protos: list[PrototypePlan] = []
    variant_edges: list[tuple[str, str]] = []
    child_nodes: list[GlyphNodePlan] = []
    minted_variant_ids: set[str] = set()

    for i, comp_name in enumerate(components):
        decision = decide_prototype(
            component_char=comp_name,
            context_char=char,
            preset=mode,
            n_components=n,
            slot_idx=i,
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
            if decision.chosen_id in minted_variant_ids:
                pass
            else:
                if comp_name not in mmh:
                    return PlanFailed(reason=f"variant mint needs MMH entry for {comp_name}")
                variant, match = _extract_variant_prototype(
                    component_name=comp_name,
                    context_char=char,
                    proto_id=decision.chosen_id,
                    preset=mode,
                    n_components=n,
                    slot_idx=i,
                    mmh=mmh,
                )
                if match.k_gt_m:
                    return PlanFailed(
                        reason=(
                            f"k_gt_m: canonical {comp_name} has more strokes "
                            f"than context {char} offers"
                        )
                    )
                if match.below_floor:
                    return PlanFailed(
                        reason=(
                            f"match floor: best pairing for {comp_name} in "
                            f"{char} has min_iou={match.min_iou:.3f}"
                        )
                    )
                new_protos.append(variant)
                if decision.canonical_for_edge is not None:
                    variant_edges.append((variant.id, decision.canonical_for_edge))
                minted_variant_ids.add(decision.chosen_id)

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
