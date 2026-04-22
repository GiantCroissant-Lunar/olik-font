---
title: ComfyUI styling bridge — design
created: 2026-04-22
tags: [type/design, topic/chinese-font, topic/styling]
source: self
status: active
---

# ComfyUI styling bridge — design

Ships the styling half of v1. Takes a composed glyph record (measured
transforms, MMH-faithful reconstruction) and produces N styled PNG
variants via a local ComfyUI instance.

## Context

- Measured reconstruction works (Plan 11). The stroke_instances in a
  glyph record carry real geometry.
- ComfyUI is running locally at `127.0.0.1:8188`.
- The original scene-graph spec §pipeline-split mandates: deterministic
  geometry OUTSIDE ComfyUI, styling INSIDE ComfyUI. This is the bridge
  that was named but never built.

## Invariants

1. Bridge is one-way: glyph record → ComfyUI → PNG. No styling feedback
   modifies the geometry.
2. The bridge is offline-batch capable. Given a list of chars + a style
   family, it runs without human interaction.
3. The bridge does not reinvent placement. It consumes the SVG produced
   by our existing `glyph-viz` stroke renderer (or a Python-rendered
   equivalent) and uses it as control input for ComfyUI's ControlNet /
   img2img nodes.
4. ComfyUI workflow JSON lives in-repo under `project/comfyui/` so the
   style family is diffable and reproducible.

## Architecture

```
glyph record (project/schema/examples/glyph-record-<char>.json)
         │
         ▼
svg_render(strokes)  — pure Python, already exists via emit/svg.py or
                       glyph-viz; emits 1024×1024 black-stroke-on-white PNG
         │
         ▼
ComfyUI REST POST /prompt  — workflow JSON with style + seed + input image
         │
         ▼
ComfyUI /history polling → output PNG path
         │
         ▼
styled-output/<char>/<style>/<seed>.png
```

## Components

- `project/py/src/olik_font/styling/comfyui.py` — REST client for
  `/prompt`, `/history`, and `/view`. Typed; blocks until the job
  completes or a timeout fires.
- `project/py/src/olik_font/styling/render_base.py` — render a glyph
  record's stroke_instances to a 1024×1024 black-on-white PNG
  (pre-style input).
- `project/py/src/olik_font/styling/batch.py` — `stylize(chars, styles,
  out_dir)` orchestrator; skips already-rendered combos; retries on
  transient failures.
- `project/comfyui/workflows/ink-brush.json` — canonical "ink brush"
  style: ControlNet (lineart) + a model checkpoint + steps/cfg.
- `project/comfyui/workflows/aged-print.json` — second style for
  variety.
- `project/comfyui/workflows/soft-watercolor.json` — third style.
- CLI: `olik style <chars> --styles ink-brush,aged-print,soft-watercolor
  --out styled-output/ --seeds 3`

## Data flow per char

1. Load `glyph-record-<char>.json`.
2. Render base PNG to `/tmp/olik-style/<char>.png`.
3. For each `(style, seed)`:
   a. Load workflow JSON template.
   b. Inject base image path + seed.
   c. POST to `/prompt`.
   d. Poll `/history/<prompt_id>` until `done` with a 120s timeout.
   e. Download final PNG to `styled-output/<char>/<style>/<seed>.png`.

## Acceptance

- For each of 4 seed chars × 3 styles × 2 seeds = 24 output PNGs, kimi
  CLI says each PNG is (a) recognizable as the requested char and (b)
  rendered in the requested style. Reports as `verdict: pass|fail` per
  PNG, with aggregate pass rate ≥ 95%.
- No ComfyUI workflow uses preset-style categorical CJK layout nodes.
  Styling operates on the already-composed base image; it does not
  touch placement.

## Testing

- Offline: `test_comfyui_client.py` with a mocked ComfyUI server (record
  expected POST body shapes; assert replay matches).
- Smoke: `pytest -m integration` (opt-in) hits real ComfyUI when running
  — ensures the first style produces a non-empty PNG.

## Not in scope (deferred to v2+)

- Style consistency across a batch of different chars (e.g. all chars
  look like the same brush). v2 Task F.
- Runtime authoring UI. Post-v2.
- Alternate image backends (stable diffusion direct, Replicate API).
  v2+.
