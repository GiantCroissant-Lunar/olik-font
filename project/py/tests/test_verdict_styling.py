from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def _load_verdict_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "verdict_styling.py"
    spec = importlib.util.spec_from_file_location("verdict_styling", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_workflow(workflow_dir: Path, style: str, checkpoint: str, controlnet: str) -> None:
    (workflow_dir / f"{style}.json").write_text(
        json.dumps(
            {
                "prompt": {
                    "1": {
                        "inputs": {"ckpt_name": checkpoint},
                        "class_type": "CheckpointLoaderSimple",
                    },
                    "6": {
                        "inputs": {"control_net_name": controlnet},
                        "class_type": "ControlNetLoader",
                    },
                }
            }
        ),
        encoding="utf-8",
    )


def test_verdict_script_bootstraps_style_and_reports_success(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    verdict = _load_verdict_module()
    workflow_dir = tmp_path / "workflows"
    out_dir = tmp_path / "styled-output"
    workflow_dir.mkdir()
    _write_workflow(workflow_dir, "ink-brush", "base.safetensors", "scribble.safetensors")

    monkeypatch.setattr(
        verdict,
        "load_available_models",
        lambda _url: {
            "checkpoints": {"base.safetensors"},
            "controlnets": {"scribble.safetensors"},
        },
    )

    commands: list[list[str]] = []

    def fake_run(cmd, check, **kwargs):
        commands.append(list(cmd))
        if cmd[0] == "/tmp/olik":
            generated = out_dir / "明" / "ink-brush" / "1.png"
            generated.parent.mkdir(parents=True, exist_ok=True)
            generated.write_bytes(b"styled")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if cmd[0] == "kimi":
            return subprocess.CompletedProcess(
                cmd,
                0,
                '{"char":"明","style":"ink-brush","legible_as_char":true,"matches_style":true,"verdict":"pass"}\n',
                "",
            )
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(verdict.subprocess, "run", fake_run)

    rc = verdict.main(
        [
            "--out-dir",
            str(out_dir),
            "--workflow-dir",
            str(workflow_dir),
            "--styles",
            "ink-brush",
            "--chars",
            "明",
            "--seeds",
            "1",
            "--olik-bin",
            "/tmp/olik",
            "--kimi-bin",
            "kimi",
        ]
    )

    assert rc == 0
    assert commands[0] == [
        "/tmp/olik",
        "style",
        "明",
        "--styles",
        "ink-brush",
        "--seeds",
        "1",
        "--out",
        str(out_dir),
    ]
    assert commands[1][0:6] == [
        "kimi",
        "--work-dir",
        str(out_dir),
        "--print",
        "--yolo",
        "--final-message-only",
    ]
    assert "Look at 明/ink-brush/1.png." in commands[1][-1]
    output = capsys.readouterr().out
    assert "aggregate: 1/1 pass rate: 100.00% (threshold 95.00%)" in output


def test_verdict_script_skips_styles_with_missing_models(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    verdict = _load_verdict_module()
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    _write_workflow(
        workflow_dir, "aged-print", "missing-base.safetensors", "missing-cn.safetensors"
    )

    monkeypatch.setattr(
        verdict,
        "load_available_models",
        lambda _url: {"checkpoints": set(), "controlnets": set()},
    )

    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("subprocess.run should not be called when every style is skipped")

    monkeypatch.setattr(verdict.subprocess, "run", fake_run)

    rc = verdict.main(
        [
            "--out-dir",
            str(tmp_path / "styled-output"),
            "--workflow-dir",
            str(workflow_dir),
            "--styles",
            "aged-print",
        ]
    )

    assert rc == 0
    assert called is False
    output = capsys.readouterr().out
    assert (
        "skip style aged-print: missing missing-base.safetensors, missing-cn.safetensors" in output
    )
    assert "no locally available styles to verify" in output


def test_verdict_script_fails_when_pass_rate_is_below_threshold(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    verdict = _load_verdict_module()
    workflow_dir = tmp_path / "workflows"
    out_dir = tmp_path / "styled-output"
    workflow_dir.mkdir()
    _write_workflow(workflow_dir, "soft-watercolor", "base.safetensors", "scribble.safetensors")
    image = out_dir / "明" / "soft-watercolor" / "1.png"
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b"styled")

    monkeypatch.setattr(
        verdict,
        "load_available_models",
        lambda _url: {
            "checkpoints": {"base.safetensors"},
            "controlnets": {"scribble.safetensors"},
        },
    )

    def fake_run(cmd, check, **kwargs):
        return subprocess.CompletedProcess(
            cmd,
            0,
            '{"char":"明","style":"soft-watercolor","legible_as_char":true,"matches_style":false,"verdict":"fail"}\n',
            "",
        )

    monkeypatch.setattr(verdict.subprocess, "run", fake_run)

    rc = verdict.main(
        [
            "--out-dir",
            str(out_dir),
            "--workflow-dir",
            str(workflow_dir),
            "--styles",
            "soft-watercolor",
            "--pass-threshold",
            "0.95",
        ]
    )

    assert rc == 1
    output = capsys.readouterr().out
    assert "FAIL 明/soft-watercolor/1.png legible=True style=False" in output
    assert "aggregate: 0/1 pass rate: 0.00% (threshold 95.00%)" in output
