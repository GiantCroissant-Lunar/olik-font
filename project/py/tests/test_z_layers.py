from olik_font.compose.z_layers import z_for_stroke


def test_horizontal_strokes_go_to_stroke_body():
    assert 10 <= z_for_stroke(role="horizontal", order=0) <= 49


def test_order_increments_z_within_role():
    assert z_for_stroke("horizontal", 0) < z_for_stroke("horizontal", 1)


def test_dot_role_goes_to_stroke_body_too():
    # pass 1: all strokes live in stroke_body layer (10-49); edge/texture/damage empty
    assert 10 <= z_for_stroke("dot", 0) <= 49


def test_order_saturates_within_layer():
    # very high order clamps to top of layer
    z = z_for_stroke("horizontal", 1000)
    assert z <= 49
