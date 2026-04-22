---
title: "Plan 10.1 — Aspect-preserving slot fit (design)"
created: 2026-04-22
tags: [type/spec, topic/compose, topic/layout]
status: draft
supersedes: null
relates-to:
  - "[[2026-04-22-admin-review-ui-design]]"
  - "[[2026-04-21-bulk-extraction-design]]"
  - "[[handover-2026-04-22-pm]]"
---

# Plan 10.1 — Aspect-preserving slot fit (design)

## 1. Context & motivation

Plan 10's admin review UI surfaced a layout-fidelity issue that was
invisible before we had composed-vs-MMH side-by-side rendering. The
preset adapters (`apply_left_right`, `apply_top_bottom`, `apply_enclose`,
`apply_repeat_triangle`) compute a slot bbox and apply
`bbox_to_bbox_affine(CANONICAL, slot_bbox)` — which scales X and Y
*independently* (non-uniform). Whenever the canonical component's
natural aspect ratio doesn't match the slot's aspect ratio, the result
is a stretched/squashed rendering.

Concrete example from the post-Plan-10 smoke: 囀 (= `a(口, 轉)`,
left_right). Slot 0 is 400×1024. Canonical 口 is ~1024×1024 (fills its
canonical frame). Non-uniform affine stretches 口 to 400×1024 — a fat,
column-tall 口 instead of the small top-left square 口 MMH actually
renders. Same pattern hits every char whose radical component is
smaller than its slot: 呢, 呀, 吗, 啦, 哈, 唉, 哇, 啥, 嗎, etc. (every
口-radical char), plus similar cases for 土, 女, 子, 亻 when the
right-hand body is wide.

Plan 10.2 (MMH-informed slot weights) will size the slot per-char based
on actual stroke distribution. Plan 10.1 is the quick structural win
that stops the stretching *within* whatever slot the preset produces:
uniform-scale the canonical to fit inside the slot while preserving its
aspect ratio, and anchor it at the slot's outer corner (top-left for
left_right slots, top-center/bottom-center for top_bottom, center for
enclose inner and repeat_triangle cells).

Expected visual effect: the "fat squashed radical" look disappears
across all affected chars; radicals render at their natural square
proportions in the top-left (or top-center / bottom-center for
top_bottom) of their slot, with whitespace letterbox in the remaining
area. Plan 10.2 later shrinks the letterbox to zero by making slot
size itself per-char.

## 2. Goals

- Introduce `olik_font.geom.fit_in_slot(src, dst, anchor) -> BBox`
  that returns a sub-bbox of `dst` preserving `src`'s aspect ratio,
  anchored at a named position within `dst`.
- Update all four preset adapters in `constraints/presets.py` to use
  `fit_in_slot` before calling `bbox_to_bbox_affine`. The affine
  receives a target sub-bbox whose aspect equals CANONICAL's, so the
  resulting transform is inherently uniform-scale.
- Hardcode per-slot anchor choices:
  - `left_right[0]`, `left_right[1]` → `top-left`
  - `top_bottom[0]` → `top-center`; `top_bottom[1]` → `bottom-center`
  - `enclose[0]` (outer) → unchanged (outer fills the whole glyph frame;
    no letterboxing)
  - `enclose[1]` (inner) → `center`
  - `repeat_triangle[0..2]` → `center` of each cell
- Preserve existing preset weight parameters (`weight_l`, `weight_top`,
  `padding`, `scale`): they still control slot *size*, which is a
  distinct concern from the aspect-preserving fit.
- Update three preset unit tests (`test_preset_left_right.py`,
  `test_preset_top_bottom.py`, `test_preset_enclose.py`) to assert the
  new anchored-bbox expectations.
- Add `test_anchor_fit.py` unit tests for the `fit_in_slot` helper.
- Verify via `olik extract auto --count 10 --seed 99` followed by a
  visual check in the admin UI: IoU distribution should improve or stay
  stable, and the visual diff between composed and MMH reference should
  tighten for radical-small characters.

## 3. Non-goals

- Per-char slot sizing. Slot bboxes stay hardcoded via the existing
  preset weights. Plan 10.2 tackles per-char weights.
- Role-aware anchor heuristics beyond the per-slot table. We do not
  look at the prototype's role tags (`meaning`, `phonetic`,
  `position_hint`) to choose anchors.
- Changes to the preset weight defaults (`weight_l = 400/1024`,
  `weight_top = 0.49`, `padding = 100`, `scale = 0.5`). Those stay
  exactly as today.
- Re-extraction of existing DB rows. The user can trigger
  `olik extract auto --count N --seed K` with a fresh seed to see the
  new renders; pre-Plan-10.1 rows keep their old stroke_instances and
  render the old (stretched) shape until manually re-extracted.
- Matcher improvements, Plan 09.3 scope, ComfyUI integration.

## 4. Architecture

One new helper in `project/py/src/olik_font/geom.py`:

```python
def fit_in_slot(
    src: BBox,
    dst: BBox,
    anchor: Literal["top-left", "top-center", "bottom-center", "center"],
) -> BBox:
    """Return the sub-bbox of `dst` preserving `src`'s aspect ratio,
    anchored at the named position within `dst`.

    y-up convention: `dst.y1` is the visual top; `dst.y0` is the
    visual bottom. Anchor names describe the visual position of
    `src` within `dst` after the fit.
    """
```

Used inside each preset adapter:

```python
def apply_left_right(left, right, glyph_bbox, weight_l=..., gap=...):
    del weight_l, gap           # existing delete-pattern from Plan 09.1
    slot_0 = _slot_bbox_left_right(0, glyph_bbox)
    slot_1 = _slot_bbox_left_right(1, glyph_bbox)

    left_target  = fit_in_slot(CANONICAL, slot_0, "top-left")
    right_target = fit_in_slot(CANONICAL, slot_1, "top-left")

    left_out  = replace(left,  transform=bbox_to_bbox_affine(CANONICAL, left_target))
    right_out = replace(right, transform=bbox_to_bbox_affine(CANONICAL, right_target))
    # ... constraints unchanged
```

`bbox_to_bbox_affine(CANONICAL, left_target)` now receives a target
whose aspect ratio equals CANONICAL's (1:1). The resulting affine's
scale_x and scale_y are equal, i.e. uniform — automatically.

Data flow is unchanged downstream: the transform field on
`InstancePlacement` still encodes the same Affine type; `compose.walk`
and `emit.record` don't need any changes; the sink doesn't need any
changes; the admin UI reads `glyph.stroke_instances[].path` which
renders the post-transform paths same as before.

## 5. `fit_in_slot` semantics

### 5.1 Scale

Uniform scale factor:

```
scale = min(
    (dst.x1 - dst.x0) / (src.x1 - src.x0),
    (dst.y1 - dst.y0) / (src.y1 - src.y0),
)
```

New source dimensions after scaling:

```
new_w = (src.x1 - src.x0) * scale
new_h = (src.y1 - src.y0) * scale
```

### 5.2 Anchors (y-up)

`dst.y1` is the visual TOP. Anchor semantics:

| Anchor | x0, x1 | y0, y1 |
|---|---|---|
| `top-left` | `dst.x0`, `dst.x0 + new_w` | `dst.y1 - new_h`, `dst.y1` |
| `top-center` | `cx - new_w/2`, `cx + new_w/2` | `dst.y1 - new_h`, `dst.y1` |
| `bottom-center` | `cx - new_w/2`, `cx + new_w/2` | `dst.y0`, `dst.y0 + new_h` |
| `center` | `cx - new_w/2`, `cx + new_w/2` | `cy - new_h/2`, `cy + new_h/2` |

where `cx = (dst.x0 + dst.x1) / 2`, `cy = (dst.y0 + dst.y1) / 2`.

Only these four anchors are used by Plan 10.1's preset table.
Additional anchors (`top-right`, `bottom-right`, `left-center`, etc.)
can be added in a future plan if needed.

### 5.3 Degenerate cases

- If `src` has zero width or height, raise `ValueError` (matches
  existing `bbox_to_bbox_affine` behavior; caller shouldn't pass an
  empty source).
- If `dst` is zero-area, return `dst` as-is (degenerate no-op).
- If `src`'s aspect ratio equals `dst`'s (within float tolerance), the
  result equals `dst` regardless of anchor — that's the "fills slot
  naturally" case.

## 6. Per-preset changes

### 6.1 `apply_left_right`

Slot 0 and slot 1 both use `top-left`. Rationale: in CJK left-right
compositions, radicals hug the top-left corner of the left slot, and
body components (right slot) fill the width from the gap onwards. For
body components that fill naturally (a common case), top-left behaves
the same as center (the uniform scale factor makes `new_w == dst_w`
and `new_h == dst_h`).

### 6.2 `apply_top_bottom`

Slot 0 (top) → `top-center`. Slot 1 (bottom) → `bottom-center`.
Rationale: top components sit at the visual top edge of the glyph;
bottom components sit at the visual bottom edge. Both are typically
wider than they are tall, so `top-center` anchors them flush against
the top of their slot with horizontal centering.

### 6.3 `apply_enclose`

Slot 0 (outer) → no `fit_in_slot` call. The outer frame by definition
fills the whole glyph canvas — letterboxing it would leave whitespace
outside the enclosing component, which is nonsense. Behavior
unchanged from today.

Slot 1 (inner) → `center`. The inner component sits in the center of
the outer's interior. Today's behavior already centers via padding;
adding `fit_in_slot` with `center` anchor makes this explicit and
preserves aspect ratio if the inner component is non-square.

### 6.4 `apply_repeat_triangle`

All three cells → `center`. Cells are 512×512 with `scale=0.5`. Most
repeat_triangle canonicals (like 木 in 森) fill a roughly square frame,
so uniform scale produces essentially the same result as today's
non-uniform affine. For non-square canonicals, centering in the cell
preserves their aspect ratio.

## 7. Seed glyph behavior post-fix

Expected behavior for the 4 Plan-01 seeds:

| Seed | Preset | Expected change |
|---|---|---|
| 明 (`a` 日 月) | left_right | 日 and 月 currently stretched to 400×1024 each. Post-fix: each anchored top-left at 400×400 (both canonicals fill 1024² standalone, uniform scale 0.39). MMH reference shows 日 at top half of left; 月 at top half of right. **Improvement.** |
| 清 (`a` 氵 青) | left_right | 氵 is tall-narrow standalone (~300×1000). Uniform scale factor ≈ 1.02 → 氵 barely shrinks, top-left anchor. 青 fills its slot. Minimal visual change. |
| 國 (`s` 囗 或) | enclose | Outer unchanged. Inner (今 1024² standalone) scales uniformly to 819×819 centered in the 824×824 padded area. Near-identical to today. |
| 森 (`r3tr` 木) | repeat_triangle | Cells are 512×512; 木 standalone fills 1024². Uniform scale 0.5 → 512×512 centered in each cell. Unchanged. |

None of the four seeds should regress below the 0.90 IoU gate. 明 may
actually *improve* its IoU because the post-fix layout is closer to
MMH's reference rendering.

## 8. Testing strategy

### 8.1 Unit — new

- `tests/test_anchor_fit.py` — pure `fit_in_slot` tests:
  - Identity (src aspect == dst aspect) returns dst unchanged for any
    anchor.
  - Uniform scale factor is `min(dst_w/src_w, dst_h/src_h)`.
  - `top-left` anchor in y-up: returned bbox has `y1 == dst.y1`.
  - `top-center` anchor: x-centered in dst, y-flush to top.
  - `bottom-center` anchor: x-centered, y-flush to bottom.
  - `center` anchor: both axes centered.
  - Zero-width src raises `ValueError`.
  - Square src (1:1) in tall rectangular dst: new bbox is square with
    side = dst_w.
  - Tall src (1:2) in wide dst (2:1): new bbox has aspect 1:2.

### 8.2 Unit — updated

- `tests/test_preset_left_right.py`:
  - Existing test `test_left_and_right_split_at_weight_l` — replace the
    bbox expectation with the anchored version. Left bbox width
    = `min(slot_w, slot_h) = slot_w = 400`; height = width (square
    canonical) = 400; y-range = top of slot (y=1024-400 to y=1024).
    Same pattern for right bbox.
- `tests/test_preset_top_bottom.py`:
  - Existing test `test_top_gets_upper_portion` (already updated by
    Plan 09.1). Update further: top bbox height = `min(glyph_w,
    slot_h)` = slot_h (slot is wider than tall), x-range centered in
    glyph width. Bottom bbox height = slot_h, x-range centered.
- `tests/test_preset_enclose.py`:
  - Outer unchanged. Inner bbox = centered square inside the padded
    area (820×820 centered in 824×824 = ~(102, 102, 922, 922) rounded).

### 8.3 Unit — unchanged

- `tests/test_preset_repeat_triangle.py` — cells are square;
  fit_in_slot with square src in square dst is identity; no change.
- `tests/test_preset_slot_bbox.py` — tests `slot_bbox` helper, which is
  independent of this change.

### 8.4 Integration

- `tests/test_compose_walk.py::test_senr_repeat_triangle_resolves` —
  may need the expected transform to match the new centered result
  (identity in this case, since repeat_triangle cells are square).

### 8.5 Manual smoke

After the plan merges:

1. `olik extract auto --count 10 --seed 99` on the host DB (adds 10
   fresh rows with the new compose behavior).
2. Open admin UI, review a few of the new rows alongside old rows
   (seed 7 rows from Plan 10 verification) via direct URLs. The
   difference should be visually obvious for 口-radical chars.
3. Run `olik extract report` — compare verified/needs_review/
   failed_extraction distribution. No regression expected.

## 9. Risks & open questions

- **Letterbox whitespace may look worse than stretching for reviewers
  used to the stretched version.** This is subjective. The honest
  answer is "the stretched version was wrong; letterboxed is closer to
  correct but not yet ideal — Plan 10.2 closes the gap." If reviewers
  find the whitespace distracting, a follow-up can shade it or pre-
  crop the canonical to its own stroke union bbox before calling
  `fit_in_slot` (which would effectively remove the whitespace by
  tightening `src` — tracked as a possible Plan 10.1.1 if needed).
- **IoU-per-stroke measurement** (`compose.iou.iou_report_for`) does
  positional bbox matching between composed and MMH strokes. The fix
  moves composed strokes into smaller bboxes, which may or may not
  improve IoU depending on whether MMH's corresponding strokes occupy
  the same tight region. Expectation: IoU should improve for radicals
  (since MMH also puts them tight in the corner) and stay flat for
  full-height body components.
- **Hand-authored entries in `extraction_plan.yaml`.** The 4 seeds go
  through the same preset adapters; no manual override path. Their
  rendered output will shift per Section 7. If any seed's IoU drops
  below the gate, the plan commit updates the seed's expected IoU
  baseline alongside.
- **`ApplyRepeatTriangle` centering.** Today's non-uniform affine on a
  square cell + square canonical produces the same output as uniform
  scale + center anchor. So this should be a literal no-op visually.
  If tests disagree, the test expectations are stale and get updated.

## 10. Out of scope / follow-ups

- **Plan 10.2** — MMH-informed per-char slot weights. Replaces the
  hardcoded `weight_l`, `weight_top`, `padding` with per-char values
  derived from context stroke distribution. Closes the "slot is still
  too wide" side of the 囀 problem.
- **Plan 10.1.1** (possible follow-up) — crop canonical to its stroke
  union bbox before `fit_in_slot`. Tightens letterboxing for canonicals
  that don't fill their 1024² frame. Small change, useful polish.
- **Additional anchors** (`top-right`, `left-center`, etc.) — add when
  a specific preset layout demands them. Not needed for the 4 presets
  we ship today.

## 11. Migration / compatibility

- No schema changes.
- No API changes on `@olik/glyph-db` or the TS admin app.
- Python API change: `fit_in_slot` is a new public function on
  `olik_font.geom`. No existing consumer calls it today.
- `apply_*` function signatures unchanged (keep the same keyword
  parameters that are already `del`-ignored per Plan 09.1).
- Pre-Plan-10.1 DB rows keep their old `stroke_instances` (stretched
  renders). A re-extraction via `olik extract auto` or
  `olik extract retry` re-runs compose and produces the new anchored
  renders.
- `olik db export` round-trips naturally — the shape of
  `stroke_instances` is unchanged; only the numerical values shift.
