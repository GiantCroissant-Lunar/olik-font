# project/py/tests/test_cjk_decomp.py
from pathlib import Path

import pytest

from olik_font.sources.cjk_decomp import (
    CjkDecompEntry,
    decompose_once,
    decompose_recursive,
    load_cjk_decomp,
)

FIXTURE = Path(__file__).parent / "fixtures" / "cjk_decomp_sample.json"


def test_load_parses_operator_and_components():
    table = load_cjk_decomp(FIXTURE)
    assert table["明"] == CjkDecompEntry(char="明", operator="c", components=("日", "月"))
    assert table["青"] == CjkDecompEntry(char="青", operator="b", components=("生", "月"))
    assert table["日"] == CjkDecompEntry(char="日", operator=None, components=())


def test_atomic_entries_decompose_to_themselves():
    table = load_cjk_decomp(FIXTURE)
    assert decompose_once(table, "日") == ("日",)


def test_decompose_once_returns_one_level():
    table = load_cjk_decomp(FIXTURE)
    assert decompose_once(table, "明") == ("日", "月")
    assert decompose_once(table, "青") == ("生", "月")


def test_recursive_flattens_to_leaves():
    table = load_cjk_decomp(FIXTURE)
    # 森 → (木, 林) → (木, (木, 木)) → (木, 木, 木)
    assert decompose_recursive(table, "森") == ("木", "木", "木")
    # 清 decomposes into graphical leaves (氵, 生, 月 — our fixture marks these atomic)
    assert decompose_recursive(table, "清") == ("氵", "生", "月")


def test_unknown_char_raises():
    table = load_cjk_decomp(FIXTURE)
    with pytest.raises(KeyError):
        decompose_once(table, "✗")
