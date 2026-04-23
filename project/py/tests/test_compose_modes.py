from __future__ import annotations

import json
from pathlib import Path

import pytest

from olik_font.compose.walk import compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.prototypes.extraction_plan import (
    ExtractionPlan,
    GlyphNodePlan,
    GlyphPlan,
    PrototypePlan,
)
from olik_font.sources.authored import load_authored
from olik_font.types import Affine

_TEST_CHAR = "A"
_STROKES = (
    "M 0 0 L 200 0 L 200 400 L 0 400 Z",
    "M 300 50 L 700 50 L 700 450 L 300 450 Z",
)


def _bbox(transform: Affine) -> tuple[float, float, float, float]:
    tx, ty = transform.translate
    sx, sy = transform.scale
    return (tx, ty, tx + 1024.0 * sx, ty + 1024.0 * sy)


@pytest.fixture(autouse=True)
def _stub_mmh_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "olik_font.compose.walk.MMH_LOOKUP",
        lambda char: _STROKES if char == _TEST_CHAR else (),
    )


def test_keep_uses_prototype_as_is() -> None:
    plan = ExtractionPlan(
        schema_version="0.1",
        prototypes=(),
        glyphs={
            _TEST_CHAR: GlyphPlan(
                children=(
                    GlyphNodePlan(
                        prototype_ref="proto:keep_leaf",
                        mode="keep",
                        source_stroke_indices=(0,),
                    ),
                )
            )
        },
    )

    tree = build_instance_tree(_TEST_CHAR, plan)
    resolved, constraints = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))

    leaf = resolved.children[0]
    assert constraints == ()
    assert leaf.prototype_ref == "proto:keep_leaf"
    assert leaf.input_adapter == "measured"
    assert leaf.children == ()
    assert _bbox(leaf.transform) == pytest.approx((0.0, 0.0, 200.0, 400.0))


def test_refine_recurses_into_children() -> None:
    plan = ExtractionPlan(
        schema_version="0.1",
        prototypes=(),
        glyphs={
            _TEST_CHAR: GlyphPlan(
                children=(
                    GlyphNodePlan(
                        prototype_ref="proto:refine_parent",
                        mode="refine",
                        children=(
                            GlyphNodePlan(
                                prototype_ref="proto:left_child",
                                mode="keep",
                                source_stroke_indices=(0,),
                            ),
                            GlyphNodePlan(
                                prototype_ref="proto:right_child",
                                mode="keep",
                                source_stroke_indices=(1,),
                            ),
                        ),
                    ),
                )
            )
        },
    )

    tree = build_instance_tree(_TEST_CHAR, plan)
    assert len(tree.children[0].children) == 2
    assert tree.children[0].input_adapter == "refine"

    resolved, _constraints = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))

    parent = resolved.children[0]
    assert [child.prototype_ref for child in parent.children] == [
        "proto:left_child",
        "proto:right_child",
    ]
    assert _bbox(parent.transform) == pytest.approx((0.0, 0.0, 700.0, 450.0))


def test_replace_swaps_prototype_ref(tmp_path: Path) -> None:
    authored_root = tmp_path / "glyph_decomp"
    authored_root.mkdir()
    (authored_root / f"{_TEST_CHAR}.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "char": _TEST_CHAR,
                "supersedes": "mmh",
                "rationale": "swap to the authored variant prototype",
                "authored_by": "test",
                "authored_at": "2026-04-23T03:00:00Z",
                "partition": [
                    {
                        "prototype_ref": "proto:shape_old",
                        "mode": "replace",
                        "replacement_proto_ref": "proto:shape_new",
                        "source_stroke_indices": [1],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    authored = load_authored(_TEST_CHAR, root=authored_root)
    assert authored is not None
    node = authored.partition[0]
    plan = ExtractionPlan(
        schema_version="0.1",
        prototypes=(
            PrototypePlan(
                id="proto:shape_old",
                name="shape_old",
                from_char=_TEST_CHAR,
                stroke_indices=(1,),
                roles=("meaning",),
                anchors={},
            ),
            PrototypePlan(
                id="proto:shape_new",
                name="shape_new",
                from_char=_TEST_CHAR,
                stroke_indices=(1,),
                roles=("meaning",),
                anchors={},
            ),
        ),
        glyphs={
            _TEST_CHAR: GlyphPlan(
                children=(
                    GlyphNodePlan(
                        prototype_ref=node.prototype_ref,
                        mode=node.mode,
                        source_stroke_indices=node.source_stroke_indices,
                        replacement_proto_ref=node.replacement_proto_ref,
                    ),
                )
            )
        },
    )

    tree = build_instance_tree(_TEST_CHAR, plan)
    assert tree.children[0].prototype_ref == "proto:shape_new"
    assert tree.children[0].input_adapter == "replaced"

    resolved, _constraints = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))

    replaced = resolved.children[0]
    assert replaced.prototype_ref == "proto:shape_new"
    assert replaced.mode == "replace"
    assert _bbox(replaced.transform) == pytest.approx((300.0, 50.0, 700.0, 450.0))
