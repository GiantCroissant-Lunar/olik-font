---
title: "Plan 09.2 — Variant extraction correctness (design)"
created: 2026-04-22
tags: [type/spec, topic/scene-graph, topic/extraction]
status: draft
supersedes: null
relates-to:
  - "[[2026-04-21-bulk-extraction-design]]"
  - "[[handover-2026-04-22]]"
---

# Plan 09.2 — Variant extraction correctness (design)

## 1. Context & motivation

Plan 09 delivered the bulk extraction pipeline (`olik extract auto/report/list/retry/backfill-status`). Plan 09.1 fixed two correctness bugs in canonical prototype extraction and preset y-up bbox semantics.

Two residual gaps remain, both called out in [[handover-2026-04-22]] as Plan 09.2 work:

1. **Canonical probe is a stub.** `bulk/reuse.decide_prototype` uses `probe_iou(canonical)` to decide canonical-reuse vs variant mint. The current implementation (`_trivial_probe_iou` in `bulk/batch.py`) always returns `1.0`, so the variant branch never fires. Every component resolves to the canonical, even when the canonical is a poor fit for the context char's slot.
2. **Variant branch is disabled.** `bulk/planner.plan_char`'s `is_new_variant` arm returns `PlanFailed` because we have no reliable way to slice a context char's strokes into per-component indices. MMH's per-stroke `matches` field — which would give us component-to-stroke assignment — is null for all 9574 entries.

The empirical effect: post-Plan-09.1, ~60 of 100 random chars land as `needs_review` with IoU in the 0.65..0.89 range. Most are cases where the canonical is structurally right but geometrically misaligned for this specific context — exactly the problem a context variant is meant to solve. Zero `variant_of` edges exist in the DB today.

Plan 09.2 closes both gaps. It replaces the trivial probe with real IoU-per-stroke matching and enables the variant branch to mint `PrototypePlan` records with stroke indices derived from that matching.

Expected effect on a fresh `olik extract auto --count 100 --seed 7` run:

- `verified` 1–5% → ~30–50%
- `needs_review` 60–65% → 15–25%
- `unsupported_op` and `failed_extraction` largely unchanged (still gated by the LUT and MMH data gaps)

## 2. Goals

- Implement `bulk.variant_match` with Hungarian assignment (scipy `linear_sum_assignment`) over canonical-vs-context stroke bbox-IoU.
- Replace `_trivial_probe_iou` with a real probe backed by the same matching call — probe score = matched mean IoU.
- Mint context variants in `planner.plan_char` when the probe falls below the gate; variant's `stroke_indices` are the matched context-char indices.
- Write `variant_of` edges for every minted variant, with `reason = "iou_fallback"`.
- Add observability counters to `extraction_run.counts`: `variants_minted`, `canonical_probe_rejections`.
- Make `olik extract retry --status needs_review` / `--status failed_extraction` re-process existing rows through the new pipeline.
- Deduplicate slot-bbox math: extract a pure `constraints.presets.slot_bbox(preset, n, i)` helper that both the preset renderers and the variant-matching probe consume.

## 3. Non-goals

- No polygon-level IoU. Bbox IoU continues as the matching score. Polygon IoU is a separate fidelity axis tracked as Plan 09.3.
- No new compose modes. `unsupported_op` rows stay failed until Plan 12 expands the operator LUT.
- No speculative post-compose verification of a minted variant. Variant by construction matches exact context strokes, so IoU is guaranteed to beat the canonical's probe score modulo preset bugs — those are regression-tested in Plan 09.1 and `test_preset_slot_bbox.py` below.
- No TS consumer changes. Plan 10 (admin UI) is the first reader of `variant_of` edges.
- No change to the 4 hand-tuned seed prototypes (`proto:sun`, etc.). Auto-planned glyphs continue to use `proto:u<hex>` canonicals; variants are `proto:u<hex>_in_<context>`.

## 4. Architecture overview

Single additional matching step inside the existing `plan_char` loop:

```
plan_char(林, cjk_entry, mmh, proto_index)
│
├─ resolve_mode("a") → "left_right"
│
└─ for each component (木, 木) at slot_idx i:
     │
     ├─ canonical = proto_index.canonical_for(木)              # proto:u6728
     │
     ├─ match = variant_match.match_in_slot(                   ◄─── NEW
     │      canonical_strokes = MMH[木].strokes,
     │      context_strokes   = MMH[林].strokes,
     │      slot              = presets.slot_bbox("left_right", 2, i),
     │      per_stroke_floor  = 0.30,
     │   )
     │
     ├─ probe_iou = match.mean_iou                             ◄─── real probe
     │
     ├─ if canonical missing            → mint canonical (existing)
     ├─ elif match.k_gt_m               → PlanFailed (canonical has more strokes than context)
     ├─ elif match.below_floor          → PlanFailed (any pair < 0.30)
     ├─ elif probe_iou ≥ gate (0.90)    → reuse canonical
     ├─ elif variant_cap exceeded       → PlanFailed (existing cap)
     └─ else                            → mint variant with
                                            from_char        = 林,
                                            stroke_indices   = tuple(p.context_idx for p in match.pairs),
                                          + variant_edges.append((variant.id, canonical.id))
```

Probe and variant extraction share the same matching call. One Hungarian solve yields both the reuse/mint decision score and the stroke indices needed for the variant.

## 5. Module layout

### 5.1 New: `project/py/src/olik_font/bulk/variant_match.py`

```python
from dataclasses import dataclass

from olik_font.types import BBox


@dataclass(frozen=True)
class StrokePair:
    canonical_idx: int
    context_idx:   int
    iou:           float


@dataclass(frozen=True)
class MatchResult:
    pairs:        tuple[StrokePair, ...]
    mean_iou:     float
    min_iou:      float
    k_gt_m:       bool           # canonical stroke count > context stroke count
    below_floor:  bool            # at least one matched pair below per_stroke_floor


def match_in_slot(
    canonical_strokes: list[str],     # SVG path-d strings from MMH
    context_strokes:   list[str],
    slot:              BBox,
    per_stroke_floor:  float = 0.30,
) -> MatchResult:
    """Hungarian bbox-IoU assignment of canonical strokes to context strokes.

    1. Compute canonical's union bbox; derive affine to slot.
    2. Transform each canonical stroke's bbox into slot frame.
    3. Build K×M cost = 1 - bbox_iou for each pair.
    4. If K > M, return MatchResult(k_gt_m=True, mean_iou=0.0, ...).
    5. Solve with scipy.optimize.linear_sum_assignment.
    6. Materialize pairs; flag below_floor if any pair.iou < per_stroke_floor.
    """
```

### 5.2 Touch: `constraints/presets.py`

Extract slot-bbox math duplicated inside `apply_left_right` / `apply_top_bottom` / `apply_enclose` / `apply_repeat_triangle` into a pure helper:

```python
def slot_bbox(
    preset:       str,                     # "left_right" | "top_bottom" | "enclose" | "repeat_triangle"
    n_components: int,
    slot_idx:     int,
    glyph_bbox:   BBox = (0, 0, 1024, 1024),
) -> BBox:
    """Return the y-up bbox for component `slot_idx` in `preset`.

    y-up is invariant throughout the pipeline; Plan 09.1 fixed this.
    Used by both apply_* renderers and variant_match.match_in_slot.
    """
```

The existing `apply_*` functions call `slot_bbox` internally. Behavior is unchanged (Plan 09.1's y-up fix stays intact) — this is pure deduplication.

### 5.3 Touch: `bulk/reuse.py`

`decide_prototype` signature gains three arguments needed to compute the slot:

```python
def decide_prototype(
    component_char:   str,
    context_char:     str,
    preset:           str,
    n_components:     int,
    slot_idx:         int,
    index:            ProtoIndex,
    probe_iou:        Callable[[str, str, str, int, int], float],
    gate:             float,
    cap:              int,
) -> ReuseDecision: ...
```

`probe_iou(component_char, context_char, preset, n_components, slot_idx)` returns the matched mean IoU. The closure is built in `batch.py` with `mmh` and `proto_index` captured; `preset`, `n_components`, and `slot_idx` are passed at call time because `plan_char` knows them per-component. Keeping `probe_iou` as a callable preserves testability (unit tests pass deterministic stub probes).

### 5.4 Touch: `bulk/planner.py`

`plan_char` passes `preset`, `n_components`, `slot_idx` into `decide_prototype`.

The `is_new_variant` branch becomes:

```python
elif decision.is_new_variant:
    match = variant_match.match_in_slot(
        canonical_strokes = _stroke_paths(mmh[comp_name]),
        context_strokes   = _stroke_paths(mmh[char]),
        slot              = presets.slot_bbox(mode, len(components), i),
    )
    if match.k_gt_m or match.below_floor:
        return PlanFailed(reason=…)
    variant = PrototypePlan(
        id               = decision.chosen_id,
        name             = comp_name,
        from_char        = char,
        stroke_indices   = tuple(p.context_idx for p in match.pairs),
        roles            = ("meaning",),
        anchors          = {},
    )
    new_protos.append(variant)
    variant_edges.append((variant.id, decision.canonical_for_edge))
```

### 5.5 Touch: `bulk/batch.py`

- Build the real `probe_iou` closure:
  ```python
  def make_probe(mmh, proto_index):
      def probe(component_char, context_char, preset, n_components, slot_idx):
          canonical = proto_index.canonical_for(component_char)
          if canonical is None or component_char not in mmh or context_char not in mmh:
              return 0.0
          match = variant_match.match_in_slot(
              canonical_strokes = _stroke_paths_for_proto(canonical, mmh),
              context_strokes   = _stroke_paths(mmh[context_char]),
              slot              = presets.slot_bbox(preset, n_components, slot_idx),
          )
          return match.mean_iou if not (match.k_gt_m or match.below_floor) else 0.0
      return probe
  ```
- Write `variant_of` edges via the existing sink helper (Plan 09's `sync_protos_and_variants`; verify it actually runs now that `variant_edges` is populated).
- Increment counters on `extraction_run`:
  - `counts.variants_minted` — per mint.
  - `counts.canonical_probe_rejections` — per time probe < gate, regardless of downstream outcome (variant mint vs PlanFailed).

### 5.6 `extraction_run.counts` additions

```
counts: {
    verified:                       int,
    needs_review:                   int,
    unsupported_op:                 int,
    failed:                         int,
    variants_minted:                int,   # NEW
    canonical_probe_rejections:     int,   # NEW
}
```

No schema change required — `counts` is `option<object>` (Plan 09 §5.3).

## 6. Failure ladder

Evaluated in order; first match wins:

| Condition | Outcome |
|---|---|
| Operator unsupported | `PlanUnsupported` (existing) |
| MMH missing context char | `PlanFailed` (existing) |
| Canonical missing — mint via standalone MMH | PlanOk with new canonical (existing, Plan 09.1) |
| K > M (canonical strokes > context strokes) | `PlanFailed` |
| variant cap already hit for this canonical | `PlanFailed` (existing, Plan 09) |
| `mean_iou ≥ 0.90` (probe gate) | Reuse canonical |
| `min_iou < 0.30` (per-stroke floor) | **Reuse canonical** (fall back to Plan 09.1 behavior) |
| otherwise | Mint variant; write `variant_of` edge |

**Revision note (2026-04-22, post-merge verification):** The original spec had
`min_iou < 0.30 → PlanFailed`. Real-data verification surfaced that CJK
components routinely cross slot boundaries (e.g. 木 in 李 spans y=[385..851]
across the top_bottom y=542 split), so Hungarian often produces zero-IoU
pairings even when canonical reuse would render correctly. Failing these
cases moved ~27 chars per 100 from Plan 09.1's `needs_review` to
`failed_extraction` — a regression in usable output. Changed the ladder so
`below_floor` falls back to canonical reuse; the final compose-time IoU
gate still decides verified vs needs_review. Variant minting is now gated
on the matcher actually finding clean pairs (above floor). Plan 09.3 will
replace bbox IoU with a shape/median-based matcher that handles boundary-
crossing components correctly.

## 7. CLI

No new commands. The following existing commands flow through the new pipeline automatically:

- `olik extract auto --count N --seed K` — default run path.
- `olik extract retry --status needs_review` — re-processes existing `needs_review` rows. Expected lift: most to `verified`, residual stays at `needs_review` where the canonical was already near-gate and variant doesn't help (unusual).
- `olik extract retry --status failed_extraction` — re-processes existing stubs; covers the post-Plan-09.1 cases that landed as failed because the variant branch was disabled.
- `olik extract report` — status breakdown now reflects non-zero `variants_minted` under the latest `extraction_run`.

## 8. Testing strategy

### 8.1 Unit

- `test_variant_match.py`:
  - Synthetic canonical = 2 unit-box strokes, context = same 2 strokes repositioned into slot; assert both pairs IoU ≈ 1.0.
  - K > M case: canonical has 3 strokes, context has 2; assert `k_gt_m=True`.
  - Below-floor case: canonical and context strokes deliberately misaligned; assert `below_floor=True` and correct flag.
  - Permutation invariance: shuffle context stroke order; pairing remains the same canonical → context ground-truth indices.

- `test_preset_slot_bbox.py`:
  - `slot_bbox("left_right", 2, 0)` returns `(0, 0, 512, 1024)`, `(_, 1)` returns `(512, 0, 1024, 1024)`.
  - `slot_bbox("top_bottom", 2, 0)` returns y-up upper half (HIGH y = visual top, Plan 09.1 convention).
  - `slot_bbox("repeat_triangle", 3, i)` returns the three triangle cells with HIGH y for top-center.
  - Regression guard: `apply_top_bottom` and `apply_repeat_triangle` produce identical bboxes before/after refactor.

- `test_bulk_reuse.py` (extend):
  - `decide_prototype` with stub `probe_iou` returning 0.85 → `is_new_variant=True`.
  - With 0.95 → reuse canonical.
  - With cap exceeded → `cap_exceeded=True`.

- `test_bulk_planner.py` (extend):
  - `plan_char` for a context char where canonical's probe < gate yields `PlanOk` with one `new_prototype` (the variant) and one `variant_edge`.
  - `plan_char` where context char has fewer strokes than canonical yields `PlanFailed`.

### 8.2 Integration

- `test_bulk_variant_smoke.py` (new):
  - `run_batch(count=10, seed=7)` on the ephemeral DB fixture.
  - Assert at least one `variant_of` edge is written.
  - Assert `extraction_run.counts.variants_minted >= 1`.
  - Assert post-batch `verified` share is strictly greater than a baseline run with `probe_iou` stubbed back to 1.0 (regression guard against future changes that accidentally re-disable the probe).

### 8.3 End-to-end (manual, post-merge)

- `task db:reset && project/py/.venv/bin/olik extract auto --count 100 --seed 7`.
- Expected: `verified` 30–50%, `needs_review` 15–25%. Compare against handover's current baseline.
- `project/py/.venv/bin/olik extract retry --status needs_review` — expect most existing needs_review rows to lift.

## 9. Risks & open questions

- **Probe gate too aggressive.** If 0.90 triggers variant mint for chars that would have been fine with the canonical, we produce unnecessary variant rows. Mitigation: `extraction_run.counts.variants_minted / (variants_minted + verified_via_canonical)` serves as a health metric. If > 80%, consider loosening the probe gate to 0.75 in a follow-up.
- **Preset slot-bbox assumption.** `match_in_slot` assumes the canonical belongs in the straightforward `slot_bbox` rectangle. `enclose` — where an outer component wraps an inner — may have non-rectangular "inside" semantics that this helper simplifies. Acceptable for Plan 09.2; the IoU gate catches mismatches and routes them to `needs_review`.
- **Hungarian is global-optimal under a local cost.** Bbox IoU ignores stroke shape, so the optimal assignment under cost=1-bboxIoU can still be wrong when two context strokes have near-identical bboxes. In practice: rare; when it happens it yields mean_iou near canonical's natural fit and the char either reuses canonical (if ≥ gate) or lands in `needs_review` after composition. Plan 09.3's polygon IoU would disambiguate.
- **`decide_prototype` signature change** is a breaking API change inside the `bulk` package. All call sites are inside `olik_font.bulk`; no external consumers. Mechanically safe; tests updated in the same change.

## 10. Out of scope / follow-up plans

- **Plan 09.3** — polygon-level IoU (shapely + path-to-polygon) for both the matching score and the final `iou_mean` measurement. Addresses the "two context strokes with similar bboxes" ambiguity.
- **Plan 10** — admin UI. First UI consumer of `variant_of` edges; renders the canonical→variant lineage graph.
- **Plan 12** — operator LUT expansion (`stl`, `st`, `sl`, `str`, `lock`, `me`, `w`, `wtl`, `d/t`, `d/m`, `sbl`, `wd`, `rrefl`, `ra`). Unlocks currently-`unsupported_op` rows.
- **Archon workflow `create_pr` safety** — the bad heredoc pattern in `.archon/workflows/plan-09-bulk-extraction.yaml` must be patched to `gh pr create --body-file <tmpfile>` before the next Archon workflow runs. Flagged in [[handover-2026-04-22]] §"Archon workflow create_pr prompt is unsafe".

## 11. Migration / compatibility

- No schema changes — `variant_of` table and `counts` object already exist from Plan 09.
- No data migration — existing rows are re-processable via `olik extract retry`.
- `decide_prototype` signature change is internal to `olik_font.bulk`; no external breakage.
- The 4 hand-tuned seed prototypes continue to be used for 明/清/國/森; their `variant_of` graph remains empty (intentional — seeds are hand-authored, not extracted).
