"""Build an InstancePlacement tree from a GlyphPlan.

Output transforms are placeholders (identity). Compose resolves
placement downstream from plan-authored geometry.
"""

from __future__ import annotations

from olik_font.prototypes.extraction_plan import (
    ExtractionPlan,
    GlyphNodePlan,
    GlyphPlan,
)
from olik_font.types import Affine, InstancePlacement

_INSTANCE_COUNTER = "_ctr"


def build_instance_tree(
    char: str,
    plan: ExtractionPlan,
    *,
    decomp_source: dict[str, object] | None = None,
) -> InstancePlacement:
    """Walk a glyph's plan; emit an InstancePlacement tree with identity transforms."""
    gp = plan.glyphs[char]
    state = {_INSTANCE_COUNTER: 0}
    return _build_glyph(char, gp, plan.by_prototype_id, state, decomp_source=decomp_source)


def _fresh_id(name: str, state: dict) -> str:
    state[_INSTANCE_COUNTER] += 1
    return f"inst:{name}_{state[_INSTANCE_COUNTER]}"


def _build_glyph(
    char: str,
    gp: GlyphPlan,
    by_prototype_id,
    state: dict,
    *,
    decomp_source: dict[str, object] | None,
) -> InstancePlacement:
    children = tuple(
        _build_node(c, root_char=char, by_prototype_id=by_prototype_id, depth=1, state=state)
        for c in gp.children
    )
    return InstancePlacement(
        instance_id=f"inst:{char}_root",
        prototype_ref=f"proto:__glyph_{char}",
        transform=Affine.identity(),
        mode="keep",
        depth=0,
        children=children,
        input_adapter="extraction_plan",
        decomp_source=decomp_source or {"char": char, "adapter": "extraction_plan"},
    )


def _build_node(
    node: GlyphNodePlan,
    *,
    root_char: str,
    by_prototype_id,
    depth: int,
    state: dict,
) -> InstancePlacement:
    children: tuple[InstancePlacement, ...] = ()
    if node.mode == "refine":
        children = tuple(
            _build_node(
                c,
                root_char=root_char,
                by_prototype_id=by_prototype_id,
                depth=depth + 1,
                state=state,
            )
            for c in node.children
        )

    source_stroke_indices = node.source_stroke_indices
    if source_stroke_indices is None:
        prototype = by_prototype_id.get(node.prototype_ref)
        if prototype is not None and prototype.from_char == root_char:
            source_stroke_indices = prototype.stroke_indices

    input_adapter = "refine" if node.children else ("measured" if source_stroke_indices else "leaf")
    return InstancePlacement(
        instance_id=_fresh_id(node.prototype_ref.replace("proto:", ""), state),
        prototype_ref=node.prototype_ref,
        transform=None,
        source_stroke_indices=source_stroke_indices,
        mode=node.mode,
        depth=depth,
        children=children,
        input_adapter=input_adapter,
    )
