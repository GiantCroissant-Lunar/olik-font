# project/py/tests/test_sources_integration.py
from pathlib import Path

import pytest

from olik_font.sources.cjk_decomp import load_cjk_decomp
from olik_font.sources.makemeahanzi import load_mmh_graphics

DATA = Path(__file__).resolve().parents[1] / "data"
MMH_GRAPHICS = DATA / "mmh" / "graphics.txt"
# cjk-decomp.json is committed to the repo; no skipif required.
CJK_DECOMP = DATA / "cjk-decomp.json"

SEED_CHARS = ["明", "清", "國", "森"]


@pytest.mark.skipif(
    not MMH_GRAPHICS.exists(),
    reason="run `task data:fetch-mmh` or let the Archon workflow warm this cache",
)
def test_mmh_contains_seed_chars():
    chars = load_mmh_graphics(MMH_GRAPHICS)
    for ch in SEED_CHARS:
        assert ch in chars, f"{ch} missing from MMH graphics"
        assert len(chars[ch].strokes) > 0


def test_cjk_decomp_contains_seed_chars():
    """cjk-decomp.json is committed; this test should never skip."""
    assert CJK_DECOMP.exists(), f"{CJK_DECOMP} missing — regen via `task data:regen-cjk-decomp`"
    table = load_cjk_decomp(CJK_DECOMP)
    for ch in SEED_CHARS:
        assert ch in table, f"{ch} missing from cjk-decomp"
