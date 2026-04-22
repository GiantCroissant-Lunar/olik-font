#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request

DEFAULT_CHARS = ["明", "清", "國", "森"]
DEFAULT_STYLES = ["ink-brush", "aged-print", "soft-watercolor"]
DEFAULT_PASS_THRESHOLD = 0.95
DEFAULT_COMFYUI_URL = "http://127.0.0.1:8188"
EXPECTED_VERDICT_KEYS = {
    "char",
    "style",
    "legible_as_char",
    "matches_style",
    "verdict",
}


@dataclass(frozen=True, slots=True)
class StyledImage:
    char: str
    style: str
    seed: str
    path: Path


@dataclass(frozen=True, slots=True)
class StyleRequirement:
    style: str
    checkpoint: str
    controlnet: str


@dataclass(frozen=True, slots=True)
class VerdictRecord:
    file: str
    char: str
    style: str
    legible_as_char: bool
    matches_style: bool
    verdict: str

    @property
    def passed(self) -> bool:
        return self.legible_as_char and self.matches_style and self.verdict == "pass"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    requested_styles = [style.strip() for style in args.styles.split(",") if style.strip()]
    if not requested_styles:
        raise SystemExit("no styles requested")

    available_styles, skipped_styles = filter_available_styles(
        requested_styles,
        args.workflow_dir,
        args.comfyui_url,
    )
    for style, missing in skipped_styles.items():
        print(f"skip style {style}: missing {', '.join(missing)}")

    if not available_styles:
        print("no locally available styles to verify")
        return 0

    existing_images = collect_styled_images(args.out_dir, allowed_styles=set(available_styles))
    if not existing_images:
        invoke_olik_style(
            olik_bin=args.olik_bin,
            chars=args.chars,
            styles=available_styles,
            seeds=args.seeds,
            out_dir=args.out_dir,
        )

    images = collect_styled_images(args.out_dir, allowed_styles=set(available_styles))
    if not images:
        raise FileNotFoundError(f"no styled PNGs found under {args.out_dir}")

    verdicts = [run_kimi_verdict(image, args.out_dir, args.kimi_bin) for image in images]
    passed = sum(1 for verdict in verdicts if verdict.passed)
    total = len(verdicts)
    pass_rate = passed / total

    for verdict in verdicts:
        print(
            f"{verdict.verdict.upper()} {verdict.file} "
            f"legible={verdict.legible_as_char} style={verdict.matches_style}"
        )
    print(
        f"aggregate: {passed}/{total} pass rate: {pass_rate:.2%} "
        f"(threshold {args.pass_threshold:.2%})"
    )
    return 0 if pass_rate >= args.pass_threshold else 1


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path("styled-output"))
    parser.add_argument("--chars", nargs="+", default=DEFAULT_CHARS)
    parser.add_argument("--styles", default=",".join(DEFAULT_STYLES))
    parser.add_argument("--seeds", type=int, default=2)
    parser.add_argument("--pass-threshold", type=float, default=DEFAULT_PASS_THRESHOLD)
    parser.add_argument("--comfyui-url", default=DEFAULT_COMFYUI_URL)
    parser.add_argument(
        "--workflow-dir", type=Path, default=project_root.parent / "comfyui" / "workflows"
    )
    parser.add_argument("--olik-bin", type=Path, default=project_root / ".venv" / "bin" / "olik")
    parser.add_argument("--kimi-bin", default="kimi")
    return parser.parse_args(list(argv) if argv is not None else None)


def filter_available_styles(
    styles: Sequence[str],
    workflow_dir: Path,
    comfyui_url: str,
) -> tuple[list[str], dict[str, list[str]]]:
    installed = load_available_models(comfyui_url)
    available: list[str] = []
    skipped: dict[str, list[str]] = {}

    for style in styles:
        requirement = load_style_requirement(style, workflow_dir)
        missing: list[str] = []
        if requirement.checkpoint not in installed["checkpoints"]:
            missing.append(requirement.checkpoint)
        if requirement.controlnet not in installed["controlnets"]:
            missing.append(requirement.controlnet)
        if missing:
            skipped[style] = missing
            continue
        available.append(style)

    return available, skipped


def load_available_models(comfyui_url: str) -> dict[str, set[str]]:
    payload = fetch_object_info(comfyui_url)
    checkpoints = _extract_model_names(payload, "CheckpointLoaderSimple", "ckpt_name")
    controlnets = _extract_model_names(payload, "ControlNetLoader", "control_net_name")
    return {"checkpoints": checkpoints, "controlnets": controlnets}


def fetch_object_info(comfyui_url: str) -> dict[str, Any]:
    url = f"{comfyui_url.rstrip('/')}/object_info"
    try:
        with request.urlopen(url, timeout=10) as response:
            return json.load(response)
    except error.URLError as exc:
        raise RuntimeError(f"failed to fetch ComfyUI object_info from {url}") from exc


def load_style_requirement(style: str, workflow_dir: Path) -> StyleRequirement:
    workflow_path = workflow_dir / f"{style}.json"
    payload = json.loads(workflow_path.read_text(encoding="utf-8"))
    prompt = payload.get("prompt")
    if not isinstance(prompt, dict):
        raise ValueError(f"workflow missing prompt payload: {workflow_path}")

    checkpoint = _find_prompt_input(prompt, "CheckpointLoaderSimple", "ckpt_name")
    controlnet = _find_prompt_input(prompt, "ControlNetLoader", "control_net_name")
    return StyleRequirement(style=style, checkpoint=checkpoint, controlnet=controlnet)


def collect_styled_images(
    out_dir: Path, allowed_styles: set[str] | None = None
) -> list[StyledImage]:
    images: list[StyledImage] = []
    if not out_dir.exists():
        return images

    for path in sorted(out_dir.rglob("*.png")):
        relative = path.relative_to(out_dir)
        if len(relative.parts) != 3:
            continue
        char, style, filename = relative.parts
        if allowed_styles is not None and style not in allowed_styles:
            continue
        images.append(
            StyledImage(
                char=char,
                style=style,
                seed=Path(filename).stem,
                path=path,
            )
        )
    return images


def invoke_olik_style(
    *,
    olik_bin: Path,
    chars: Sequence[str],
    styles: Sequence[str],
    seeds: int,
    out_dir: Path,
) -> None:
    cmd = [
        str(olik_bin),
        "style",
        *chars,
        "--styles",
        ",".join(styles),
        "--seeds",
        str(seeds),
        "--out",
        str(out_dir),
    ]
    subprocess.run(cmd, check=True)


def run_kimi_verdict(image: StyledImage, out_dir: Path, kimi_bin: str) -> VerdictRecord:
    relative_path = image.path.relative_to(out_dir).as_posix()
    prompt = (
        f"Look at {relative_path}. Strict JSON one-line: "
        f'{{"char":"{image.char}","style":"{image.style}","legible_as_char":bool,'
        f'"matches_style":bool,"verdict":"pass|fail"}}'
    )
    result = subprocess.run(
        [
            kimi_bin,
            "--work-dir",
            str(out_dir),
            "--print",
            "--yolo",
            "--final-message-only",
            "-p",
            prompt,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_kimi_output(
        result.stdout,
        expected_file=relative_path,
        expected_char=image.char,
        expected_style=image.style,
    )


def parse_kimi_output(
    stdout: str,
    *,
    expected_file: str,
    expected_char: str,
    expected_style: str,
) -> VerdictRecord:
    try:
        payload = json.loads(_extract_json_object(stdout))
    except json.JSONDecodeError:
        return VerdictRecord(
            file=expected_file,
            char=expected_char,
            style=expected_style,
            legible_as_char=False,
            matches_style=False,
            verdict="fail",
        )

    if set(payload) != EXPECTED_VERDICT_KEYS:
        return VerdictRecord(
            file=expected_file,
            char=expected_char,
            style=expected_style,
            legible_as_char=False,
            matches_style=False,
            verdict="fail",
        )

    if payload["char"] != expected_char or payload["style"] != expected_style:
        return VerdictRecord(
            file=expected_file,
            char=expected_char,
            style=expected_style,
            legible_as_char=False,
            matches_style=False,
            verdict="fail",
        )

    verdict = payload["verdict"]
    legible = payload["legible_as_char"]
    matches_style = payload["matches_style"]
    if not isinstance(verdict, str) or verdict not in {"pass", "fail"}:
        verdict = "fail"
    if not isinstance(legible, bool):
        legible = False
    if not isinstance(matches_style, bool):
        matches_style = False

    return VerdictRecord(
        file=expected_file,
        char=expected_char,
        style=expected_style,
        legible_as_char=legible,
        matches_style=matches_style,
        verdict=verdict,
    )


def _extract_json_object(stdout: str) -> str:
    stripped = stdout.strip()
    if stripped.startswith("```"):
        lines = [line for line in stripped.splitlines() if not line.startswith("```")]
        stripped = "\n".join(lines).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise json.JSONDecodeError("missing JSON object", stripped, 0)
    return stripped[start : end + 1]


def _extract_model_names(payload: dict[str, Any], node_type: str, field_name: str) -> set[str]:
    node_info = payload.get(node_type, {})
    options = node_info.get("input", {}).get("required", {}).get(field_name, [])
    if not isinstance(options, list) or not options:
        return set()
    names = options[0]
    if not isinstance(names, list):
        return set()
    return {name for name in names if isinstance(name, str)}


def _find_prompt_input(prompt: dict[str, Any], class_type: str, input_name: str) -> str:
    for node in prompt.values():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") != class_type:
            continue
        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            continue
        value = inputs.get(input_name)
        if isinstance(value, str):
            return value
    raise ValueError(f"prompt missing {class_type}.{input_name}")


if __name__ == "__main__":
    raise SystemExit(main())
