from olik_font.constraints.presets import apply_enclose
from olik_font.geom import apply_affine_to_point
from olik_font.types import Affine, InstancePlacement


def _leaf(iid, proto):
    return InstancePlacement(instance_id=iid, prototype_ref=proto, transform=Affine.identity())


def test_outer_fills_the_whole_glyph_unchanged():
    """Outer is not letterboxed — it fills the full glyph frame.
    Plan 10.1 leaves this behavior untouched."""
    outer = _leaf("inst:O", "proto:box")
    inner = _leaf("inst:I", "proto:guts")
    outer_out, _inner_out, _c = apply_enclose(
        outer, inner, glyph_bbox=(0, 0, 1024, 1024), padding=100
    )
    p0 = apply_affine_to_point(outer_out.transform, (0.0, 0.0))
    p1 = apply_affine_to_point(outer_out.transform, (1024.0, 1024.0))
    assert p0 == (0.0, 0.0)
    assert p1 == (1024.0, 1024.0)


def test_inner_centered_in_padded_frame_with_aspect_preserved():
    """Padded frame is (100, 100, 924, 924) = 824x824. Square canonical
    fits exactly 824x824 — centered means flush to the padded edges."""
    outer = _leaf("inst:O", "proto:box")
    inner = _leaf("inst:I", "proto:guts")
    _outer_out, inner_out, _c = apply_enclose(
        outer, inner, glyph_bbox=(0, 0, 1024, 1024), padding=100
    )
    ip0 = apply_affine_to_point(inner_out.transform, (0.0, 0.0))
    ip1 = apply_affine_to_point(inner_out.transform, (1024.0, 1024.0))
    assert ip0 == (100.0, 100.0)
    assert ip1 == (924.0, 924.0)


def test_constraints_emitted_unchanged():
    outer = _leaf("inst:O", "proto:box")
    inner = _leaf("inst:I", "proto:guts")
    _, _, constraints = apply_enclose(outer, inner, glyph_bbox=(0, 0, 1024, 1024), padding=100)
    kinds = [c.__class__.__name__ for c in constraints]
    assert "Inside" in kinds
    assert "AlignX" in kinds
    assert "AlignY" in kinds
