"""Build an InstancePlacement tree from a GlyphPlan.

Output transforms are placeholders (identity). Preset resolvers in
`constraints/presets.py` fill in real transforms downstream.
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

    if gp.preset == "repeat_triangle":
        return _build_repeat_triangle(char, gp, state)
    return _build_preset(char, gp, state)


def _fresh_id(name: str, state: dict) -> str:
    state[_INSTANCE_COUNTER] += 1
    return f"inst:{name}_{state[_INSTANCE_COUNTER]}"


def _build_preset(char: str, gp: GlyphPlan, state: dict) -> InstancePlacement:
    children = tuple(_build_node(c, depth=1, state=state) for c in gp.children)
    return InstancePlacement(
        instance_id=f"inst:{char}_root",
        prototype_ref=f"proto:__glyph_{char}",
        transform=Affine.identity(),
        mode="keep",
        depth=0,
        children=children,
        input_adapter=f"preset:{gp.preset}",
        decomp_source={"char": char, "adapter": "extraction_plan"},
    )


def _build_node(node: GlyphNodePlan, depth: int, state: dict) -> InstancePlacement:
    children: tuple[InstancePlacement, ...] = ()
    if node.mode == "refine":
        children = tuple(_build_node(c, depth=depth + 1, state=state) for c in node.children)
    input_adapter = f"preset:{node.preset}" if node.preset else "leaf"
    return InstancePlacement(
        instance_id=_fresh_id(node.prototype_ref.replace("proto:", ""), state),
        prototype_ref=node.prototype_ref,
        transform=Affine.identity(),
        mode=node.mode,
        depth=depth,
        children=children,
        input_adapter=input_adapter,
    )


def _build_repeat_triangle(char: str, gp: GlyphPlan, state: dict) -> InstancePlacement:
    if gp.prototype_ref is None or gp.count is None:
        raise ValueError(f"repeat_triangle for {char} missing prototype_ref/count")
    children = tuple(
        InstancePlacement(
            instance_id=_fresh_id(gp.prototype_ref.replace("proto:", "") + f"_{i}", state),
            prototype_ref=gp.prototype_ref,
            transform=Affine.identity(),
            mode="keep",
            depth=1,
            input_adapter="direct",
        )
        for i in range(gp.count)
    )
    return InstancePlacement(
        instance_id=f"inst:{char}_root",
        prototype_ref=f"proto:__glyph_{char}",
        transform=Affine.identity(),
        mode="keep",
        depth=0,
        children=children,
        input_adapter="direct:repeat_triangle",
        decomp_source={"char": char, "adapter": "extraction_plan", "kind": "repeat_triangle"},
    )
