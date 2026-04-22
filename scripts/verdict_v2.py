#!/usr/bin/env python3
# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY_ROOT = ROOT / "project" / "py"
if str(PY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PY_ROOT / "src"))

from olik_font.sources.unified import UnifiedLookup, load_unified_lookup
from olik_font.styling.render_base import render_base_png

DEFAULT_OUT_DIR = ROOT / "styled-output" / "v2-sweep"
DEFAULT_REPORT = ROOT / "vault" / "references" / "v2-verdict.md"
DEFAULT_MMH_DIR = PY_ROOT / "data" / "mmh"
DEFAULT_ANIMCJK_DIR = PY_ROOT / "data" / "animcjk"
DEFAULT_PASS_THRESHOLD = 0.95
DEFAULT_SAMPLE_SIZE = 200
DEFAULT_SEED = 2026


@dataclass(frozen=True, slots=True)
class StyledSample:
    char: str
    style: str
    seed: int
    image_path: Path


@dataclass(frozen=True, slots=True)
class VerdictRecord:
    char: str
    style: str
    seed: int
    styled_image: str
    reference_image: str
    geometry_matches_mmh: bool
    style_legible: bool
    verdict: str

    @property
    def passed(self) -> bool:
        return self.geometry_matches_mmh and self.style_legible and self.verdict == "pass"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    lookup = load_unified_lookup(args.mmh_dir, args.animcjk_dir)
    all_samples = collect_styled_samples(args.out_dir)
    selected = select_samples(all_samples, sample_size=args.sample_size, seed=args.seed)
    if not selected:
        raise FileNotFoundError(f"no styled PNGs found under {args.out_dir}")

    ref_dir = args.out_dir / ".v2-reference"
    ref_dir.mkdir(parents=True, exist_ok=True)

    verdicts: list[VerdictRecord] = []
    for sample in selected:
        reference = render_reference_png(sample.char, lookup, ref_dir)
        verdicts.append(run_kimi_verdict(sample, reference, args.out_dir, args.kimi_bin))

    passed = sum(1 for verdict in verdicts if verdict.passed)
    total = len(verdicts)
    pass_rate = passed / total

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        render_report(
            verdicts,
            pass_rate=pass_rate,
            threshold=args.pass_threshold,
            sample_seed=args.seed,
            sample_size=total,
        ),
        encoding="utf-8",
    )

    for verdict in verdicts:
        print(
            f"{verdict.verdict.upper()} {verdict.styled_image} "
            f"geometry={verdict.geometry_matches_mmh} style={verdict.style_legible}"
        )
    print(f"aggregate: {passed}/{total} pass rate: {pass_rate:.2%}")
    print(args.report)
    return 0 if pass_rate >= args.pass_threshold else 1


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--pass-threshold", type=float, default=DEFAULT_PASS_THRESHOLD)
    parser.add_argument("--mmh-dir", type=Path, default=DEFAULT_MMH_DIR)
    parser.add_argument("--animcjk-dir", type=Path, default=DEFAULT_ANIMCJK_DIR)
    parser.add_argument("--kimi-bin", default="kimi")
    return parser.parse_args(argv)


def collect_styled_samples(out_dir: Path) -> list[StyledSample]:
    samples: list[StyledSample] = []
    if not out_dir.exists():
        return samples
    for path in sorted(out_dir.rglob("*.png")):
        if ".v2-reference" in path.parts:
            continue
        relative = path.relative_to(out_dir)
        if len(relative.parts) != 3:
            continue
        char, style, filename = relative.parts
        try:
            seed = int(Path(filename).stem)
        except ValueError:
            continue
        samples.append(StyledSample(char=char, style=style, seed=seed, image_path=path))
    return samples


def select_samples(
    samples: list[StyledSample],
    *,
    sample_size: int,
    seed: int,
) -> list[StyledSample]:
    if sample_size <= 0:
        raise ValueError("sample_size must be positive")
    deduped: dict[str, StyledSample] = {}
    for sample in samples:
        deduped.setdefault(sample.char, sample)
    chars = list(deduped)
    rng = random.Random(seed)
    rng.shuffle(chars)
    chosen = chars[: min(sample_size, len(chars))]
    return [deduped[char] for char in chosen]


def render_reference_png(char: str, lookup: UnifiedLookup, ref_dir: Path) -> Path:
    entry = lookup.char_graphics_lookup(char)
    if entry is None:
        raise FileNotFoundError(f"no source graphics found for {char}")
    glyph_record = {
        "glyph_id": char,
        "coord_space": {"width": 1024, "height": 1024},
        "stroke_instances": [
            {"id": f"s{idx}", "path": path, "median": median}
            for idx, (path, median) in enumerate(zip(entry.strokes, entry.medians, strict=True))
        ],
    }
    return render_base_png(glyph_record, ref_dir / f"{char}.png")


def run_kimi_verdict(
    sample: StyledSample,
    reference_image: Path,
    out_dir: Path,
    kimi_bin: str,
) -> VerdictRecord:
    styled_rel = sample.image_path.relative_to(out_dir).as_posix()
    reference_rel = reference_image.relative_to(out_dir).as_posix()
    prompt = (
        f"Compare styled glyph {styled_rel} against MMH reference {reference_rel}. "
        "Strict JSON one-line: "
        f'{{"char":"{sample.char}","style":"{sample.style}","geometry_matches_mmh":bool,'
        '"style_legible":bool,"verdict":"pass|fail"}}. '
        f"geometry_matches_mmh is true only if the styled glyph still matches the MMH "
        f"reference structure for {sample.char}. style_legible is true only if the styled "
        f"image remains clearly legible as {sample.char}."
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
        expected_char=sample.char,
        expected_style=sample.style,
        seed=sample.seed,
        styled_image=styled_rel,
        reference_image=reference_rel,
    )


def parse_kimi_output(
    stdout: str,
    *,
    expected_char: str,
    expected_style: str,
    seed: int,
    styled_image: str,
    reference_image: str,
) -> VerdictRecord:
    try:
        payload = json.loads(extract_json_object(stdout))
    except json.JSONDecodeError:
        payload = {}

    char = str(payload.get("char") or expected_char)
    style = str(payload.get("style") or expected_style)
    geometry = bool(payload.get("geometry_matches_mmh")) if payload else False
    legible = bool(payload.get("style_legible")) if payload else False
    verdict = str(payload.get("verdict") or "fail")

    if char != expected_char or style != expected_style:
        geometry = False
        legible = False
        verdict = "fail"

    return VerdictRecord(
        char=expected_char,
        style=expected_style,
        seed=seed,
        styled_image=styled_image,
        reference_image=reference_image,
        geometry_matches_mmh=geometry,
        style_legible=legible,
        verdict=verdict,
    )


def extract_json_object(stdout: str) -> str:
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise json.JSONDecodeError("no JSON object found", stdout, 0)
    return stdout[start : end + 1]


def render_report(
    verdicts: list[VerdictRecord],
    *,
    pass_rate: float,
    threshold: float,
    sample_seed: int,
    sample_size: int,
) -> str:
    passed = sum(1 for verdict in verdicts if verdict.passed)
    lines = [
        "# v2 verdict sweep",
        "",
        f"Sample seed: {sample_seed}",
        f"Sample size: {sample_size}",
        f"Passed: {passed}",
        f"Pass rate: {pass_rate:.2%}",
        f"Threshold: {threshold:.2%}",
        "",
        "## Results",
        "",
    ]
    for verdict in verdicts:
        lines.append(
            "- "
            f"`{verdict.char}` `{verdict.style}` seed={verdict.seed} "
            f"geometry={verdict.geometry_matches_mmh} "
            f"style={verdict.style_legible} verdict={verdict.verdict}"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
