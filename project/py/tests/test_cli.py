import json
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

from olik_font.cli import main

ROOT = Path(__file__).resolve().parents[1]
MMH = ROOT / "data" / "mmh" / "graphics.txt"
RULES = ROOT / "src" / "olik_font" / "rules" / "rules.yaml"
SCHEMA_ROOT = ROOT.parent / "schema"

pytestmark = pytest.mark.skipif(not MMH.exists(), reason="run Plan 01 Task 4 first")


def test_build_emits_records_and_library_and_traces(tmp_path: Path, monkeypatch):
    argv = ["olik", "build", "明", "清", "國", "森", "-o", str(tmp_path)]
    monkeypatch.setattr(sys, "argv", argv)
    rc = main()
    assert rc == 0

    lib_file = tmp_path / "prototype-library.json"
    assert lib_file.exists()
    lib = json.loads(lib_file.read_text())
    jsonschema.Draft202012Validator(
        json.loads((SCHEMA_ROOT / "prototype-library.schema.json").read_text())
    ).validate(lib)

    rules_file = tmp_path / "rules.json"
    assert rules_file.exists()
    assert json.loads(rules_file.read_text()) == yaml.safe_load(RULES.read_text(encoding="utf-8"))

    for ch in ["明", "清", "國", "森"]:
        rec = tmp_path / f"glyph-record-{ch}.json"
        assert rec.exists(), f"{rec} missing"
        data = json.loads(rec.read_text())
        jsonschema.Draft202012Validator(
            json.loads((SCHEMA_ROOT / "glyph-record.schema.json").read_text())
        ).validate(data)
        trace = tmp_path / f"rule-trace-{ch}.json"
        assert trace.exists()


def test_unknown_char_returns_nonzero(tmp_path: Path, monkeypatch, capsys):
    argv = ["olik", "build", "✗", "-o", str(tmp_path)]
    monkeypatch.setattr(sys, "argv", argv)
    rc = main()
    assert rc != 0
    captured = capsys.readouterr()
    assert "✗" in captured.err or "✗" in captured.out
