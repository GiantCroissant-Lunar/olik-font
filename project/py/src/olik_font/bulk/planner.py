"""Auto-plan a single character from its cjk-decomp entry + MMH data.

Placement comes from MMH's `matches` partition, not from any preset
vocabulary. For each component instance the planner reads the measured
stroke indices from MMH, carries them on the GlyphNodePlan, and emits
`mode="refine"` subtrees when MMH exposes nested component partitions.

The Hungarian matcher in `variant_match.py` is used only as an IoU
probe to decide canonical-reuse vs. variant-extraction; both sides of
that probe are measured (the canonical against the partitioned slot).
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from olik_font.bulk import variant_match
from olik_font.bulk.mmh_partition import nested_partition, top_level_partition
from olik_font.bulk.reuse import ProtoIndex, VariantCap, decide_prototype, name_to_slug
from olik_font.geom import bbox_of_paths, union_bbox
from olik_font.prototypes.carve import DEFAULT_CARVED_COMPONENTS, carve_component
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
    *,
    cjk_entries: dict[str, dict[str, Any]] | None = None,
    graphics_lookup: Callable[[str], Any | None] | None = None,
    dictionary_lookup: Callable[[str], Any | None] | None = None,
    carved_cache_path: Path = DEFAULT_CARVED_COMPONENTS,
) -> PrototypePlan:
    """Extract a canonical prototype from the component's OWN standalone
    MMH entry (Plan 09.1 correctness fix).
    """
    try:
        mmh_entry = _require_standalone_entry(component_name, mmh)
    except RuntimeError:
        if cjk_entries is None or graphics_lookup is None or dictionary_lookup is None:
            raise
        carved = carve_component(
            component_name,
            cjk_entries,
            graphics_lookup=graphics_lookup,
            dictionary_lookup=dictionary_lookup,
            cache_path=carved_cache_path,
        )
        mmh_entry = {
            "character": carved.character,
            "strokes": list(carved.strokes),
            "medians": carved.medians,
        }
        mmh[component_name] = mmh_entry
    stroke_count = len(_strokes_of(mmh_entry))
    return PrototypePlan(
        id=proto_id,
        name=component_name,
        from_char=component_name,
        stroke_indices=tuple(range(stroke_count)),
        roles=("meaning",),
        anchors={},
    )


def _require_standalone_entry(component_name: str, mmh: dict) -> Any:
    mmh_entry = mmh.get(component_name)
    if mmh_entry is None:
        raise RuntimeError(f"no standalone MMH entry for component '{component_name}'")
    return mmh_entry


def _extract_variant_prototype(
    component_name: str,
    context_char: str,
    proto_id: str,
    partition_indices: tuple[int, ...],
    context_strokes: list[str],
    slot: BBox,
    mmh: dict,
) -> tuple[PrototypePlan, variant_match.MatchResult]:
    """Mint a variant prototype using the MMH partition's own indices.

    Variant stroke_indices come from the partition — placement is already
    determined. The Hungarian match here is a diagnostic IoU score; when
    we don't have a standalone canonical for the component (common for
    single-stroke CJK primitives like U+31D0 / U+31D4 / U+31DA), we skip
    the probe and mint anyway. Missing canonical geometry never blocks
    variant minting.
    """
    partitioned_strokes = [context_strokes[i] for i in partition_indices]
    if component_name in mmh:
        canonical_strokes = _strokes_of(mmh[component_name])
        match = variant_match.match_in_slot(canonical_strokes, partitioned_strokes, slot)
    else:
        match = variant_match.MatchResult(
            pairs=(),
            mean_iou=0.0,
            min_iou=0.0,
            k_gt_m=False,
            below_floor=False,
        )
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


def _build_single_component_plan(
    char: str,
    comp_name: str,
    host_stroke_count: int,
    index: ProtoIndex,
    slot: BBox,
    probe_iou: Callable[[str, str, BBox], float],
    gate: float,
    cap: VariantCap,
    mmh: dict,
) -> PlanOk | PlanFailed:
    """Build a plan for a single-component decomposition.

    This is the "char IS its sole prototype" case — atomic glyphs like 一, or
    chars whose cjk-decomp has only one component and MMH declined to
    partition. All host strokes belong to one prototype.
    """
    source_indices = tuple(range(host_stroke_count))
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

    new_protos: list[PrototypePlan] = []
    variant_edges: list[tuple[str, str]] = []

    if decision.is_new_canonical:
        # Use the HOST's strokes as the canonical geometry. This is the "a 一
        # glyph's prototype IS 一" pattern — we don't need (and can't find) a
        # standalone MMH entry for a 1-component carve of the host.
        proto = PrototypePlan(
            id=decision.chosen_id,
            name=comp_name,
            from_char=char,
            stroke_indices=source_indices,
            roles=("meaning",),
            anchors={},
        )
        new_protos.append(proto)
    elif decision.is_new_variant:
        variant = PrototypePlan(
            id=decision.chosen_id,
            name=comp_name,
            from_char=char,
            stroke_indices=source_indices,
            roles=("meaning",),
            anchors={},
        )
        new_protos.append(variant)
        if decision.canonical_for_edge is not None:
            variant_edges.append((variant.id, decision.canonical_for_edge))

    child = GlyphNodePlan(
        prototype_ref=decision.chosen_id,
        mode="keep",
        source_stroke_indices=source_indices,
    )
    return PlanOk(
        glyph_plan=GlyphPlan(children=(child,)),
        new_prototypes=new_protos,
        variant_edges=variant_edges,
    )


def _component_name(component: object) -> str:
    if isinstance(component, dict):
        return str(component.get("char") or "")
    return str(component)


def _component_children(component: object) -> list[object]:
    if not isinstance(component, dict):
        return []
    raw_children = component.get("components")
    if not isinstance(raw_children, list):
        return []
    return list(raw_children)


def _components_for_entry(cjk_entry: dict[str, Any]) -> list[object]:
    raw_tree = cjk_entry.get("component_tree")
    if isinstance(raw_tree, list):
        return list(raw_tree)

    raw_components = cjk_entry.get("components", [])
    if isinstance(raw_components, tuple):
        return list(raw_components)
    if isinstance(raw_components, list):
        return list(raw_components)
    return []


def _partition_at_path(
    matches: list[list[int] | None] | None,
    path: tuple[int, ...],
) -> list[list[int]] | None:
    if not path:
        return top_level_partition(matches)
    return nested_partition(matches, path_prefix=path)


def _refine_proto_ref(char: str, path: tuple[int, ...]) -> str:
    suffix = "_".join(str(idx) for idx in path) if path else "root"
    return f"proto:refine_{name_to_slug(char)}_{suffix}"


def plan_char(
    char: str,
    cjk_entry: dict,
    mmh: dict,
    matches: list[list[int] | None] | None,
    index: ProtoIndex,
    probe_iou: Callable[[str, str, BBox], float],
    gate: float,
    cap: VariantCap,
    *,
    cjk_entries: dict[str, dict[str, Any]] | None = None,
    graphics_lookup: Callable[[str], Any | None] | None = None,
    dictionary_lookup: Callable[[str], Any | None] | None = None,
    carved_cache_path: Path = DEFAULT_CARVED_COMPONENTS,
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

    components = _components_for_entry(cjk_entry)
    if len(components) == 0:
        return PlanUnsupported(missing_op=cjk_entry.get("operator", "") or "<empty>")

    host_strokes = _strokes_of(mmh[char])

    # Single-component decomposition (atomic chars like 一, or "char IS its
    # sole prototype" cases): no partition needed — the char itself is the
    # one prototype. This is the valid answer when MMH's matches is [None]
    # or [] for a 1-component decomp.
    if len(components) == 1 and top_level_partition(matches) is None:
        comp_name = _component_name(components[0])
        # Treat the whole host as the sole prototype. If the component name
        # differs from the host char (e.g. 一 decomposes to ㇐), we still
        # use ALL host strokes since there is nothing to partition.
        return _build_single_component_plan(
            char=char,
            comp_name=comp_name or char,
            host_stroke_count=len(host_strokes),
            index=index,
            slot=_measure_slot(host_strokes, tuple(range(len(host_strokes)))),
            probe_iou=probe_iou,
            gate=gate,
            cap=cap,
            mmh=mmh,
        )

    if top_level_partition(matches) is None:
        return PlanFailed(reason=f"MMH partition shape mismatch for {char}: None")
    new_protos: list[PrototypePlan] = []
    variant_edges: list[tuple[str, str]] = []
    working_index = ProtoIndex(prototypes=list(index.prototypes))

    def build_nodes(
        current_components: list[object], path: tuple[int, ...]
    ) -> PlanFailed | list[GlyphNodePlan]:
        current_partition = _partition_at_path(matches, path)
        if current_partition is None:
            return PlanFailed(
                reason=f"MMH partition shape mismatch for {char}: {current_partition}"
            )

        expanded_components = list(current_components)
        if len(current_partition) > len(expanded_components):
            if len(expanded_components) != 1:
                return PlanFailed(
                    reason=f"MMH partition shape mismatch for {char}: {current_partition}"
                )
            expanded_components = [deepcopy(expanded_components[0]) for _ in current_partition]

        if len(current_partition) != len(expanded_components):
            return PlanFailed(
                reason=f"MMH partition shape mismatch for {char}: {current_partition}"
            )

        child_nodes: list[GlyphNodePlan] = []
        for i, component in enumerate(expanded_components):
            child_path = (*path, i)
            comp_name = _component_name(component)
            comp_children = _component_children(component)
            child_partition = _partition_at_path(matches, child_path)

            if comp_children and child_partition is not None:
                nested_nodes = build_nodes(comp_children, child_path)
                if isinstance(nested_nodes, PlanFailed):
                    return nested_nodes
                child_nodes.append(
                    GlyphNodePlan(
                        prototype_ref=_refine_proto_ref(char, child_path),
                        mode="refine",
                        children=tuple(nested_nodes),
                    )
                )
                continue

            partition_indices = tuple(current_partition[i])
            slot = _measure_slot(host_strokes, partition_indices)
            decision = decide_prototype(
                component_char=comp_name,
                context_char=char,
                slot=slot,
                index=working_index,
                probe_iou=probe_iou,
                gate=gate,
                cap=cap,
            )
            if decision.cap_exceeded:
                return PlanFailed(reason=f"variant cap exceeded for {comp_name}")

            if decision.is_new_canonical:
                try:
                    proto = _extract_canonical_prototype(
                        comp_name,
                        decision.chosen_id,
                        mmh,
                        cjk_entries=cjk_entries,
                        graphics_lookup=graphics_lookup,
                        dictionary_lookup=dictionary_lookup,
                        carved_cache_path=carved_cache_path,
                    )
                except RuntimeError as exc:
                    return PlanFailed(reason=str(exc))
                new_protos.append(proto)
                working_index.prototypes.append(proto)
            elif decision.is_new_variant:
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
                working_index.prototypes.append(variant)

            child_nodes.append(
                GlyphNodePlan(
                    prototype_ref=decision.chosen_id,
                    mode="keep",
                    source_stroke_indices=partition_indices,
                )
            )
        return child_nodes

    child_nodes = build_nodes(components, ())
    if isinstance(child_nodes, PlanFailed):
        return child_nodes

    glyph_plan = GlyphPlan(children=tuple(child_nodes))
    return PlanOk(
        glyph_plan=glyph_plan,
        new_prototypes=new_protos,
        variant_edges=variant_edges,
    )
