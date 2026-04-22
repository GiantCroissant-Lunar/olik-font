---
title: Session handover — 2026-04-23 (morning)
created: 2026-04-23
tags: [type/handover]
source: self
status: active
supersedes: "[[handover-2026-04-22-evening]]"
---

# Session handover — 2026-04-23 (morning)

> **Read this first when resuming.** Three big pieces landed: Plan 11
> (virtual-coordinates refactor — preset vocabulary deleted from code
> and data), Plan 12 (ComfyUI styling bridge — v1 completion), and
> Plan 13 partial (full 4808 bulk extract reached **3331 verified /
> 4808**, tag `v2-partial-3331`). Style-sweep harvest bug still open.
> Supersedes [[handover-2026-04-22-evening]].

## TL;DR — resume here

1. **Plan 11 merged** — preset vocabulary (left_right / top_bottom /
   enclose / repeat_triangle + slot_bbox + global slot weight constants)
   deleted from py source, yaml data, and seed JSON records. Compose now
   reads measured transforms from MMH source-stroke bboxes. Tag
   `plan-11-virtual-coordinates-only` at `e6b82f9`.
2. **Plan 12 merged** — ComfyUI styling bridge delivered. `olik style`
   CLI + 3 workflow templates (ink-brush, aged-print, soft-watercolor) +
   kimi-driven verdict script. Tag `v1-seed-plus-styling` at `1e4ca51`.
   24 seed styled PNGs verified: 100% legible, 58% style-fidelity (soft-
   watercolor prompts too tight; calibration notes below).
3. **Plan 13 partial** — full 4808-char Taiwan pool processed. Final DB
   state: **verified 3331, needs_review 133, failed_extraction 1329,
   filled 4797 / 4808.** Tag `v2-partial-3331` at `e878d00`. From the
   first bulk-pass 632 → final 3331 via three diagnosed planner fixes
   (atomic-char path, variant-carve fallback, bumped caps).
4. **Two known bugs blocking further v2 progress:**
   - **Styling harvest bug.** ComfyUI `execution_cached` responses yield
     empty `outputs` dict; `batch.py` marks the job failed even though
     the PNG actually landed in ComfyUI's own output dir at
     `~/Applications/ComfyUI/output/olik/<hex>/<style>/…_NNNNN_.png`.
     Fix: read the filesystem directly when `history.outputs` is empty.
     Blocks `olik style --all-verified` for the 3331.
   - **Admin detail page crashes** at http://localhost:5174/glyph/<char>
     with `TypeError: __privateGet(...).defaultMutationOptions is not a
     function` — `@refinedev/core` × `@tanstack/react-query` peer-dep
     mismatch. Blocks interactive review. Workaround: use
     `/tmp/plan13-gallery/index.html` (3464 clickable detail pages).
5. **Main is clean, pushed.** Tag `v2-partial-3331` + `v1-seed-plus-styling`
   on origin.

## Current state

### Git

| Thing | Ref |
|---|---|
| main | `e878d00` (atomic-char + variant-carve fallback + caps) |
| origin | `github.com/GiantCroissant-Lunar/olik-font` |
| Open PRs | none |
| Recent tags | `v1-seed-plus-styling`, `plan-12-comfyui-styling-bridge`, `v2-partial-3331`, `plan-11-virtual-coordinates-only` |

Key commit chain across this session:

```
e878d00 fix(py): atomic-char planner + variant carve fallback + bumped caps
ab1815a fix(py): use Hungarian IoU assignment in glyph record emitter
276651a feat(py): add v2 unresolved and verdict sweep tooling
507f10e feat(cli): olik style --all-verified
37fae00 feat(data): cjk-decomp overrides file
25aeaef feat(py): per-prototype variant cap config
3aa4897 feat(prototypes): carve components from containing hosts
8e312b0 feat(sources): animCJK graphics + dictionary loader
3f81902 feat(py): planner descends into MMH nested partitions
1e4ca51 docs(roadmap): v1 complete (seeds + ComfyUI styling)
51dea1b feat(scripts): kimi-driven styling verdict sweep
0ab78c4 feat(cli): olik style — batch stylize via ComfyUI
36f81dc feat(comfyui): ink-brush / aged-print / soft-watercolor workflows
8db390b feat(styling): render glyph records to base PNG
80fe4bd feat(styling): ComfyUI REST client scaffold
```

### SurrealDB at 127.0.0.1:6480 ns=hanfont db=olik

```
filled 4797 / 4808
  verified             3331
  needs_review         133
  unsupported_op       0
  failed_extraction    1329
```

Run the update via `project/py/.venv/bin/olik extract report`.

### Visual gallery

`/tmp/plan13-gallery/index.html` — 3464 clickable chars. Each detail
page shows:
- Composed (measured, unstyled) vs MMH reference, side-by-side
- Decomposition + placement tree as SVG (rounded-rect nodes, curved edges;
  border color: blue=measured, amber=refine, gray=leaf)
- IoU report JSON
- ComfyUI styled variants (populated for the 4 seeds only; empty for the
  rest until the harvest bug lands)

Regenerable at any time by running the python snippet in the final
section of the 2026-04-23 session transcript (or write a small script
at `scripts/build_gallery.py`).

### Inspector

`pnpm --filter @olik/inspector dev` serves on http://localhost:5176.
React-Flow views for the 4 seeds. Works.

### Admin

`pnpm --filter @olik/admin dev` serves on http://localhost:5174. List
view works (with status filter tweaks); detail view crashes — see the
known bug in §TL;DR.

### ComfyUI

Running locally on 127.0.0.1:8188 (v0.18.1). Three workflow templates
shipped at `project/comfyui/workflows/`. Checkpoints needed listed in
`project/comfyui/workflows/README.md` (all present on this machine:
`sd_xl_base_1.0.safetensors` + xinsir SDXL ControlNets for canny and
scribble).

## Why v2 target (≥4700 verified) wasn't met

**1462 chars** are non-verified (1329 failed + 133 needs_review). They
break down into:

- **~780 KeyError / missing-MMH** — CJK stroke primitives and obscure
  radicals not in MMH graphics. `carve_component` fallback covers many
  (via containing hosts) but not all. Fix: broaden graphics coverage
  via animCJK zh-Hans (7907 chars, covers 8/15 sample gaps vs zh-Hant's
  1/15).
- **~400 partition arity mismatch** — cjk-decomp says 2-3 components but
  MMH's `matches` only partitions to 1-2. Recursive descent helps some
  but not all. Fix: CHISE IDS as third decomposition source.
- **~200 variant cap / carving edge cases** — covered by the cap bumps
  in this session, few still failing due to ordering (char X fails
  because char Y that would have minted the variant hasn't been
  processed yet). Fix: two-pass extraction.
- **~130 needs_review** — compose runs but IoU < gate (0.90). Per-
  prototype cap tuning + maybe per-glyph override.

All four fixes are v3-scope; none violate the geometry skill.

## Plan 12 styling — known calibration

Three workflow templates ship; `ink-brush` produces good style-fidelity,
`aged-print` 6/8 pass, `soft-watercolor` 0/8 pass at default params
(denoise 0.55-0.72, ControlNet strength 0.85 → diffusion too locked to
base PNG). Tested alternative: **denoise 0.85 + ControlNet strength 0.50**
produces distinct style variation with ~80% usable (some hallucinated
phantom glyphs at the lower strength). Recommended v2 calibration:
**denoise 0.80 + strength 0.65** — write into the workflow JSONs before
running `olik style --all-verified`.

## Spawned tangent tasks (not yet actioned)

Two chip-tasks were spawned this session; neither ran. They should be
picked up in the next session if the user wants.

1. **Admin detail-page + filter fix.** Fixes Refine/TanStack peer-dep
   mismatch + list default filter + detail queue filter. See
   `mcp__ccd_session__spawn_task` output from the 2026-04-23 session
   for the full prompt.
2. **MMH em-box y=900 transform fix.** `quickview/glyph-svg.tsx`
   (line 29), `glyph-viz/`, and any other SVG renderer use
   `translate(0 ${h}) scale(1 -1)` which leaves 124px blank at the top
   of each rendered cell because MMH's em-box convention puts
   ascender-top at y=900, not y=1024. Fix: `translate(0 900) scale(1 -1)`
   with `viewBox="0 0 1024 1024"`. The `/tmp/plan13-gallery/` HTML
   renderer already uses the correct transform; the codebase renderers
   do not.

## How to resume

### Environment

```bash
cd /Users/apprenticegc/Work/lunar-horse/plate-projects/olik-font
set -a; source infra/.env 2>/dev/null; set +a
alias arc='env -u CLAUDECODE archon'
```

### Sanity checks

```bash
cd project/py && .venv/bin/pytest -q
# Expected: ~185 passed, 1 xfailed
# Known failure: test_render_base_png_rasterizes_two_horizontal_strokes
# (unrelated to Plan 13; 26 vs 32 pixel-position off-by-6 in a synthetic
# test — fix when touching render_base.py)

cd ../.. && task db:up
project/py/.venv/bin/olik extract report
# Expected: filled 4797, verified 3331, needs_review 133, failed 1329
```

### Starting v3 (or finishing v2)

Pick one:

**v2 finish — the two quick wins:**
1. Fix the styling harvest bug in `project/py/src/olik_font/styling/batch.py`
   — read ComfyUI's filesystem output when `history.outputs` is empty.
2. Add animCJK zh-Hans snapshot to `sources/unified.py` (covers 8/15
   sample class-D/C failures) and expand `data/animcjk/` with zh-Hans
   rows for the ~780 KeyError chars.
3. Rerun `olik extract retry --status failed_extraction`. Projected to
   push verified past 4100.
4. Rerun `olik style --all-verified --styles ink-brush --seeds 1` with
   fixed harvest. Expected: ~3500 styled PNGs.

**v3 start — broader data sources:**
1. CHISE IDS ingestion as third decomposition source.
2. Simplified Chinese / Ja / Ko pools alongside Taiwan 4808.
3. Two-pass bulk extract: first pass plants prototypes, second pass
   uses them.

### Gallery

`open -a "Google Chrome" file:///tmp/plan13-gallery/index.html`

To refresh with latest DB state, rerun the gallery python snippet from
the final message of this session's transcript, or save it as
`scripts/build_gallery.py` for reuse.

## Open memory / feedback

Two binding rules recorded in `~/.claude/projects/-Users-apprenticegc-…/memory/`:

1. **Virtual coordinates, not preset buckets** (`feedback_virtual_coordinates.md`)
   — placement is a measured 1024² affine, never left_right / top_bottom
   categorical labels with global weights. This rule and the skill at
   `.agent/skills/05-engine/glyph-geometry/SKILL.md` stay binding across
   all future versions.
2. **Never fall back to smaller vision models** (`feedback_visual_verifier_model.md`)
   — if the user asks for Gemma 4 (cloud) or another specific vision
   model, don't silently substitute gemma3:4b. Use kimi CLI as the
   preferred visual verifier; it's confirmed working on
   UI-screenshot + PNG-content verdicts.

## Reference trail

- Roadmap: [[2026-04-22-roadmap]] — v1 done, v2 partial, v3 scope.
- Plan 11 spec/plan: [[2026-04-22-virtual-coordinates-only-design]] /
  [[2026-04-22-11-virtual-coordinates-only]].
- Plan 12 spec/plan: [[2026-04-22-comfyui-styling-bridge-design]] /
  [[2026-04-22-12-comfyui-styling-bridge]].
- Plan 13 plan: [[2026-04-22-13-v2-full-4808-coverage]].
- Geometry skill: `.agent/skills/05-engine/glyph-geometry/SKILL.md`.
- v2-unresolved log: `vault/references/v2-unresolved.md` (written by
  Plan 13 Task G tooling; stale — regenerate after next bulk run).
- v2-verdict log: `vault/references/v2-verdict.md` (blocked; will
  regenerate after styling harvest fix).
- Gallery: `/tmp/plan13-gallery/index.html`.
