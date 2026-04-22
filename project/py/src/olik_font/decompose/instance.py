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


def build_instance_tree(char: str, plan: ExtractionPlan) -> InstancePlacement:
    """Walk a glyph's plan; emit an InstancePlacement tree with identity transforms."""
    gp = plan.glyphs[char]
    state = {_INSTANCE_COUNTER: 0}
    return _build_glyph(char, gp, state)


def _fresh_id(name: str, state: dict) -> str:
    state[_INSTANCE_COUNTER] += 1
    return f"inst:{name}_{state[_INSTANCE_COUNTER]}"


def _build_glyph(char: str, gp: GlyphPlan, state: dict) -> InstancePlacement:
    children = tuple(_build_node(c, depth=1, state=state) for c in gp.children)
    return InstancePlacement(
        instance_id=f"inst:{char}_root",
        prototype_ref=f"proto:__glyph_{char}",
        transform=Affine.identity(),
        mode="keep",
        depth=0,
        children=children,
        input_adapter="extraction_plan",
        decomp_source={"char": char, "adapter": "extraction_plan"},
    )


def _build_node(node: GlyphNodePlan, depth: int, state: dict) -> InstancePlacement:
    children: tuple[InstancePlacement, ...] = ()
    if node.mode == "refine":
        children = tuple(_build_node(c, depth=depth + 1, state=state) for c in node.children)
    input_adapter = "refine" if node.children else "leaf"
    return InstancePlacement(
        instance_id=_fresh_id(node.prototype_ref.replace("proto:", ""), state),
        prototype_ref=node.prototype_ref,
        transform=Affine.identity(),
        mode=node.mode,
        depth=depth,
        children=children,
        input_adapter=input_adapter,
    )
