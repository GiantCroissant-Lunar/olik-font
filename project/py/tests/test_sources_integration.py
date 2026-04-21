# project/py/tests/test_sources_integration.py
from pathlib import Path

import pytest

from olik_font.sources.cjk_decomp import load_cjk_decomp
from olik_font.sources.makemeahanzi import load_mmh_graphics

MMH_GRAPHICS = Path(__file__).resolve().parents[1] / "data" / "mmh" / "graphics.txt"
CJK_DECOMP = Path(__file__).resolve().parents[1] / "data" / "cjk-decomp.txt"
SEED_CHARS = ["明", "清", "國", "森"]


@pytest.mark.skipif(
    not MMH_GRAPHICS.exists(),
    reason="run fetch_mmh once first (see Task 4 Step 5)",
)
def test_mmh_contains_seed_chars():
    chars = load_mmh_graphics(MMH_GRAPHICS)
    for ch in SEED_CHARS:
        assert ch in chars, f"{ch} missing from MMH graphics"
        assert len(chars[ch].strokes) > 0


@pytest.mark.skipif(
    not CJK_DECOMP.exists(),
    reason="run extract_from_hanzijs once first (see Task 5 Step 6)",
)
def test_cjk_decomp_contains_seed_chars():
    table = load_cjk_decomp(CJK_DECOMP)
    for ch in SEED_CHARS:
        assert ch in table, f"{ch} missing from cjk-decomp"
