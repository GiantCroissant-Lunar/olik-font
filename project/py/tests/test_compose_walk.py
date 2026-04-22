from pathlib import Path

import pytest

from olik_font.compose.walk import UnderspecifiedPlacement, compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.prototypes.extraction_plan import (
    ExtractionPlan,
    GlyphNodePlan,
    GlyphPlan,
    PrototypePlan,
)
from olik_font.sources.makemeahanzi import load_mmh_graphics
from olik_font.types import Affine

ROOT = Path(__file__).resolve().parents[1]
MMH = ROOT / "data" / "mmh" / "graphics.txt"

pytestmark = pytest.mark.skipif(not MMH.exists(), reason="run Plan 01 Task 4 first")


def _bbox(transform: Affine) -> tuple[float, float, float, float]:
    tx, ty = transform.translate
    sx, sy = transform.scale
    return (tx, ty, tx + 1024.0 * sx, ty + 1024.0 * sy)


def _ming_plan() -> ExtractionPlan:
    return ExtractionPlan(
        schema_version="0.1",
        prototypes=(
            PrototypePlan(
                id="proto:sun",
                name="日",
                from_char="明",
                stroke_indices=(0, 1, 2, 3),
                roles=("meaning",),
                anchors={},
            ),
            PrototypePlan(
                id="proto:moon",
                name="月",
                from_char="明",
                stroke_indices=(4, 5, 6, 7),
                roles=("meaning",),
                anchors={},
            ),
        ),
        glyphs={
            "明": GlyphPlan(
                children=(
                    GlyphNodePlan(
                        prototype_ref="proto:sun",
                        source_stroke_indices=(0, 1, 2, 3),
                    ),
                    GlyphNodePlan(
                        prototype_ref="proto:moon",
                        source_stroke_indices=(4, 5, 6, 7),
                    ),
                )
            )
        },
    )


def test_compose_transforms_measures_ming_children_from_mmh():
    assert "明" in load_mmh_graphics(MMH)

    tree = build_instance_tree("明", _ming_plan())
    resolved, constraints = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))

    left, right = resolved.children
    assert constraints == ()
    assert left.transform is not None
    assert right.transform is not None
    assert left.transform != right.transform

    left_bbox = _bbox(left.transform)
    right_bbox = _bbox(right.transform)
    assert left_bbox[0] < right_bbox[0]
    assert left_bbox[1] < 320
    assert right_bbox[1] < 100
    assert left_bbox[3] < 900
    assert right_bbox[3] < 900
    assert left.transform.scale[1] < 0.6
    assert right.transform.scale[1] < 0.9


def test_compose_transforms_raises_for_underspecified_leaf():
    plan = ExtractionPlan(
        schema_version="0.1",
        prototypes=(),
        glyphs={"明": GlyphPlan(children=(GlyphNodePlan(prototype_ref="proto:missing"),))},
    )

    tree = build_instance_tree("明", plan)
    with pytest.raises(UnderspecifiedPlacement):
        compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
