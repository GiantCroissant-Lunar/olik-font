from olik_font.constraints.primitives import (
    AlignX,
    AlignY,
    AnchorDistance,
    AvoidOverlap,
    Inside,
    OrderX,
    OrderY,
    Repeat,
    as_dict,
)


def test_align_y_dict_round_trip():
    c = AlignY(targets=("inst:a.center", "inst:b.center"))
    assert as_dict(c) == {"kind": "align_y", "targets": ["inst:a.center", "inst:b.center"]}


def test_order_x_dict():
    c = OrderX(before="inst:a", after="inst:b")
    assert as_dict(c) == {"kind": "order_x", "before": "inst:a", "after": "inst:b"}


def test_anchor_distance_dict():
    c = AnchorDistance(from_="inst:a.right_edge", to="inst:b.left_edge", value=20.0)
    assert as_dict(c) == {
        "kind": "anchor_distance",
        "from": "inst:a.right_edge",
        "to": "inst:b.left_edge",
        "value": 20.0,
    }


def test_inside_dict():
    c = Inside(target="inst:inner", frame="inst:outer", padding=40.0)
    assert as_dict(c) == {
        "kind": "inside",
        "target": "inst:inner",
        "frame": "inst:outer",
        "padding": 40.0,
    }


def test_avoid_overlap_dict():
    c = AvoidOverlap(a="inst:x", b="inst:y", padding=8.0)
    assert as_dict(c) == {"kind": "avoid_overlap", "a": "inst:x", "b": "inst:y", "padding": 8.0}


def test_repeat_dict():
    c = Repeat(prototype_ref="proto:tree", count=3, layout_hint="triangle")
    assert as_dict(c) == {
        "kind": "repeat",
        "prototype_ref": "proto:tree",
        "count": 3,
        "layout_hint": "triangle",
    }


def test_unknown_primitive_raises():
    import pytest

    with pytest.raises(TypeError):
        as_dict(object())  # type: ignore[arg-type]


def test_align_x_and_order_y_dicts():
    assert as_dict(AlignX(targets=("a.center", "b.center"))) == {
        "kind": "align_x",
        "targets": ["a.center", "b.center"],
    }
    assert as_dict(OrderY(above="a", below="b")) == {
        "kind": "order_y",
        "above": "a",
        "below": "b",
    }
