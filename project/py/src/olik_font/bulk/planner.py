"""Auto-plan a single character from a unified decomposition + MMH data.

Placement comes from per-instance measured stroke indices, not from any
categorical layout vocabulary. Source lookup decides whether that
partition came from authored data, animCJK, MMH, or cjk-decomp, and the
planner turns the chosen tree into a GlyphPlan.

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
from olik_font.sources.unified import Decomposition, PartitionNode
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


def _decomposition_from_legacy(
    cjk_entry: dict[str, Any] | None,
    matches: list[list[int] | None] | None,
) -> Decomposition | None:
    if cjk_entry is None:
        return None

    raw_tree = cjk_entry.get("component_tree")
    if not isinstance(raw_tree, list) or not raw_tree:
        raw_components = cjk_entry.get("components", [])
        if not isinstance(raw_components, list) or not raw_components:
            return None
        raw_tree = [{"char": str(component), "components": []} for component in raw_components]

    def partition_for_path(path: tuple[int, ...]) -> list[list[int]] | None:
        if not path:
            return top_level_partition(matches)
        return nested_partition(matches, path_prefix=path)

    def build_nodes(
        nodes: list[dict[str, Any]],
        path: tuple[int, ...] = (),
    ) -> tuple[PartitionNode, ...]:
        current_partition = partition_for_path(path)
        current_nodes = list(nodes)
        if current_partition is not None:
            if len(current_partition) > len(current_nodes):
                if len(current_nodes) != 1:
                    raise ValueError(f"MMH partition shape mismatch at {path}: {current_partition}")
                current_nodes = [deepcopy(current_nodes[0]) for _ in current_partition]
            if len(current_partition) != len(current_nodes):
                raise ValueError(f"MMH partition shape mismatch at {path}: {current_partition}")

        out: list[PartitionNode] = []
        for index, node in enumerate(current_nodes):
            child_path = (*path, index)
            raw_children = node.get("components", [])
            children = (
                build_nodes(raw_children, child_path)
                if isinstance(raw_children, list) and raw_children
                else ()
            )
            out.append(
                PartitionNode(
                    component=str(node.get("char") or ""),
                    mode="refine" if children else "keep",
                    source_stroke_indices=(
                        None
                        if children or current_partition is None
                        else tuple(current_partition[index])
                    ),
                    children=children,
                )
            )
        return tuple(out)

    return Decomposition(partition=build_nodes(raw_tree), source="mmh", confidence=1.0)


def _refine_proto_ref(char: str, path: tuple[int, ...]) -> str:
    suffix = "_".join(str(idx) for idx in path) if path else "root"
    return f"proto:refine_{name_to_slug(char)}_{suffix}"


def _existing_proto(proto_id: str, index: ProtoIndex, new_protos: list[PrototypePlan]) -> bool:
    return any(proto.id == proto_id for proto in index.prototypes) or any(
        proto.id == proto_id for proto in new_protos
    )


def _name_for_authored_proto(proto_id: str) -> str:
    return proto_id.removeprefix("proto:")


def plan_char(
    char: str,
    cjk_entry: dict | None,
    mmh: dict,
    matches: list[list[int] | None] | None,
    index: ProtoIndex,
    probe_iou: Callable[[str, str, BBox], float],
    gate: float,
    cap: VariantCap,
    *,
    decomposition: Decomposition | None = None,
    cjk_entries: dict[str, dict[str, Any]] | None = None,
    graphics_lookup: Callable[[str], Any | None] | None = None,
    dictionary_lookup: Callable[[str], Any | None] | None = None,
    carved_cache_path: Path = DEFAULT_CARVED_COMPONENTS,
) -> PlanResult:
    """Return a PlanResult for one char without touching the DB."""
    if char not in mmh:
        return PlanFailed(reason=f"MMH missing {char}")

    if decomposition is None:
        try:
            decomposition = _decomposition_from_legacy(cjk_entry, matches)
        except ValueError as exc:
            return PlanFailed(reason=str(exc))
    if decomposition is None or len(decomposition.partition) == 0:
        missing_op = "<empty>"
        if isinstance(cjk_entry, dict):
            missing_op = cjk_entry.get("operator", "") or "<empty>"
        return PlanUnsupported(missing_op=missing_op)

    host_strokes = _strokes_of(mmh[char])

    if (
        len(decomposition.partition) == 1
        and not decomposition.partition[0].children
        and decomposition.partition[0].component is not None
        and decomposition.partition[0].source_stroke_indices is None
    ):
        return _build_single_component_plan(
            char=char,
            comp_name=decomposition.partition[0].component or char,
            host_stroke_count=len(host_strokes),
            index=index,
            slot=_measure_slot(host_strokes, tuple(range(len(host_strokes)))),
            probe_iou=probe_iou,
            gate=gate,
            cap=cap,
            mmh=mmh,
        )

    new_protos: list[PrototypePlan] = []
    variant_edges: list[tuple[str, str]] = []
    working_index = ProtoIndex(prototypes=list(index.prototypes))

    def build_nodes(
        nodes: tuple[PartitionNode, ...], path: tuple[int, ...]
    ) -> PlanFailed | list[GlyphNodePlan]:
        child_nodes: list[GlyphNodePlan] = []
        for index_in_parent, node in enumerate(nodes):
            child_path = (*path, index_in_parent)

            if node.children:
                nested_nodes = build_nodes(node.children, child_path)
                if isinstance(nested_nodes, PlanFailed):
                    return nested_nodes
                refine_ref = node.prototype_ref or _refine_proto_ref(char, child_path)
                child_nodes.append(
                    GlyphNodePlan(
                        prototype_ref=refine_ref,
                        mode="refine",
                        children=tuple(nested_nodes),
                    )
                )
                continue

            partition_indices = node.source_stroke_indices
            if partition_indices is None:
                return PlanFailed(reason=f"missing measured partition for {char} at {child_path}")

            if node.prototype_ref is not None:
                if not _existing_proto(node.prototype_ref, working_index, new_protos):
                    proto = PrototypePlan(
                        id=node.prototype_ref,
                        name=_name_for_authored_proto(node.prototype_ref),
                        from_char=char,
                        stroke_indices=partition_indices,
                        roles=("meaning",),
                        anchors={},
                    )
                    new_protos.append(proto)
                    working_index.prototypes.append(proto)
                child_nodes.append(
                    GlyphNodePlan(
                        prototype_ref=node.prototype_ref,
                        mode=node.mode,
                        source_stroke_indices=partition_indices,
                    )
                )
                continue

            comp_name = node.component or ""
            if not comp_name:
                return PlanFailed(reason=f"missing component name for {char} at {child_path}")

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

    child_nodes = build_nodes(decomposition.partition, ())
    if isinstance(child_nodes, PlanFailed):
        return child_nodes

    glyph_plan = GlyphPlan(children=tuple(child_nodes))
    return PlanOk(
        glyph_plan=glyph_plan,
        new_prototypes=new_protos,
        variant_edges=variant_edges,
    )
