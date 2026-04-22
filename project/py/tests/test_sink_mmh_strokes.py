"""Plan 10: glyph rows carry mmh_strokes for browser-side reference render."""

from __future__ import annotations

from olik_font.emit.record import build_glyph_record
from olik_font.sources.makemeahanzi import MmhChar
from olik_font.types import Affine, InstancePlacement, PrototypeLibrary


def _mmh(strokes: list[str]) -> MmhChar:
    return MmhChar(character="X", strokes=strokes, medians=[[]] * len(strokes))


def _resolved() -> InstancePlacement:
    return InstancePlacement(
        instance_id="glyph:X",
        prototype_ref="decomp:X",
        transform=Affine.identity(),
    )


def test_build_glyph_record_embeds_mmh_strokes() -> None:
    """The emit path writes the MMH stroke path-d strings onto the
    record so the browser renders the reference view without fetching
    the source JSONL.
    """
    mmh_paths = ["M0,0 L100,100", "M100,100 L200,200"]
    record = build_glyph_record(
        "X",
        _resolved(),
        constraints=(),
        library=PrototypeLibrary(),
        mmh_char=_mmh(mmh_paths),
    )
    assert record.get("mmh_strokes") == mmh_paths


def test_build_glyph_record_mmh_strokes_is_tuple_or_list() -> None:
    """Downstream JSON serialization needs list-or-tuple; not a custom type."""
    record = build_glyph_record(
        "X",
        _resolved(),
        constraints=(),
        library=PrototypeLibrary(),
        mmh_char=_mmh(["M0,0"]),
    )
    assert isinstance(record["mmh_strokes"], (list, tuple))
