from __future__ import annotations

import json
from pathlib import Path

import requests

from olik_font.styling.batch import stylize


class _FakeClient:
    def __init__(self, fail_first: bool = False):
        self.fail_first = fail_first
        self.submissions: list[dict[str, object]] = []
        self.downloads: list[tuple[str, Path]] = []
        self.wait_calls = 0

    def submit_prompt(self, workflow_json: dict[str, object]) -> str:
        self.submissions.append(workflow_json)
        return f"prompt-{len(self.submissions)}"

    def wait_for_completion(self, prompt_id: str, timeout: float = 120) -> list[str]:
        _ = prompt_id, timeout
        self.wait_calls += 1
        if self.fail_first and self.wait_calls == 1:
            response = requests.Response()
            response.status_code = 503
            raise requests.HTTPError("temporary server error", response=response)
        return [f"output/job-{self.wait_calls}.png"]

    def download_image(self, path: str, dest: Path) -> None:
        self.downloads.append((path, dest))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(f"downloaded:{path}".encode())


def test_stylize_skips_existing_outputs_and_retries_once(tmp_path: Path, monkeypatch) -> None:
    record_dir = tmp_path / "records"
    workflow_dir = tmp_path / "workflows"
    comfy_input_dir = tmp_path / "comfy-input"
    out_dir = tmp_path / "styled-output"
    record_dir.mkdir()
    workflow_dir.mkdir()
    comfy_input_dir.mkdir()
    (out_dir / "明" / "ink-brush").mkdir(parents=True)
    existing = out_dir / "明" / "ink-brush" / "1.png"
    existing.write_bytes(b"already-there")

    (record_dir / "glyph-record-明.json").write_text(
        json.dumps(
            {
                "glyph_id": "明",
                "coord_space": {"width": 1024, "height": 1024},
                "stroke_instances": [
                    {
                        "id": "s0",
                        "path": "M 128 512 L 896 512",
                        "median": [[128, 512], [896, 512]],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (workflow_dir / "ink-brush.json").write_text(
        json.dumps(
            {
                "prompt": {
                    "4": {"inputs": {"image": "example.png"}, "class_type": "LoadImage"},
                    "8": {"inputs": {"seed": 1001}, "class_type": "KSampler"},
                    "10": {
                        "inputs": {"filename_prefix": "olik/ink-brush"},
                        "class_type": "SaveImage",
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("OLIK_GLYPH_RECORD_DIR", str(record_dir))
    monkeypatch.setenv("OLIK_COMFYUI_WORKFLOW_DIR", str(workflow_dir))
    monkeypatch.setenv("COMFYUI_INPUT_DIR", str(comfy_input_dir))

    client = _FakeClient(fail_first=True)

    report = stylize(
        chars=["明"],
        styles=["ink-brush"],
        out_dir=out_dir,
        seeds_per_style=2,
        client=client,
    )

    assert existing.read_bytes() == b"already-there"
    generated = out_dir / "明" / "ink-brush" / "2.png"
    assert generated.read_text(encoding="utf-8") == "downloaded:output/job-2.png"
    assert report.requested == 2
    assert report.generated == 1
    assert report.skipped == 1
    assert report.failed == 0
    assert report.outputs == [generated]
    assert len(client.submissions) == 2
    assert client.downloads == [("output/job-2.png", generated)]
    assert client.submissions[0]["4"]["inputs"]["image"].endswith(".png")
    assert client.submissions[1]["8"]["inputs"]["seed"] == 2
    assert client.submissions[1]["10"]["inputs"]["filename_prefix"].endswith("/ink-brush/2")
    staged_inputs = list(comfy_input_dir.glob("*.png"))
    assert len(staged_inputs) == 1
