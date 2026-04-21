"""MoE 4808 loader + deterministic bucket selection."""

from __future__ import annotations

from olik_font.bulk.charlist import load_moe_4808, select_buckets


def test_load_moe_4808_returns_unique_chars() -> None:
    chars = load_moe_4808()
    assert len(chars) >= 4000, f"expected ~4808 chars, got {len(chars)}"
    assert len(set(chars)) == len(chars), "duplicates present"
    # Sanity: all entries are single CJK codepoints.
    assert all(len(c) == 1 and "\u4e00" <= c <= "\u9fff" for c in chars[:100])


def test_select_buckets_deterministic_per_seed() -> None:
    pool = [chr(0x4E00 + i) for i in range(200)]  # 一 … for 200 codepoints
    a = select_buckets(pool, already_filled=set(), count=20, seed=42)
    b = select_buckets(pool, already_filled=set(), count=20, seed=42)
    c = select_buckets(pool, already_filled=set(), count=20, seed=43)
    assert a == b
    assert a != c
    assert len(a) == 20
    assert len(set(a)) == 20


def test_select_buckets_excludes_already_filled() -> None:
    pool = [chr(0x4E00 + i) for i in range(50)]
    filled = set(pool[:10])
    picked = select_buckets(pool, already_filled=filled, count=10, seed=1)
    assert len(picked) == 10
    assert all(ch not in filled for ch in picked)


def test_select_buckets_caps_at_available() -> None:
    pool = [chr(0x4E00 + i) for i in range(10)]
    filled = set(pool[:7])
    picked = select_buckets(pool, already_filled=filled, count=99, seed=0)
    # Only 3 available; result must be exactly those 3.
    assert len(picked) == 3
    assert set(picked) == set(pool[7:])
