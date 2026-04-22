---
title: Session handover — 2026-04-22 (evening)
created: 2026-04-22
tags: [type/handover]
source: self
status: active
supersedes: "[[handover-2026-04-22-pm]]"
---

# Session handover — 2026-04-22 (evening)

> **Read this first when resuming.** Two big wins today (Plan 09.2 + Plan 10 both merged and reviewed end-to-end through a working admin UI) plus a revert: Plan 10.1 (aspect-preserving slot fit) landed as PR #12, was visually verified against the host DB via the admin UI, and then reverted because it traded one layout bug for another. Plan 10.1's design absorbs into Plan 10.2, which will ship the two concerns together: aspect-preserving fit **and** per-char MMH-informed slot sizing. Supersedes [[handover-2026-04-22-pm]].

## TL;DR — resume here

1. **Plan 09.2 merged** earlier today. Variant extraction infrastructure in place; matcher produces 0 variants on real data (expected; Plan 09.3 will address). Below-floor fallback to canonical preserves Plan 09.1 baseline output.
2. **Plan 10 merged** — admin review UI on Refine + Mantine 8 (not 9; @refinedev/mantine hadn't shipped Mantine 9 support at workflow time — Codex pinned Mantine 8 per the workflow's fallback rule). React 18.3 → 19.0 workspace upgrade successful, Remotion stayed compatible, no pin-back needed. Four post-merge bugs caught via playwright smoke and committed as `aed657f`.
3. **Plan 10.1 landed and reverted.** Shipped as PR #12, post-merge visual review against 囀 showed the fix traded "fat squashed radical" for "body-component-with-whitespace." Reverted cleanly via `7b9f8d8`. Plan 10.1's spec + plan + workflow docs **stay in the repo** as reference material for Plan 10.2, which expands scope to ship aspect-preservation + slot-sizing together.
4. **Pre-existing `upsert_variant_of_edge` bug fixed** (`65eacd6`). Plan 09.2's smoke happened to mint zero variants so this latent bug never fired; the Plan 10.1 post-merge retry tripped it. Handles both surrealdb-python payload shapes (1.x `[{"result": [...]}]` and 2.x direct list) + switches the RELATE syntax to angle-bracket record IDs instead of `type::record()` (which newer SurrealDB rejects in RELATE).
5. **Main is clean, pushed to origin** at `7b9f8d8`.
6. **Admin UI is live.** `pnpm --filter @olik/admin dev` starts it on port 5174 (or 5175 if 5174 is busy); connect to `127.0.0.1:6480` SurrealDB. Keyboard shortcuts (Y/N/J/K/R/Esc) work in Chrome; playwright's `press_key` dispatches below the `useHotkeys` window-level binding, so click buttons when driving via playwright.

## Current state

### Git

| Thing | Ref |
|---|---|
| main | `7b9f8d8` (Plan 10.1 revert) |
| origin | `github.com/GiantCroissant-Lunar/olik-font` |
| Open PRs | none |
| Tags | plan-01 through plan-09 + plan-09.2 + plan-10 + plan-10.1 + pass-1-complete |

**Note on `plan-10.1` tag:** it was applied at merge time. It remains pointing at the squash commit (`025ca23`) which is now reverted on main — the tag itself stays as a historical marker of the merge. If this is confusing, `git tag -d plan-10.1-aspect-preserving-slot-fit` removes it; I left it in place.

Today's commit sequence (oldest → newest):

```
9f2eb0a Plan 09.2: Variant extraction correctness (#10)  — merged am
c2e532d feat(archon): plan-10 workflow
a863de0 docs(plan): Plan 10
# ... docs commits ...
dd97ad6 Plan 10: Admin review UI (#11)  — merged am-pm
aed657f fix(admin): 4 post-merge bugs
025ca23 Plan 10.1: Aspect-preserving slot fit (#12)  — merged evening
65eacd6 fix(sink): upsert_variant_of_edge handles new surrealdb payload shape
7b9f8d8 Revert "Plan 10.1" (see §"Why Plan 10.1 was reverted")
```

### SurrealDB

Host DB at `127.0.0.1:6480`, ns `hanfont`, db `olik`. Current contents:
- 4 seed glyphs (明 清 國 森) + ~132 auto-extracted rows across runs seed=0/7/99/111.
- 36 `needs_review` rows were re-extracted post-revert via `olik extract retry --status needs_review` — they carry the pre-Plan-10.1 stretched compose shape again. `extraction_run = 9f73pj3kl41sstujc7wu`.
- 1 row (佈?) lifted from needs_review → verified during the Plan-10.1 retry; it stayed verified post-revert because the second retry did not downgrade its status. The retry reports "36 chars retried" because the verified row was excluded from the status filter.

### TS workspace

Everything on React 19.0. Admin app uses Mantine 8.3.x. All 9 packages/apps tests green. `pnpm -r build` produces dist/ for glyph-* packages.

## Why Plan 10.1 was reverted

The spec's recommended approach — uniform scale + per-slot corner anchor — visibly fixed the radical-side of `left_right` compositions (囀's 口 became a proper small square at top-left instead of a stretched full-height column) but regressed the body-side. Body components like 囀's 轉 are square canonicals (from standalone MMH 轉) placed into a tall rectangular slot (604×1024). Under non-uniform scale, 轉 stretches vertically to fill the slot; under Plan 10.1's uniform-scale-with-top-left-anchor, 轉 becomes a 604×604 square anchored top-right with a huge empty bottom half.

Neither "stretched body" nor "square body + whitespace" matches the MMH reference, where 轉 naturally spans full column height. The compose layer doesn't know whether a given component "wants to stretch to fill its slot" (body) or "wants to sit compactly" (radical). Plan 09's ExtractionPlan doesn't tag role (`is_radical: bool`) in a way the presets can see.

**The coupled fix:** Plan 10.2 will size the slot *per-char* from MMH stroke density. For 囀:
- Measure MMH 囀's stroke x-distribution → 口-region is x=[0..~100], 轉-region is x=[~180..1024]
- Set `weight_l = 100/1024 = 0.098` for this specific char instead of the global `0.39`
- Slots become `(0, 0, 100, 1024)` + `(120, 0, 1024, 1024)`
- Non-uniform scale on each slot: 口 at canonical 1024² → 100×1024 (squished to narrow slot, but close to MMH's actual 口 which is also ~100 wide)
- 轉 at canonical 1024² → 900×1024 (slightly stretched but fills the right column)
- Result: matches MMH structurally.

Plan 10.1's `fit_in_slot` helper is still the right tool for the *radical* side — once slots are correctly sized, the tight slot + aspect-preserve combination produces natural radical renders. Plan 10.2 will reintroduce `fit_in_slot` + proper slot sizing together, atomically.

## Plan 10.2 scope (revised from [[2026-04-22-variant-extraction-design]]'s original framing)

Originally Plan 10.2 was "MMH-informed slot weights." After the 10.1 revert, it's absorbing 10.1's scope:

1. **Slot sizing from MMH stroke density.** For each char in the batch, project MMH stroke bboxes onto the layout axis (x for left_right, y for top_bottom), find the natural split point where stroke density transitions, use that ratio as the preset weight.
2. **Aspect-preserving fit within each sized slot.** `fit_in_slot` helper from Plan 10.1 (safe to bring back once slots are per-char-sized).
3. **Per-slot corner anchor.** Same anchor table as Plan 10.1's spec (top-left for left_right, top-center/bottom-center for top_bottom, center for enclose inner + repeat_triangle).
4. **Apply during emit, not during preset adapter.** Slot sizes per-char can't be hardcoded in presets — they need to be computed in the batch orchestrator and passed to compose. This may require extending `GlyphPlan` to carry `slot_overrides` or similar.

The Plan 10.1 spec [[2026-04-22-aspect-preserving-slot-fit-design]] + plan file stay in the repo as reference material for Plan 10.2.

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
# Expected: 164 passed, 1 xfailed

cd ../ts && pnpm -r test
# Expected: all packages green (glyph-db 18, admin 12, inspector 2, etc.)

cd ../.. && task db:up
project/py/.venv/bin/olik extract report
# Expected: filled ~136 / 4808; distribution depends on which retries landed
```

### Admin UI

```bash
cd project/ts/apps/admin && pnpm dev
# Opens http://localhost:5174/ (or 5175 if busy)
# Keyboard shortcuts Y/N/J/K/R/Esc work in Chrome/Firefox; not in playwright.
```

### Starting Plan 10.2 (aspect-preserving fit + MMH-informed slot sizing)

1. Brainstorm session: build on the reverted Plan 10.1 spec. Decide:
   - How to measure stroke density (flat x-projection vs centroid-based).
   - Threshold for the density transition (e.g. where stroke mass drops below 10% of peak).
   - Where to pass slot overrides: extend `GlyphPlan.layout_overrides` or compute inside `batch.py::run_batch` before calling `compose_transforms`.
2. Spec + plan + workflow, same pattern as 10.1.
3. Visual smoke on 囀, 嗦, 哈, 哩, 妃, 圾, 沫 — all left_right radical-small cases.

### Cleanup: `plan-10.1-aspect-preserving-slot-fit` tag

```bash
git tag -d plan-10.1-aspect-preserving-slot-fit
git push origin :refs/tags/plan-10.1-aspect-preserving-slot-fit
```

Optional — I left it in place so the merge-and-revert sequence is traceable. Remove if you prefer clean tag history.

## Commits landed this session (am → evening)

```
7b9f8d8 Revert Plan 10.1 (see §"Why Plan 10.1 was reverted")  — evening
65eacd6 fix(sink): upsert_variant_of_edge handles new surrealdb payload shape
317371e feat(archon): plan-10.1-aspect-preserving-slot-fit workflow  — pre-revert
4a3001b docs(plan): Plan 10.1 — aspect-preserving slot fit implementation plan
f5bb550 docs(spec): Plan 10.1 — aspect-preserving slot fit design
025ca23 Plan 10.1: Aspect-preserving slot fit (#12)  — reverted
aed657f fix(admin): four post-merge bugs from Plan 10 host-DB smoke  — pm
dd97ad6 Plan 10: Admin review UI (#11)  — pm
a863de0 docs(plan): Plan 10
c2e532d feat(archon): plan-10 workflow
# ... earlier docs commits ...
b58d147 fix(bulk): below_floor falls back to canonical reuse  — am
9f2eb0a Plan 09.2: Variant extraction correctness (#10)  — am
```

## Reference trail

- Plan 09.2 spec/plan: [[2026-04-22-variant-extraction-design]] / [[2026-04-22-09.2-variant-extraction]]
- Plan 10 spec/plan: [[2026-04-22-admin-review-ui-design]] / [[2026-04-22-10-admin-review-ui]]
- Plan 10.1 (reverted) spec/plan: [[2026-04-22-aspect-preserving-slot-fit-design]] / [[2026-04-22-10.1-aspect-preserving-slot-fit]]
- Plan 10.2 (next): spec to be written absorbing Plan 10.1's fit_in_slot approach plus new per-char slot sizing
- Prior handover: [[handover-2026-04-22-pm]]
- PRs this session:
  - https://github.com/GiantCroissant-Lunar/olik-font/pull/10 (Plan 09.2)
  - https://github.com/GiantCroissant-Lunar/olik-font/pull/11 (Plan 10)
  - https://github.com/GiantCroissant-Lunar/olik-font/pull/12 (Plan 10.1 — merged then reverted)
