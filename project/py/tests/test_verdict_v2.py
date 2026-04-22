from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "verdict_v2.py"
    spec = importlib.util.spec_from_file_location("verdict_v2", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_verdict_v2_samples_chars_and_writes_report(tmp_path: Path, monkeypatch, capsys) -> None:
    mod = _load_module()
    out_dir = tmp_path / "styled-output" / "v2-sweep"
    report_path = tmp_path / "v2-verdict.md"
    image = out_dir / "明" / "ink-brush" / "1.png"
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b"styled")

    monkeypatch.setattr(mod, "load_unified_lookup", lambda *_args, **_kwargs: object())

    def fake_render_reference_png(char, lookup, ref_dir):
        _ = lookup
        path = ref_dir / f"{char}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"reference")
        return path

    def fake_run(cmd, check, capture_output, text):
        assert check is True
        assert capture_output is True
        assert text is True
        assert cmd[0] == "kimi"
        assert "明/ink-brush/1.png" in cmd[-1]
        assert ".v2-reference/明.png" in cmd[-1]
        return subprocess.CompletedProcess(
            cmd,
            0,
            '{"char":"明","style":"ink-brush","geometry_matches_mmh":true,'
            '"style_legible":true,"verdict":"pass"}\n',
            "",
        )

    monkeypatch.setattr(mod, "render_reference_png", fake_render_reference_png)
    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    rc = mod.main(
        [
            "--out-dir",
            str(out_dir),
            "--report",
            str(report_path),
            "--sample-size",
            "1",
            "--seed",
            "2026",
            "--kimi-bin",
            "kimi",
        ]
    )

    assert rc == 0
    assert report_path.exists()
    report = report_path.read_text(encoding="utf-8")
    assert "Pass rate: 100.00%" in report
    assert "`明` `ink-brush` seed=1" in report
    output = capsys.readouterr().out
    assert "aggregate: 1/1 pass rate: 100.00%" in output
