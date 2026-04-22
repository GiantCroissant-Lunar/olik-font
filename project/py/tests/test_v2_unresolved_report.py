from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "v2_unresolved_report.py"
    spec = importlib.util.spec_from_file_location("v2_unresolved_report", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Entry:
    def __init__(self, decomposition: str | None, radical: str | None, matches: list[object]):
        self.decomposition = decomposition
        self.radical = radical
        self.matches = matches


class _Graphics:
    def __init__(self, strokes: list[str]):
        self.strokes = strokes


class _Lookup:
    def __init__(self) -> None:
        self.mmh_graphics = {"乙": _Graphics(["M 0 0 L 10 10"])}
        self.animcjk_graphics = {"丐": _Graphics(["M 1 1 L 9 9"])}
        self.mmh_dictionary = {"乙": _Entry("乙", "乙", [[0]])}
        self.animcjk_dictionary = {"丐": _Entry("丐", "一", [[0], [1]])}


def test_render_report_includes_reason_geometry_and_cjk_entry() -> None:
    mod = _load_module()
    unresolved = [
        mod.UnresolvedChar(
            char="乙",
            status="failed_extraction",
            reason="MMH partition shape mismatch",
            iou_mean=None,
            cjk_entry={"operator": "a", "components": ["乙"]},
            geometry=mod.describe_geometry("乙", _Lookup()),
            dictionary=mod.describe_dictionary("乙", _Lookup()),
        ),
        mod.UnresolvedChar(
            char="丐",
            status="missing",
            reason="no glyph row after bulk extract",
            iou_mean=None,
            cjk_entry={"operator": "a", "components": ["一", "丨"]},
            geometry=mod.describe_geometry("丐", _Lookup()),
            dictionary=mod.describe_dictionary("丐", _Lookup()),
        ),
    ]

    report = mod.render_report(unresolved, ["乙", "丐"], notes=["ComfyUI was slow."])

    assert "failed_extraction" in report
    assert "no glyph row after bulk extract" in report
    assert "source=mmh strokes=1" in report
    assert "source=animcjk decomposition='丐'" in report
    assert '"components": [' in report
    assert "ComfyUI was slow." in report
