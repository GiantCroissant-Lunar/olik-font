from __future__ import annotations

import json
from pathlib import Path

import pytest

from olik_font import cli as cli_mod
from olik_font.cli import _build_artifacts
from olik_font.sources.makemeahanzi import MmhDictEntry
from olik_font.sources.unified import UnifiedLookup, load_unified_lookup

ROOT = Path(__file__).resolve().parents[1]
MMH_DIR = ROOT / "data" / "mmh"
MMH_GRAPHICS = MMH_DIR / "graphics.txt"
PLAN = ROOT / "data" / "extraction_plan.yaml"
RULES = ROOT / "src" / "olik_font" / "rules" / "rules.yaml"
FIXTURES = ROOT.parent / "ts" / "apps" / "remotion-studio" / "public" / "data"
SEED = ("明", "清", "國", "森")

pytestmark = pytest.mark.skipif(not MMH_GRAPHICS.exists(), reason="run Plan 01 Task 4 first")


def _component_tree() -> dict[str, dict[str, object]]:
    return {
        "明": {
            "operator": "a",
            "components": ["日", "月"],
            "component_tree": [
                {"char": "日", "components": []},
                {"char": "月", "components": []},
            ],
        }
    }


def test_priority_order_prefers_authored_then_mmh_then_none(tmp_path: Path) -> None:
    authored_root = tmp_path / "glyph_decomp"
    authored_root.mkdir()
    (authored_root / "明.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "char": "明",
                "supersedes": "mmh",
                "rationale": "swap order to prove authored precedence",
                "authored_by": "test",
                "authored_at": "2026-04-23T02:10:00Z",
                "partition": [
                    {
                        "prototype_ref": "proto:moon",
                        "mode": "keep",
                        "source_stroke_indices": [4, 5, 6, 7],
                    },
                    {
                        "prototype_ref": "proto:sun",
                        "mode": "keep",
                        "source_stroke_indices": [0, 1, 2, 3],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    lookup = UnifiedLookup(
        mmh_graphics={},
        mmh_dictionary={
            "明": MmhDictEntry(
                character="明",
                definition=None,
                decomposition="⿰日月",
                matches=[[0], [0], [0], [0], [1], [1], [1], [1]],
            )
        },
        animcjk_graphics={},
        animcjk_dictionary={},
        cjk_entries=_component_tree(),
        authored_root=authored_root,
    )

    authored = lookup.char_decomposition_lookup("明")
    assert authored is not None
    assert authored.source == "authored"
    assert [node.prototype_ref for node in authored.partition] == ["proto:moon", "proto:sun"]

    mmh_only = UnifiedLookup(
        mmh_graphics={},
        mmh_dictionary=lookup.mmh_dictionary,
        animcjk_graphics={},
        animcjk_dictionary={},
        cjk_entries=_component_tree(),
        authored_root=tmp_path / "empty",
    )
    mmh_decomp = mmh_only.char_decomposition_lookup("明")
    assert mmh_decomp is not None
    assert mmh_decomp.source == "mmh"
    assert [node.component for node in mmh_decomp.partition] == ["日", "月"]

    assert mmh_only.char_decomposition_lookup("無") is None


def test_unified_lookup_preserves_seed_iou_against_committed_records() -> None:
    records, _library, _rules_doc, _traces = _build_artifacts(list(SEED), MMH_DIR, PLAN, RULES)

    mins: list[float] = []
    fixture_mins: list[float] = []
    for char in SEED:
        fixture = json.loads((FIXTURES / f"glyph-record-{char}.json").read_text(encoding="utf-8"))
        current_mean = float(records[char]["metadata"]["iou_report"]["mean"])
        fixture_mean = float(fixture["metadata"]["iou_report"]["mean"])
        mins.append(current_mean)
        fixture_mins.append(fixture_mean)
        assert current_mean == pytest.approx(fixture_mean, rel=0.0, abs=1e-9)

    assert min(mins) == pytest.approx(min(fixture_mins), rel=0.0, abs=1e-9)


def test_authored_override_changes_partition_identity_and_compose_still_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authored_root = tmp_path / "glyph_decomp"
    authored_root.mkdir()

    baseline_lookup = load_unified_lookup(
        MMH_DIR, ROOT / "data" / "animcjk", authored_root=authored_root
    )
    baseline = baseline_lookup.char_decomposition_lookup("明")
    assert baseline is not None
    assert baseline.source in {"animcjk", "mmh", "cjk-decomp"}

    (authored_root / "明.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "char": "明",
                "supersedes": baseline.source,
                "rationale": "swap child order for override gate",
                "authored_by": "test",
                "authored_at": "2026-04-23T02:10:00Z",
                "partition": [
                    {
                        "prototype_ref": "proto:moon",
                        "mode": "keep",
                        "source_stroke_indices": [4, 5, 6, 7],
                    },
                    {
                        "prototype_ref": "proto:sun",
                        "mode": "keep",
                        "source_stroke_indices": [0, 1, 2, 3],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    override_lookup = load_unified_lookup(
        MMH_DIR, ROOT / "data" / "animcjk", authored_root=authored_root
    )
    overridden = override_lookup.char_decomposition_lookup("明")
    assert overridden is not None
    assert overridden.source == "authored"
    assert overridden.partition != baseline.partition

    monkeypatch.setattr(
        cli_mod,
        "load_unified_lookup",
        lambda mmh_dir, animcjk_dir: load_unified_lookup(
            mmh_dir,
            animcjk_dir,
            authored_root=authored_root,
        ),
    )

    records, _library, _rules_doc, _traces = _build_artifacts(["明"], MMH_DIR, PLAN, RULES)
    assert records["明"]["source"]["decomp_source"] == "authored"
    assert float(records["明"]["metadata"]["iou_report"]["mean"]) >= 0.99
