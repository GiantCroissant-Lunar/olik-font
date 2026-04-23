---
title: Session handover — 2026-04-23 (evening)
created: 2026-04-23
tags: [type/handover]
source: self
status: active
supersedes: "[[handover-2026-04-23-morning]]"
---

# Session handover — 2026-04-23 (evening)

> **Read this first when resuming.** Plan 14 (authored decomposition
> layer + prototype graph) implementation **complete on a feature
> branch**, all 13 task commits + tag applied, all kimi visual gates
> passed, all measurements recorded. **Branch is not yet merged to
> `main` and no PR was opened** — the Archon workflow's post-loop gates
> cascaded into skips because `run_py` hit the default 2-min bash node
> timeout (the test surface is past that now). Demo char `丁` flipped
> from `failed_extraction` to `verified` (3331 → 3332). Supersedes
> [[handover-2026-04-23-morning]].

## TL;DR — resume here

1. **Plan 14 design distilled and written.** Spec
   [[2026-04-23-authored-decomp-and-prototype-graph-design]],
   plan [[2026-04-23-14-authored-decomp-and-prototype-graph]],
   workflow `.archon/workflows/plan-14-authored-decomp-and-prototype-graph.yaml`,
   trace ledger `vault/references/plan-14-trace.md`, kimi verdict
   index `vault/references/plan-14-kimi-verdicts/README.md`. All on
   `main` at commit `79595f4`.

2. **Preset-vocabulary scrub merged to main.** Commit `46108ff` on
   `main`. Removed residuals from TS source (`theme.ts`,
   `input-adapter-chip.tsx`), 5 py tests, 3 TS tests, and 4
   remotion-studio fixtures. Plan 14 Task 0 (`b0b7972` on the feature
   branch) added the repo-wide guard test that locks this in.

3. **Plan 14 implementation: 13/13 task commits + tag — on the
   Archon worktree branch, NOT on `main`.**
   Branch: `archon/task-plan-14-authored-decomp-and-prototype-graph-177690`.
   Tag: `plan-14-authored-decomp-and-prototype-graph` at `8d2f785`.
   Worktree path:
   `/Users/apprenticegc/.archon/worktrees/plate-projects/olik-font/archon/task-plan-14-authored-decomp-and-prototype-graph-177690`.

4. **Codex's own regression sweep (inside Task 12) was green:**
   - Python `208 passed, 1 xfailed`
   - TS workspace tests + typecheck + build all passed
   - `olik extract report`: **verified 3332** (3331 + the demo char)

5. **Workflow's post-loop bash gates DID NOT RUN.** `run_py` timed out
   at the default 120000ms; cascade-skipped `run_ts`, `run_typecheck`,
   `run_build`, `check_no_preset_regressions`, `check_trace_ledger`,
   `check_demo_char_verified`, `approve`, `create_pr`. **No PR was
   opened.** The Archon workflow YAML needs explicit `timeout_ms`
   bumps on `run_py` and `run_ts` for the next run (see §Workflow
   YAML fix below).

6. **Demo char (Task 11 proof gate):** `丁`. Authored partition at
   `project/py/data/glyph_decomp/丁.json` (currently only on the
   feature branch). After `olik extract retry --status
   failed_extraction --chars 丁`, `丁` flipped to `verified` with IoU
   `0.999999191166753`. Kimi verdict pass — see
   `vault/references/plan-14-kimi-verdicts/task-11-e2e.md` (on the
   feature branch).

## Current state

### Git

| Thing | Ref |
|---|---|
| `main` HEAD | `79595f4` (Plan 14 docs commit) |
| Feature branch HEAD | `8d2f785` (Task 12, on `archon/task-plan-14-authored-decomp-and-prototype-graph-177690`) |
| Tag | `plan-14-authored-decomp-and-prototype-graph` → `8d2f785` |
| Open PRs | none |
| Recent main-side tags | `v1-seed-plus-styling`, `plan-12-comfyui-styling-bridge`, `v2-partial-3331`, `plan-11-virtual-coordinates-only`, `plan-14-authored-decomp-and-prototype-graph` (only `plan-14` is on the feature branch) |

13 Plan 14 commits ahead of `main`, in order (oldest → newest):

```
b0b7972 feat(test): repo-wide guard against preset vocabulary regrowth                        [Task 0  — guard]
e52750e feat(py): authored decomposition layer (data/glyph_decomp loader)                     [Task 1  — sample 丁]
56c893c feat(py): unified decomposition lookup — authored → animCJK → MMH → cjk-decomp        [Task 2  — 4-seed iou floor 0.9091]
a7803ca feat(py): compose dispatches on RefinementMode (keep|refine|replace)                  [Task 3  — 3 mode tests]
75f9315 feat(sink): prototype graph schema — decomposes_into, appears_in, has_kangxi          [Task 4  — 3 new tables]
adb9485 feat(sink): import MMH radical + etymology into prototype graph                       [Task 5  — has_kangxi=99 / etymology=97 over 100]
baa2e99 feat(sink): compute productive_count per prototype                                    [Task 6  — HanziCraft overlap 0/10 ⚠]
f241ba5 feat(inspector): dagre tree + mode coloring in DecompositionExplorer                  [Task 7  — kimi 4/4 on seeds]
0d1e245 feat(inspector): authoring panel writes data/glyph_decomp/<char>.json                 [Task 8  — vitest 4/4 + smoke save]
7f46870 feat(inspector): PrototypeBrowser view — prototype graph + productive_count           [Task 9  — kimi pass on 月]
a8b73bc feat(py): centroid + inertia spread QA metrics                                        [Task 10 — Pearson 0.9595]
d78281f test(e2e): authored decomposition flow — 丁 failed → verified                         [Task 11 — IoU 0.99999919, kimi pass]
8d2f785 fix(py): regression sweep for unified lookup + geom stats                             [Task 12 — 208 py / TS / build green]
```

### SurrealDB at 127.0.0.1:6480 ns=hanfont db=olik

After Task 11 retry:

```
filled 4798 / 4808
  verified            3332     (was 3331; +1 from 丁)
  needs_review        133
  unsupported_op      0
  failed_extraction   1328     (was 1329; -1)
```

### Plan 14 measurements (recorded values)

| Task | Metric | Value | Note |
|---|---|---|---|
| 0 | preset-vocab violations across 249 files | 0 | guard test |
| 2 | 4-seed `iou_min` after refactor | 0.9091 | matches committed `國` reference |
| 5 | `has_kangxi` over 100-char sample | 99/100 | |
| 5 | `etymology` over 100-char sample | 97/100 | |
| 6 | top-10 `productive_count` overlap with HanziCraft | **0/10** | known issue, see §Plan 15 candidates |
| 7 | kimi pass count on seed-char inspector screenshots | 4/4 | 明 / 清 / 國 / 森 |
| 9 | kimi verdict on `/proto/u6708` (月) | pass | central node + appears_in correct |
| 10 | Pearson(`iou_mean`, `1 − centroid_dist/scale`) over 4808 | **0.9595** | gate ≥ 0.5 |
| 11 | demo char status flip | `failed_extraction` → `verified` | 丁 |
| 11 | demo char composed IoU | 0.99999919 | |
| 11 | kimi verdict on composed-vs-MMH side-by-side | pass | |
| 12 | `verified_count` after retry | 3332 | baseline 3331 + 丁 |
| 12 | regression sweep — pytest | 208 passed, 1 xfailed | run inside worktree by Codex |
| 12 | regression sweep — TS workspace test+typecheck+build | passed | |

Trace ledger (16 rows total): `vault/references/plan-14-trace.md` on the
feature branch.

### Kimi verdict transcripts (immutable, on feature branch)

`vault/references/plan-14-kimi-verdicts/`:
- `task-07-decomp-explorer.md` + `task-07-screens/` (4 PNGs)
- `task-09-proto-browser.md` + `task-09-proto-browser.png`
- `task-11-e2e.md` + `task-11-e2e-{composed,reference,side-by-side}.png`
- `README.md` (naming + immutability rules)

### Authored decomposition layer (on feature branch)

`project/py/data/glyph_decomp/`:
- `丁.json` — only authored override so far. Hand-authored partition
  for the demo char; serves both as Task 1's sample and Task 11's
  proof input.

## What's NOT done (resume options)

### 1. Merge / PR the feature branch

The 13 Plan 14 commits + tag sit on
`archon/task-plan-14-authored-decomp-and-prototype-graph-177690` only.
Pick one:

```bash
# Option A: open PR (recommended — gives reviewer a checkpoint)
cd /Users/apprenticegc/.archon/worktrees/plate-projects/olik-font/archon/task-plan-14-authored-decomp-and-prototype-graph-177690
git push -u origin archon/task-plan-14-authored-decomp-and-prototype-graph-177690
gh pr create --title "Plan 14: Authored decomposition layer + prototype graph" \
  --body-file /tmp/pr-body-plan-14.md       # write body separately first per the safety pattern in the YAML

# Option B: fast-forward main locally if you want to skip review
cd /Users/apprenticegc/Work/lunar-horse/plate-projects/olik-font
git checkout main
git merge --ff-only archon/task-plan-14-authored-decomp-and-prototype-graph-177690
git push origin main
git push origin plan-14-authored-decomp-and-prototype-graph
```

PR body skeleton: see the `create_pr` node body in
`.archon/workflows/plan-14-authored-decomp-and-prototype-graph.yaml`
(it was never invoked but the body template is ready to copy).

### 2. Re-run the missed Archon gates locally

Codex's Task-12 sweep was green inside the worktree, but if you want
the host environment also confirmed before merging:

```bash
cd /Users/apprenticegc/Work/lunar-horse/plate-projects/olik-font
git checkout archon/task-plan-14-authored-decomp-and-prototype-graph-177690 -- .   # or just cd into the worktree
cd project/py && .venv/bin/pytest -q                                                # ~3-4 min — past the 120s YAML default
cd ../ts && pnpm install && pnpm -r test && pnpm -r typecheck && \
            pnpm -r --filter '!@olik/remotion-studio' build
.venv/bin/olik extract report                                                       # expect: verified 3332
```

### 3. Workflow YAML fix (so re-runs don't cascade-skip)

`.archon/workflows/plan-14-authored-decomp-and-prototype-graph.yaml`
needs explicit timeouts on the heavy bash nodes:

```yaml
- id: run_py
  depends_on: [implement]
  timeout_ms: 600000      # 10 min — current default 120000 is too short
  bash: |
    set -e
    cd project/py && .venv/bin/pytest -q 2>&1 | tail -25

- id: run_ts
  depends_on: [run_py]
  timeout_ms: 600000      # workspace test + install will also push past 2 min now
  bash: |
    set -e
    cd project/ts
    pnpm install --frozen-lockfile=false 2>&1 | tail -3
    pnpm -r test 2>&1 | tail -30
```

Same for any future workflow whose surface area is comparable.

## Plan 15 candidates (surfaced by Plan 14 measurements)

### A — Canonicalize `productive_count` aggregation (high priority)

Task 6 measured `0/10` overlap with HanziCraft's published top
productive components. Root cause (recorded honestly in
[plan-14-productive-counts-2026-04-23.md](vault/references/plan-14-productive-counts-2026-04-23.md)
on the feature branch): the `uses` edges point to per-instance
prototype IDs (e.g. `proto:u6708_in_明_2`) rather than canonical
prototypes (e.g. `proto:u6708`/月). The `variant_of` edges that
*should* canonicalize aren't aggregating in the metric. The plumbing
works; the aggregation is wrong.

Plan 15 task: walk `variant_of` to root before grouping in
`compute_productive_counts`. Acceptance: re-measure HanziCraft
overlap; should land in the 6/10–9/10 range (the original Plan 14
acceptance threshold).

### B — Bulk authoring of failed chars

Plan 14 built the **authoring loop**; the 1328 remaining
`failed_extraction` chars need someone (or an LLM) to actually use
it. Two approaches:

1. **UI-driven, human-in-the-loop.** Inspector's AuthoringPanel
   exists; just open each failed char and author. Slow but
   high-quality.
2. **Agent-driven.** Spawn a subagent per failed char with the MMH
   data + animCJK fallback + cjk-decomp + Inspector screenshot, ask
   it to propose a partition, save the JSON, run the retry, kimi-verify
   the result. Fast but needs guardrails so authoring doesn't drift.

Both compatible with the current architecture; neither needs
schema changes.

### C — Style failed-but-now-verified chars through ComfyUI

Each char authored via the new flow inherits all of v1's styling
machinery, but no batch run has been done since Plan 12. The
`olik style --all-verified` path still has the harvest bug from the
previous handover (`execution_cached` returns empty `outputs`). Fix
that first, then sweep the 3332 verified through ink-brush.

### D — `data/glyph_decomp/` formatter discipline

The 丁 sample was hand-formatted; the inspector authoring panel
emits in a slightly different style. Add a `pre-commit` hook that
canonicalises authored JSON files (sorted keys, 2-space indent, EOL
trailing newline) so the diff stays clean as more chars are
authored.

## Memory (added this session)

Two new feedback memories at
`~/.claude/projects/-Users-apprenticegc-Work-lunar-horse-plate-projects-olik-font/memory/`:

- `feedback_archon_kimi_standard_tooling.md` — Archon and kimi CLI
  are established tooling; just launch via
  `env -u CLAUDECODE archon` and call `kimi` like
  `scripts/verdict_v2.py` does. Don't pre-flight "is it installed?"
  questions.
- `feedback_verify_before_claiming.md` — observe → verify → announce,
  never observe → announce. False progress reports erode credibility
  worse than silence. Hard-learned during the wake-up + Monitor
  episode this session.

These join the standing rules:
- `feedback_virtual_coordinates.md` (binding geometry rule)
- `feedback_visual_verifier_model.md` (never substitute smaller vision models)

## How to resume

### Environment

```bash
cd /Users/apprenticegc/Work/lunar-horse/plate-projects/olik-font
set -a; source infra/.env 2>/dev/null; set +a
alias arc='env -u CLAUDECODE archon'
```

### Sanity checks (on `main`)

```bash
cd project/py && .venv/bin/pytest -q -k 'not preset_vocabulary_guard'
# Expected: ~185 passed, 1 xfailed (same as plan-13 baseline; the
# guard test only exists on the feature branch).
```

### Sanity checks (on the feature branch / after merge)

```bash
cd project/py && .venv/bin/pytest -q
# Expected: 208 passed, 1 xfailed (Plan 14 added ~24 tests across 8 files).
```

### Visual gallery

`/tmp/plan13-gallery/index.html` — still valid (3464 clickable chars).
After the demo char is in `verified`, re-running the gallery snippet
will include `丁`.

### Inspector

```bash
pnpm --filter @olik/inspector dev   # http://localhost:5176
```

After merging Plan 14:
- `/glyph/<char>` — DecompositionExplorer with dagre + mode chips +
  AuthoringPanel for any verified or failed char that has a record
  in `public/data/`.
- `/proto/u6708` — new PrototypeBrowser view for 月.
- `/api/authored-save` — localhost-only writer for
  `data/glyph_decomp/<char>.json`.

## Reference trail

- Spec: `[[2026-04-23-authored-decomp-and-prototype-graph-design]]`
- Plan: `[[2026-04-23-14-authored-decomp-and-prototype-graph]]`
- Workflow: `.archon/workflows/plan-14-authored-decomp-and-prototype-graph.yaml`
- Trace ledger: `vault/references/plan-14-trace.md` (on feature branch)
- Kimi verdict transcripts: `vault/references/plan-14-kimi-verdicts/` (on feature branch)
- Measurement reports: `vault/references/plan-14-{productive-counts,geom-stats}-2026-04-23.md` (on feature branch)
- Geometry skill (binding, unchanged): `.agent/skills/05-engine/glyph-geometry/SKILL.md`
- Discussion threads (the ideas this plan realises):
  `vault/references/discussion/discussion-0003.md`,
  `vault/references/discussion/discussion-0004.md`
- Predecessor handover: [[handover-2026-04-23-morning]]
- Predecessor plans / tags: Plan 11 (`plan-11-virtual-coordinates-only`),
  Plan 12 (`plan-12-comfyui-styling-bridge`), Plan 13 partial
  (`v2-partial-3331`).
