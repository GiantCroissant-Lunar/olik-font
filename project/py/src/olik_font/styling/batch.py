"""Batch orchestration for styling glyph records through ComfyUI."""

from __future__ import annotations

import copy
import json
import os
import shutil
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from olik_font.styling.comfyui import ComfyUIClient
from olik_font.styling.render_base import render_base_png

_PY_ROOT = Path(__file__).resolve().parents[3]
_PROJECT_ROOT = _PY_ROOT.parent
_DEFAULT_GLYPH_RECORD_DIR = _PROJECT_ROOT / "schema" / "examples"
_DEFAULT_WORKFLOW_DIR = _PROJECT_ROOT / "comfyui" / "workflows"
_MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True, slots=True)
class StyleReport:
    requested: int
    generated: int
    skipped: int
    failed: int
    outputs: list[Path]


@dataclass(frozen=True, slots=True)
class _StyleJob:
    char: str
    style: str
    seed: int
    dest: Path
    prompt: dict[str, Any]


def stylize(
    chars: list[str],
    styles: list[str],
    out_dir: Path,
    seeds_per_style: int,
    client: ComfyUIClient,
    *,
    glyph_records: Mapping[str, dict[str, Any]] | None = None,
    max_concurrent: int = 1,
) -> StyleReport:
    """Render glyph-record base images, submit ComfyUI jobs, and download outputs."""
    if seeds_per_style <= 0:
        raise ValueError("seeds_per_style must be positive")
    if max_concurrent <= 0:
        raise ValueError("max_concurrent must be positive")

    clean_styles = [style.strip() for style in styles if style.strip()]
    if not clean_styles:
        raise ValueError("styles must contain at least one non-empty value")

    out_dir.mkdir(parents=True, exist_ok=True)
    glyph_record_dir = None
    if glyph_records is None:
        glyph_record_dir = _resolve_dir("OLIK_GLYPH_RECORD_DIR", _DEFAULT_GLYPH_RECORD_DIR)
    workflow_dir = _resolve_dir("OLIK_COMFYUI_WORKFLOW_DIR", _DEFAULT_WORKFLOW_DIR)
    comfy_input_dir = _resolve_comfyui_input_dir()
    workflow_cache: dict[str, dict[str, Any]] = {}
    base_render_dir = out_dir / ".base-render"
    base_render_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = out_dir / _MANIFEST_NAME
    manifest_entries = _load_manifest(manifest_path)
    manifest_index = {
        (entry["char"], entry["style"], int(entry["seed"])): entry for entry in manifest_entries
    }

    requested = len(chars) * len(clean_styles) * seeds_per_style
    generated = 0
    skipped = 0
    failed = 0
    outputs: list[Path] = []
    jobs: list[_StyleJob] = []
    manifest_dirty = False

    for char in chars:
        char_jobs: list[tuple[str, int, Path]] = []
        for style in clean_styles:
            for seed in range(1, seeds_per_style + 1):
                dest = out_dir / char / style / f"{seed}.png"
                key = (char, style, seed)
                entry = manifest_index.get(key)
                if _output_exists(out_dir, dest, entry):
                    skipped += 1
                    if entry is None and dest.exists():
                        entry = _manifest_entry(
                            char,
                            style,
                            seed,
                            dest,
                            generated_at=_generated_at_for_existing_file(dest),
                            out_dir=out_dir,
                        )
                        _set_manifest_entry(manifest_entries, manifest_index, entry)
                        manifest_dirty = True
                    continue
                char_jobs.append((style, seed, dest))

        if not char_jobs:
            continue

        glyph_record = _load_glyph_record(char, glyph_record_dir, glyph_records)
        base_render = render_base_png(
            glyph_record,
            base_render_dir / _comfyui_input_name(char),
        )
        base_image_name = _stage_base_render(base_render, char, comfy_input_dir)

        for style, seed, dest in char_jobs:
            workflow = workflow_cache.get(style)
            if workflow is None:
                workflow = _load_workflow(style, workflow_dir)
                workflow_cache[style] = workflow

            jobs.append(
                _StyleJob(
                    char=char,
                    style=style,
                    seed=seed,
                    dest=dest,
                    prompt=_build_prompt(
                        workflow,
                        base_image_name=base_image_name,
                        seed=seed,
                        filename_prefix=_filename_prefix(char, style, seed),
                    ),
                )
            )

    if manifest_dirty:
        _write_manifest(manifest_path, manifest_entries)

    for result in _run_jobs(jobs, client, max_concurrent=max_concurrent):
        if isinstance(result, Exception):
            failed += 1
            continue
        generated += 1
        outputs.append(result.dest)
        entry = _manifest_entry(
            result.char,
            result.style,
            result.seed,
            result.dest,
            generated_at=_timestamp_now(),
            out_dir=out_dir,
        )
        _set_manifest_entry(manifest_entries, manifest_index, entry)
        _write_manifest(manifest_path, manifest_entries)

    return StyleReport(
        requested=requested,
        generated=generated,
        skipped=skipped,
        failed=failed,
        outputs=outputs,
    )


def _resolve_dir(env_var: str, default: Path) -> Path:
    configured = os.environ.get(env_var)
    path = Path(configured).expanduser() if configured else default
    if not path.exists():
        raise FileNotFoundError(f"{env_var} path does not exist: {path}")
    return path


def _resolve_comfyui_input_dir() -> Path:
    candidates: list[Path] = []
    configured = os.environ.get("COMFYUI_INPUT_DIR")
    if configured:
        candidates.append(Path(configured).expanduser())

    comfyui_home = os.environ.get("COMFYUI_HOME")
    if comfyui_home:
        candidates.append(Path(comfyui_home).expanduser() / "input")

    candidates.extend(
        [
            Path.home() / "Applications" / "ComfyUI" / "input",
            Path.home() / "ComfyUI" / "input",
            Path.home() / "Documents" / "ComfyUI" / "input",
            Path.cwd() / "ComfyUI" / "input",
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate
    searched = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"could not locate a ComfyUI input directory; searched: {searched}")


def _load_glyph_record(
    char: str,
    glyph_record_dir: Path | None,
    glyph_records: Mapping[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    if glyph_records is not None:
        glyph_record = glyph_records.get(char)
        if glyph_record is None:
            raise FileNotFoundError(f"missing glyph record for {char} in provided glyph_records")
        return glyph_record
    if glyph_record_dir is None:
        raise ValueError("glyph_record_dir is required when glyph_records are not provided")
    path = glyph_record_dir / f"glyph-record-{char}.json"
    if not path.exists():
        raise FileNotFoundError(f"missing glyph record for {char}: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_workflow(style: str, workflow_dir: Path) -> dict[str, Any]:
    path = workflow_dir / f"{style}.json"
    if not path.exists():
        raise FileNotFoundError(f"missing workflow for style {style}: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _stage_base_render(base_render: Path, char: str, comfy_input_dir: Path) -> str:
    filename = _comfyui_input_name(char)
    shutil.copyfile(base_render, comfy_input_dir / filename)
    return filename


def _build_prompt(
    workflow: dict[str, Any],
    *,
    base_image_name: str,
    seed: int,
    filename_prefix: str,
) -> dict[str, Any]:
    prompt = copy.deepcopy(workflow.get("prompt"))
    if not isinstance(prompt, dict):
        raise ValueError("workflow missing prompt payload")

    prompt["4"]["inputs"]["image"] = base_image_name
    prompt["8"]["inputs"]["seed"] = seed
    prompt["10"]["inputs"]["filename_prefix"] = filename_prefix
    return prompt


def _run_job_with_retry(client: ComfyUIClient, prompt: dict[str, Any], dest: Path) -> None:
    for attempt in range(2):
        try:
            prompt_id = client.submit_prompt(prompt)
            output_paths = client.wait_for_completion(prompt_id)
            if not output_paths:
                raise RuntimeError(f"ComfyUI prompt {prompt_id} produced no output paths")
            client.download_image(output_paths[0], dest)
            return
        except Exception as exc:
            if dest.exists():
                dest.unlink()
            if attempt == 0 and _is_retryable(exc):
                continue
            raise


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, TimeoutError | requests.Timeout):
        return True
    if isinstance(exc, requests.HTTPError):
        status_code = getattr(exc.response, "status_code", None)
        return isinstance(status_code, int) and 500 <= status_code < 600
    return False


def _run_jobs(
    jobs: list[_StyleJob],
    client: ComfyUIClient,
    *,
    max_concurrent: int,
):
    if max_concurrent == 1:
        for job in jobs:
            try:
                _run_job_with_retry(client, job.prompt, job.dest)
            except Exception as exc:
                yield exc
                continue
            yield job
        return

    with ThreadPoolExecutor(max_workers=max_concurrent) as pool:
        future_map = {
            pool.submit(_run_job_with_retry, client, job.prompt, job.dest): job for job in jobs
        }
        for future in as_completed(future_map):
            job = future_map[future]
            try:
                future.result()
            except Exception as exc:
                yield exc
                continue
            yield job


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"invalid manifest payload in {path}")
    entries: list[dict[str, Any]] = []
    for item in payload:
        if (
            isinstance(item, dict)
            and isinstance(item.get("char"), str)
            and isinstance(item.get("style"), str)
            and isinstance(item.get("seed"), int)
            and isinstance(item.get("output_path"), str)
            and isinstance(item.get("generated_at"), str)
        ):
            entries.append(item)
    return entries


def _write_manifest(path: Path, entries: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _set_manifest_entry(
    manifest_entries: list[dict[str, Any]],
    manifest_index: dict[tuple[str, str, int], dict[str, Any]],
    entry: dict[str, Any],
) -> None:
    key = (entry["char"], entry["style"], int(entry["seed"]))
    existing = manifest_index.get(key)
    if existing is None:
        manifest_entries.append(entry)
        manifest_index[key] = entry
        return

    for idx, current in enumerate(manifest_entries):
        if current is existing:
            manifest_entries[idx] = entry
            manifest_index[key] = entry
            return

    manifest_entries.append(entry)
    manifest_index[key] = entry


def _output_exists(out_dir: Path, dest: Path, entry: dict[str, Any] | None) -> bool:
    if dest.exists():
        return True
    if entry is None:
        return False
    output_path = Path(entry["output_path"])
    if not output_path.is_absolute():
        output_path = out_dir / output_path
    return output_path.exists()


def _manifest_entry(
    char: str,
    style: str,
    seed: int,
    dest: Path,
    *,
    generated_at: str,
    out_dir: Path,
) -> dict[str, Any]:
    return {
        "char": char,
        "style": style,
        "seed": seed,
        "output_path": str(dest.relative_to(out_dir)),
        "generated_at": generated_at,
    }


def _generated_at_for_existing_file(path: Path) -> str:
    stamp = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return stamp.isoformat().replace("+00:00", "Z")


def _timestamp_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _comfyui_input_name(char: str) -> str:
    return f"olik-base-{_char_slug(char)}.png"


def _filename_prefix(char: str, style: str, seed: int) -> str:
    safe_style = style.replace("/", "-")
    return f"olik/{_char_slug(char)}/{safe_style}/{seed}"


def _char_slug(char: str) -> str:
    return "-".join(f"{ord(codepoint):04x}" for codepoint in char)
