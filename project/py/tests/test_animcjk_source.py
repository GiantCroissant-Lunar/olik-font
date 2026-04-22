from pathlib import Path

from olik_font.sources.animcjk import load_animcjk_dictionary, load_animcjk_graphics
from olik_font.sources.makemeahanzi import load_mmh_graphics
from olik_font.sources.unified import load_unified_lookup

DATA = Path(__file__).resolve().parents[1] / "data"
ANIMCJK = DATA / "animcjk"
MMH = DATA / "mmh" / "graphics.txt"

# Current upstream animCJK-only chars in this repo's Hant snapshot. The six
# examples in Plan 13 are no longer present in today's upstream source.
ANIM_ONLY_SAMPLE = ["\u3007", "喫", "証", "説", "齣"]


def test_animcjk_snapshot_loads_current_anim_only_chars() -> None:
    graphics = load_animcjk_graphics(ANIMCJK / "graphicsZhHant.txt")
    dictionary = load_animcjk_dictionary(ANIMCJK / "dictionaryZhHant.txt")

    for ch in ANIM_ONLY_SAMPLE:
        assert ch in graphics
        assert ch in dictionary
        assert len(graphics[ch].strokes) > 0
        assert len(dictionary[ch].matches) == len(graphics[ch].strokes)


def test_unified_lookup_prefers_mmh_then_falls_back_to_animcjk() -> None:
    mmh = load_mmh_graphics(MMH)
    unified = load_unified_lookup(DATA / "mmh", ANIMCJK)

    assert "明" in mmh
    assert unified.char_graphics_lookup("明") == mmh["明"]
    assert "証" not in mmh
    assert unified.char_graphics_lookup("証") == unified.animcjk_graphics["証"]
