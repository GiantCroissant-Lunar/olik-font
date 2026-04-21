from olik_font.types import (
    Affine,
    AnchorBinding,
    InstancePlacement,
    Prototype,
    PrototypeLibrary,
    Stroke,
)


def test_affine_identity_default():
    a = Affine.identity()
    assert a.translate == (0.0, 0.0)
    assert a.scale == (1.0, 1.0)
    assert a.rotate == 0.0
    assert a.shear == (0.0, 0.0)


def test_instance_placement_minimum():
    p = InstancePlacement(
        instance_id="inst:x",
        prototype_ref="proto:x",
        transform=Affine.identity(),
    )
    assert p.mode == "keep"
    assert p.depth == 0
    assert p.children == ()
    assert p.anchor_bindings == ()


def test_prototype_library_add_and_lookup():
    lib = PrototypeLibrary()
    proto = Prototype(
        id="proto:x",
        name="x",
        kind="component",
        canonical_bbox=(0.0, 0.0, 1024.0, 1024.0),
        strokes=(
            Stroke(
                id="s0",
                path="M 0 0 L 1 0",
                median=((0.0, 0.0), (1.0, 0.0)),
                order=0,
                role="horizontal",
            ),
        ),
        anchors={"center": (512.0, 512.0)},
        roles=(),
        refinement_mode="keep",
    )
    lib.add(proto)
    assert lib["proto:x"] is proto
    assert lib.contains("proto:x")


def test_anchor_binding_str_form():
    ab = AnchorBinding(from_="inst:a.right_edge", to="inst:b.left_edge", distance=20.0)
    assert ab.from_ == "inst:a.right_edge"
    assert ab.distance == 20.0
