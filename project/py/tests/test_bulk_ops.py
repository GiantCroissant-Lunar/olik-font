"""cjk-decomp operator whitelist and arity hints."""

from __future__ import annotations

from olik_font.bulk.ops import SUPPORTED_OPS, expected_component_count, is_supported_op


def test_is_supported_op_accepts_whitelist() -> None:
    for op in ("a", "d", "s", "r3tr"):
        assert is_supported_op(op)


def test_is_supported_op_rejects_others() -> None:
    for op in ("w", "wb", "nonsense", ""):
        assert not is_supported_op(op)


def test_expected_component_count() -> None:
    assert expected_component_count("a") == 2
    assert expected_component_count("d") == 2
    assert expected_component_count("s") == 2
    assert expected_component_count("r3tr") == 3
    assert expected_component_count("unknown") is None


def test_supported_ops_is_frozen_set() -> None:
    assert isinstance(SUPPORTED_OPS, frozenset)
    assert frozenset({"a", "d", "s", "r3tr"}) == SUPPORTED_OPS
