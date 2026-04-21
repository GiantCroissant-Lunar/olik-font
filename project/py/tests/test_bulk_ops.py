"""cjk-decomp operator → compose mode mapping."""

from __future__ import annotations

from olik_font.bulk.ops import SUPPORTED_MODES, resolve_mode


def test_resolve_supported_ops() -> None:
    assert resolve_mode("a") == "left_right"
    assert resolve_mode("d") == "top_bottom"
    assert resolve_mode("s") == "enclose"
    assert resolve_mode("r3tr") == "repeat_triangle"


def test_resolve_unsupported_returns_none() -> None:
    assert resolve_mode("w") is None
    assert resolve_mode("wb") is None
    assert resolve_mode("nonsense") is None


def test_supported_modes_covers_olik_presets() -> None:
    # Sanity: the values of the LUT must all be real olik compose presets.
    import typing

    from olik_font.prototypes.extraction_plan import Preset

    valid = set(typing.get_args(Preset))
    assert SUPPORTED_MODES.issubset(valid)
