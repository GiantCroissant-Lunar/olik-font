"""Per-prototype variant cap config."""

from __future__ import annotations

from olik_font.bulk.reuse import ProtoIndex, canonical_id, decide_prototype, variant_id
from olik_font.bulk.variant_caps import load_variant_caps
from olik_font.prototypes.extraction_plan import PrototypePlan

_SLOT = (0.0, 0.0, 512.0, 1024.0)


def _proto(id_: str, name: str, from_char: str, strokes: tuple[int, ...]) -> PrototypePlan:
    return PrototypePlan(
        id=id_,
        name=name,
        from_char=from_char,
        stroke_indices=strokes,
        roles=("meaning",),
        anchors={},
    )


def test_default_variant_caps_file_loads_exact_caps() -> None:
    caps = load_variant_caps()

    assert caps.cap_for("木") == 20
    assert caps.cap_for("口") == 20
    assert caps.cap_for("水") == 10


def test_variant_caps_support_globs_with_exact_override(tmp_path) -> None:
    path = tmp_path / "variant_caps.yaml"
    path.write_text(
        'default: 10\n"[木林]": 3\n木: 1\n',
        encoding="utf-8",
    )

    caps = load_variant_caps(path)

    assert caps.cap_for("木") == 1
    assert caps.cap_for("林") == 3
    assert caps.cap_for("水") == 10


def test_decide_prototype_uses_per_component_cap(tmp_path) -> None:
    path = tmp_path / "variant_caps.yaml"
    path.write_text("default: 10\n木: 1\n", encoding="utf-8")
    caps = load_variant_caps(path)

    cid = canonical_id("木")
    idx = ProtoIndex(
        prototypes=[
            _proto(cid, "木", "木", (0, 1, 2, 3)),
            _proto(variant_id("木", "桂"), "木", "桂", (0, 1, 2, 3)),
        ]
    )

    decision = decide_prototype(
        component_char="木",
        context_char="橋",
        slot=_SLOT,
        index=idx,
        probe_iou=lambda *_a, **_kw: 0.5,
        gate=0.90,
        cap=caps.cap_for,
    )

    assert decision.chosen_id is None
    assert decision.cap_exceeded is True
