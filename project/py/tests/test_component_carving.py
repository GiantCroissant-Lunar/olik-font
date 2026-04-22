from __future__ import annotations

import json
from pathlib import Path

from olik_font.bulk.batch import _load_cjk_entries
from olik_font.bulk.planner import PlanOk, plan_char
from olik_font.bulk.reuse import ProtoIndex, canonical_id
from olik_font.prototypes.carve import carve_component
from olik_font.sources.makemeahanzi import MmhChar
from olik_font.sources.unified import load_unified_lookup

DATA = Path(__file__).resolve().parents[1] / "data"
ANIMCJK = DATA / "animcjk"
MMH = DATA / "mmh"
CJK_DECOMP = DATA / "cjk-decomp.json"
CARVE_SAMPLE = ["乏", "侖", "前", "叉", "商", "天"]


def _rect_path(x0: float, y0: float, x1: float, y1: float) -> str:
    return f"M{x0},{y0} L{x1},{y0} L{x1},{y1} L{x0},{y1} Z"


def test_carve_component_resolves_sample_targets_and_hits_cache(tmp_path: Path) -> None:
    lookup = load_unified_lookup(MMH, ANIMCJK)
    cjk_entries = _load_cjk_entries(CJK_DECOMP)
    cache_path = tmp_path / "carved_components.json"

    def blocked_graphics_lookup(char: str) -> MmhChar | None:
        if char in CARVE_SAMPLE:
            return None
        return lookup.char_graphics_lookup(char)

    for component in CARVE_SAMPLE:
        carved = carve_component(
            component,
            cjk_entries,
            graphics_lookup=blocked_graphics_lookup,
            dictionary_lookup=lookup.char_dictionary_lookup,
            cache_path=cache_path,
        )
        assert carved.character == component
        assert len(carved.strokes) > 0
        assert len(carved.medians) == len(carved.strokes)

    cached_doc = json.loads(cache_path.read_text(encoding="utf-8"))
    assert set(cached_doc["components"]) == set(CARVE_SAMPLE)

    for component in CARVE_SAMPLE:
        cached = carve_component(
            component,
            cjk_entries,
            graphics_lookup=lambda _char: None,
            dictionary_lookup=lambda _char: None,
            cache_path=cache_path,
        )
        assert cached.character == component
        assert len(cached.strokes) > 0


def test_plan_char_falls_back_to_component_carving(tmp_path: Path) -> None:
    cjk_entries = {
        "泛": {
            "operator": "a",
            "components": ["氵", "乏"],
            "component_tree": [
                {"char": "氵", "components": []},
                {"char": "乏", "components": []},
            ],
        }
    }
    mmh = {
        "泛": {
            "character": "泛",
            "strokes": [
                _rect_path(0, 0, 64, 64),
                _rect_path(128, 0, 192, 64),
                _rect_path(192, 0, 256, 64),
            ],
            "medians": [[]] * 3,
        },
        "氵": {
            "character": "氵",
            "strokes": [_rect_path(0, 0, 64, 64)],
            "medians": [[]],
        },
    }
    host_graphics = {
        "泛": MmhChar(character="泛", strokes=list(mmh["泛"]["strokes"]), medians=[[]] * 3),
        "氵": MmhChar(character="氵", strokes=[_rect_path(0, 0, 64, 64)], medians=[[]]),
    }
    host_dictionary = {"泛": {"matches": [[0], [1], [1]]}}

    result = plan_char(
        char="泛",
        cjk_entry=cjk_entries["泛"],
        mmh=mmh,
        matches=[[0], [1], [1]],
        index=ProtoIndex(prototypes=[]),
        probe_iou=lambda *_a, **_kw: 1.0,
        gate=0.90,
        cap=4,
        cjk_entries=cjk_entries,
        graphics_lookup=host_graphics.get,
        dictionary_lookup=host_dictionary.get,
        carved_cache_path=tmp_path / "carved_components.json",
    )

    assert isinstance(result, PlanOk)
    assert "乏" in mmh
    assert len(mmh["乏"]["strokes"]) == 2
    assert [child.source_stroke_indices for child in result.glyph_plan.children] == [(0,), (1, 2)]
    assert {proto.id for proto in result.new_prototypes} == {
        canonical_id("氵"),
        canonical_id("乏"),
    }
