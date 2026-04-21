# project/py/tests/test_makemeahanzi.py
from pathlib import Path

from olik_font.sources.makemeahanzi import MmhChar, load_mmh_graphics

FIXTURE = Path(__file__).parent / "fixtures" / "mmh_sample.jsonl"


def test_loads_two_chars_from_fixture():
    chars = load_mmh_graphics(FIXTURE)
    assert set(chars.keys()) == {"明", "木"}


def test_ming_has_eight_strokes():
    chars = load_mmh_graphics(FIXTURE)
    ming = chars["明"]
    assert isinstance(ming, MmhChar)
    assert ming.character == "明"
    assert len(ming.strokes) == 8
    assert len(ming.medians) == 8


def test_mu_has_four_strokes():
    chars = load_mmh_graphics(FIXTURE)
    mu = chars["木"]
    assert len(mu.strokes) == 4
    assert mu.strokes[0].startswith("M 100 480")
    assert mu.medians[0] == [[100, 480], [900, 480]]
