---
title: Session handover — 2026-04-22 (pm)
created: 2026-04-22
tags: [type/handover]
source: self
status: active
supersedes: "[[handover-2026-04-22]]"
---

# Session handover — 2026-04-22 (pm)

> **Read this first when resuming.** Plan 09.2 (variant extraction correctness) is merged as PR #10 on main. Post-merge host-DB verification surfaced a design-level issue: the per-stroke-floor gate (0.30) rejected too many real-world pairings because CJK components routinely cross preset slot boundaries (e.g. 木 in 李 spans y=[385..851] across the top_bottom y=542 split). Hungarian produced zero-IoU assignments that tripped the floor and forced `failed_extraction` on ~27 chars per 100 that Plan 09.1 would have rendered as `needs_review`. Fixed in this handover commit: `below_floor` now falls back to canonical reuse (Plan 09.1 behavior) rather than `PlanFailed`. Supersedes [[handover-2026-04-22]].

## TL;DR — resume here

1. **PR #10 merged** (`2fc1b90`): Plan 09.2 wiring is in — new `olik_font.bulk.variant_match` Hungarian matcher, `slot_bbox` preset helper, real canonical probe in `batch.py`, `variants_minted` / `canonical_probe_rejections` counters on `extraction_run`, `variant_of` edges plumbed through.
2. **Plan 09.2 follow-up fix in this handover commit:** `bulk/planner.py` `below_floor` branch now falls back to canonical reuse (prototype_ref = canonical.id) instead of `PlanFailed`. Spec updated inline at §6.
3. **Host-DB verification green (post-fix):** `olik extract auto --count 100 --seed 7` on a fresh DB produces:
   - `verified` 1
   - `needs_review` 64
   - `unsupported_op` 22
   - `failed_extraction` 13
   - `canonical_probe_rejections` 28
   - `variants_minted` 0
4. **Zero variants minted on real data.** The slot-based bbox-IoU matcher is too strict for CJK's slot-crossing components. The Plan 09.2 infrastructure (matcher, probe, counters, edges) is in place but effectively dormant until Plan 09.3 replaces bbox IoU with shape/median-based matching.
5. **Net effect of Plan 09.2 vs Plan 09.1:** usable output unchanged (~65 rows `verified + needs_review` out of 100 either way). Added infrastructure for future plans; no regression.
6. **Main is clean, pushed to origin.** 162 pytest + 1 xfail.

## Current state

### Git

| Thing | Ref |
|---|---|
| main | `<this handover commit>` (see `git log --oneline -5` when resuming) |
| origin | `github.com/GiantCroissant-Lunar/olik-font` |
| Open PRs | none |
| Tags | plan-01 through plan-09 + `plan-09.2-variant-extraction` + `pass-1-complete` |

Today's pm commit sequence (oldest → newest):

```
0a96f34 docs(spec): Plan 09.2 — variant extraction correctness design
375a1ef docs(plan): Plan 09.2 — variant extraction implementation plan
930f00f feat(archon): plan-09.2-variant-extraction workflow
2fc1b90 Plan 09.2: Variant extraction correctness — IoU-per-stroke Hungarian matcher + real canonical probe (#10)
<this> fix(bulk): below_floor falls back to canonical reuse + spec rev + pm handover
```

### SurrealDB (host)

- Endpoint: `http://127.0.0.1:6480`, user `root`, pass `root`, ns/db `hanfont/olik`.
- Re-seeded during post-merge verification — current contents reflect the `olik extract auto --count 100 --seed 7` run:
  - 4 seed glyphs (明 清 國 森) + 100 auto rows = 104 total
  - 1 `verified`, 64 `needs_review`, 22 `unsupported_op`, 13 `failed_extraction` (among the 100)
  - 1 `extraction_run` row with the post-fix counters
  - 0 `variant_of` edges (no variants successfully minted — expected per Plan 09.2 limitations noted above)

### TS workspace

Unchanged. All packages build + test green (verified in the workflow's `run_ts` + `run_typecheck` + `run_build` nodes before merge).

## Post-merge investigation — the real-data verification

### Baseline run (pre-fix, as shipped in PR #10)

```
olik extract auto --count 100 --seed 7
→ verified 1 | needs_review 38 | unsupported_op 22 | failed_extraction 39
→ variants_minted 0 | canonical_probe_rejections 27
```

**The 39 `failed_extraction`.** Of those, sampling `olik extract list --status failed_extraction --limit 15` showed the dominant failure mode was `match floor: best pairing for <comp> in <char> has min_iou=0.000`. Concrete examples:
- 哲, 喔, 嗦, 囀 — 口 in top_bottom's bottom slot
- 李, 梃, 檢 — 木 in top_bottom's top slot
- 池, 汪 — 氵 in left_right's left slot
- 息 — 心 in top_bottom's bottom slot

Every one of these had a `min_iou = 0.000` — meaning the matcher's best pairing produced zero bbox overlap for at least one canonical stroke.

### Root cause

The probe transforms canonical's stroke bboxes into the preset's slot bbox (e.g. `top_bottom[0]` = `(0, 542, 1024, 1024)`), then Hungarian-matches against context strokes. This assumes the component's strokes neatly fit inside the slot. But real hand-drawn MMH data has components that cross slot boundaries:

Example traced for 李 = `d 木 子`:
- Slot `top_bottom[0]` = `(0, 542, 1024, 1024)`
- 李's 木 strokes actually span y≈[385..851] in 李's canvas (crossing the split)
- 木 standalone's strokes span y≈[-46..842] in standalone canvas
- After affine transform to slot, canonical 木 stroke 0 (bbox y≈[835..900]) gets compared to 李's context strokes — but the 李 strokes that ARE 木 have y ranges partially *below* 542, so they're only a partial overlap with the transformed canonical's upper region. Hungarian is forced to pick some pair, picks one with IoU=0.000.
- `mean_iou=0.123`, `min_iou=0.000`, `below_floor=True` → PlanFailed.

These characters would compose fine if we just used the canonical directly (Plan 09.1 did exactly that and put them in `needs_review`). The per-stroke floor was over-aggressive at rejecting canonical reuse.

### Fix applied in this handover commit

`project/py/src/olik_font/bulk/planner.py` — in the `is_new_variant` branch, after `_extract_variant_prototype` returns with `match.below_floor=True`:

- Before: `return PlanFailed(reason=…)` — stub row, not rendered.
- After: fall back to canonical reuse. The child node's `prototype_ref` is set to the canonical's id (via `decision.canonical_for_edge`). The glyph composes normally; final compose-time IoU gate decides verified vs needs_review, same as Plan 09.1.

`k_gt_m` still fails (canonical genuinely can't work when it has more strokes than the context char has available).

`project/py/tests/test_bulk_planner.py::test_plan_char_below_floor_falls_back_to_canonical_reuse` — replaces the old `test_plan_char_fails_when_match_below_floor` and asserts PlanOk with canonical child refs.

`vault/specs/2026-04-22-variant-extraction-design.md` §6 — failure ladder updated inline, plus a "Revision note (2026-04-22, post-merge verification)" block explaining why the change was needed.

### Post-fix run (this handover commit)

```
olik extract auto --count 100 --seed 7
→ verified 1 | needs_review 64 | unsupported_op 22 | failed_extraction 13
→ variants_minted 0 | canonical_probe_rejections 28
```

Usable output (verified + needs_review) went from 39 → 65. The 13 remaining `failed_extraction` are all genuine data gaps (`no standalone MMH entry for component …` — components like 𠕁, 䒑, 𣏂, 37490 that aren't in MMH). Matches Plan 09.1's baseline usable share.

## Known limitations / follow-ups

### Plan 09.2's variant extraction is effectively dormant on real data

`variants_minted: 0` over 100 chars. The slot-based bbox-IoU matcher cannot handle the boundary-crossing reality of CJK components. The infrastructure (matcher module, probe, counters, `variant_of` edges, `slot_bbox` helper) is all in place, just not producing values. Plan 09.3 should:

1. Replace bbox-IoU cost with either polygon IoU (via shapely, path-to-polygon) OR median-based similarity (MMH's per-stroke medians are already loaded). Median similarity is likely the right choice — it's scale/position-invariant and captures stroke shape directly.
2. Drop or loosen the slot-transform assumption. Alternatives: match in a shared canonical frame (normalize both canonical and context strokes to `(0,0,1,1)`), or use a soft prior where slot position is one feature among several.
3. Expect `verified` lift from 1% toward the original 30–50% target once matching actually disambiguates components.

### Pre-existing limitations (unchanged by Plan 09.2)

- **Unsupported operators** (22% of auto runs): `stl`, `st`, `sl`, `str`, `lock`, `me`, `w`, `wtl`, `d/t`, `d/m`, `sbl`, `wd`, `rrefl`, `ra`. Plan 12 backlog.
- **Missing MMH components** (remaining 13% `failed_extraction`): 𠕁, 䒑, 𣏂, the numeric `37490`, etc. Upstream MMH data gap; no fix short of sourcing alternate data.
- **`國` xfail** in `test_iou_gate`: non-contiguous MMH extraction; sliding-window matcher can't align. Same status as Plan 09.1.

### Archon workflow `create_pr` now safe

The handover's §"Archon workflow create_pr prompt is unsafe" fix landed in `.archon/workflows/plan-09.2-variant-extraction.yaml`: Codex wrote the PR body to `/tmp/pr-body-plan-09.2.md` and called `gh pr create --body-file`, no heredoc. Verified clean in this run — no host-DB contamination. Reuse the same pattern for Plan 10's workflow.

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
# Expected: 162 passed, 1 xfailed (國)

cd ../ts && pnpm -r test
# Expected: all workspace packages green

cd ../.. && lsof -ti:6480 && project/py/.venv/bin/olik extract report
# Expected: filled 104 / 4808, verified 5 (4 seeds + 1 auto), needs_review 64,
#           unsupported_op 22, failed_extraction 13
```

### Picking up Plan 09.3 (matcher upgrade)

If you want to keep pushing on extraction quality before building UI:

1. New module `olik_font.bulk.shape_match` with median-based stroke similarity (or polygon-IoU alternative).
2. Replace the call-site in `variant_match.match_in_slot` or add an alternative matcher that the probe closure in `batch.py` can swap in.
3. Re-run `olik extract auto --count 100 --seed 7` and compare `verified` lift.

### Picking up Plan 10 (admin UI)

First UI consumer of `variant_of` edges (currently empty until 09.3 populates them). Plan 10's scope is unchanged from what [[handover-2026-04-22]] described — refine/react-admin shell, virtualized grid, status filters, detail drawer with xyflow views, reserved Style Variants tab.

### Stale worktree cleanup

`archon isolation cleanup --merged` still reports `archon/task-plan-09-2-variant-extraction` as "has uncommitted changes" — that's the workflow file being present in the worktree but not committed on the branch. Manually remove:

```bash
git worktree remove --force ~/.archon/worktrees/plate-projects/olik-font/archon/task-plan-09-2-variant-extraction
git branch -D plan-09.2-variant-extraction 2>/dev/null || true
```

(The remote branch was already deleted by `gh pr merge --delete-branch`.)

## Commits landed this session (am + pm)

```
<this handover commit> — planner below_floor fallback + spec rev + pm handover
930f00f feat(archon): plan-09.2-variant-extraction workflow
375a1ef docs(plan): Plan 09.2 — variant extraction implementation plan
0a96f34 docs(spec): Plan 09.2 — variant extraction correctness design
2fc1b90 Plan 09.2: Variant extraction correctness — IoU-per-stroke Hungarian matcher + real canonical probe (#10)
```

## Reference trail

- Plan 09.2 design: [[2026-04-22-variant-extraction-design]]
- Plan 09.2 plan: [[2026-04-22-09.2-variant-extraction]]
- Prior handover: [[handover-2026-04-22]]
- PRs this session: https://github.com/GiantCroissant-Lunar/olik-font/pull/10
