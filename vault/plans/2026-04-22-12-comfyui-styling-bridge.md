---
title: Plan 12 — ComfyUI styling bridge (v1 completion)
created: 2026-04-22
tags: [type/plan, topic/chinese-font, topic/styling]
source: self
status: active
related:
  - "[[2026-04-22-comfyui-styling-bridge-design]]"
  - "[[2026-04-22-roadmap]]"
---

# Plan 12 — ComfyUI styling bridge

Completes v1 by delivering the styling half the scene-graph spec has
always assumed. 4 seed chars × 3 styles × 2 seeds = 24 styled PNGs,
kimi-verified for char legibility + style fidelity.

Spec: `[[2026-04-22-comfyui-styling-bridge-design]]`.

Workflow file: `.archon/workflows/plan-12-comfyui-styling-bridge.yaml`.

## Tasks

### Task 1 — Styling module scaffold

1. Create `project/py/src/olik_font/styling/__init__.py`.
2. Create `project/py/src/olik_font/styling/comfyui.py` with a typed
   `ComfyUIClient` class exposing `submit_prompt(workflow_json) ->
   prompt_id`, `wait_for_completion(prompt_id, timeout=120) ->
   list[output_path]`, `download_image(path, dest) -> None`. Uses
   `requests`; base URL defaults to `http://127.0.0.1:8188`.
3. Add `project/py/tests/test_comfyui_client.py` with mocked
   responses covering submit + history polling + download.
4. Commit: `feat(styling): ComfyUI REST client scaffold`.

### Task 2 — Base-image renderer

1. Create `project/py/src/olik_font/styling/render_base.py`:
   `render_base_png(glyph_record: dict, dest: Path, size: int=1024) ->
   Path`. Takes stroke_instances + coord_space from the record and
   emits a black-on-white PNG at `dest`. SVG intermediate is fine;
   use `cairosvg` if available, else write SVG + rasterize via
   `Pillow` path ops.
2. Pin any new dep in `project/py/pyproject.toml` under the normal
   `[project.dependencies]`.
3. Add `project/py/tests/test_render_base.py`: given a synthetic glyph
   record with two horizontal strokes, the output PNG has the two
   stroke bboxes at the expected pixel locations.
4. Commit: `feat(styling): render glyph records to base PNG`.

### Task 3 — Workflow templates

1. Create `project/comfyui/workflows/ink-brush.json`,
   `project/comfyui/workflows/aged-print.json`, and
   `project/comfyui/workflows/soft-watercolor.json`. Each is a valid
   ComfyUI workflow graph (the JSON shape is "nodes + links + prompt")
   that takes a `ControlNetLoader` + `LoadImage` (pointing at our base
   PNG) + a `KSampler` + `SaveImage`. If the local ComfyUI install
   doesn't have ControlNet models, document which checkpoint it needs
   in a README under `project/comfyui/workflows/README.md`.
2. Create the README listing each style, the checkpoint it requires,
   and where to source them.
3. Commit: `feat(comfyui): ink-brush / aged-print / soft-watercolor workflows`.

### Task 4 — Batch orchestrator

1. Create `project/py/src/olik_font/styling/batch.py`:
   `stylize(chars: list[str], styles: list[str], out_dir: Path,
   seeds_per_style: int, client: ComfyUIClient) -> StyleReport`.
   Skips already-existing output files. Retries once on 5xx / timeout.
2. Extend `cli.py` with a `style` subcommand:
   `olik style 明 清 國 森 --styles ink-brush,aged-print,soft-watercolor
    --seeds 2 --out styled-output/`.
3. Add `project/py/tests/test_style_batch.py` exercising the skip-
   existing + retry-once logic with a mocked client.
4. Commit: `feat(cli): olik style — batch stylize via ComfyUI`.

### Task 5 — Visual verdict gate

1. Add `scripts/verdict_styling.py` that for each PNG under
   `styled-output/<char>/<style>/<seed>.png` invokes kimi CLI with:
   `kimi --work-dir <out_dir> --print --yolo --final-message-only
    -p "Look at <file>. Strict JSON one-line:
       {\"char\":\"<char>\",\"style\":\"<style>\",\"legible_as_char\":bool,
        \"matches_style\":bool,\"verdict\":\"pass|fail\"}"`
   Aggregate pass rate; fails if < 95%.
2. Invokes `olik style` first if the output dir is empty.
3. Commit: `feat(scripts): kimi-driven styling verdict sweep`.

### Task 6 — Tag v1 complete

1. Apply tag `v1-seed-plus-styling`.
2. Update `vault/plans/2026-04-22-roadmap.md` to mark v1 as fully
   complete.
3. Commit: `docs(roadmap): v1 complete (seeds + ComfyUI styling)`.

## Out of scope

- Per-char style consistency across the batch (v2 F).
- Styling of the 4808-coverage batch (v2 F).
- Alternative image backends (v2+).
