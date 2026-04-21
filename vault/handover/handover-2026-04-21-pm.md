---
title: Session handover — 2026-04-21 (PM)
created: 2026-04-21
tags: [type/handover]
source: self
status: active
supersedes: "[[handover-2026-04-21]]"
---

# Session handover — 2026-04-21 (PM)

> **Read this first when resuming.** Covers everything from the AM handover forward: Archon install + migration, Plans 01/02/03 execution, multi-CLI validation, quickview app, and the one real bug that surfaced (清 stroke-count mismatch). The earlier [[handover-2026-04-21|AM handover]] describes project origin + setup state pre-Archon; this one supersedes its "Open items" list.

## TL;DR — resume here

1. **Fix `project/py/data/extraction_plan.yaml`** — `proto:sheng` has one stroke too many for 青's top half. See § [Known issues → #1 清 IoU = 0.0](#1-清-ioυ--00---extraction_plan-yaml-bug).
2. Regenerate 清 locally: `cd project/py && .venv/bin/olik build 清 -o ../schema/examples` then copy the fresh record into `.preview-records/` and refresh quickview.
3. Amend PR #3 with the fix (or merge PR #3 as-is and land a follow-up commit on main — both valid; see § [Open decisions](#open-decisions)).
4. Continue: author `.archon/workflows/plan-04-*` / `plan-05-*` / `plan-06-*` / `plan-07-*`.

Everything else below is background for picking up.

---

## Current state

### Git

| Thing | Ref | Commit |
|---|---|---|
| main | `main` | `ca499d1 feat(quickview): live xyflow preview via .preview-records dropbox` |
| origin | `github.com/GiantCroissant-Lunar/olik-font` | public |
| Merged | **PR #1** — Plan 02 (Python core) | 9a833a2 merged 2026-04-21 06:50 UTC |
| **Open PR #2** | archon/task-kimi-scaffold-glyph-schema-1776753186136 | Plan 04 Task 1 scaffolding only (by Kimi CLI) |
| **Open PR #3** | archon/task-plan-03-python-compose-cli-1776754251679 | Plan 03 (compose + rules + CLI). **Ships the 清 IoU=0 bug.** |

Current `main` has 45 commits since project init. 17 of those are this session's work (Archon setup, multi-CLI workflows, quickview, Phase-1 finalization, Plan 02 merge, Plan 03 workflow, the planning-docs chain).

### Tags

- `plan-01-foundation` at `7636141`
- `plan-02-python-core` at `9a833a2` (pushed to origin)

### Worktrees (active)

Archon auto-created these under `~/.archon/worktrees/plate-projects/olik-font/archon/`:

```
task-kimi-scaffold-glyph-schema-1776753186136    — Kimi's Plan 04 Task 1 run
task-plan-02-python-core-1776749310602           — earlier Plan 02 attempt (pre-fix)
task-plan-02-python-core-1776750906355           — Plan 02 successful run (PR #1 came from this)
task-plan-03-python-compose-cli-1776754251679    — Plan 03 successful run (PR #3 came from this)
```

All can be pruned when their PRs merge via `archon isolation cleanup --merged`. The `task-plan-02-*-1776749310602` one is from an abandoned earlier run — safe to remove any time.

The main repo at `/Users/apprenticegc/Work/lunar-horse/plate-projects/olik-font/` is on `main`, clean.

### Running services at time of handover

- **Quickview Vite dev server** — port 5174, background task `bx2ca81ak`. Will die when the shell ends. Restart with `cd project/ts/apps/quickview && pnpm dev`.
- **No active Archon workflow.** Plan 03 completed successfully.
- **Monitor `bu9v7mzms`** was watching Plan 03's log — can be stopped or left; no new events expected.

---

## What was accomplished this session

### Archon stack

- Installed Archon 0.3.6 via Homebrew.
- **Switched from SQLite to PostgreSQL** per D22. Role `archon`, database `archon`, connection URL in `infra/.env` (gitignored). SQLite backup at `~/.archon/backup-sqlite-20260421-130140/`.
- Applied `migrations/000_combined.sql` — 8 tables. Archon 0.3.x does not auto-migrate.
- Wrote `~/.archon/config.yaml` with `defaultAssistant: codex` + `assistants.claude.enabled: false`.
- Configured env vars in `infra/.env`: `DATABASE_URL`, `DEFAULT_AI_ASSISTANT=codex`, `CODEX_BIN_PATH=/opt/homebrew/bin/codex`.

### Plans executed

| Plan | Scope | Workflow | Status | Notes |
|---|---|---|---|---|
| 01 | MMH + cjk-decomp sources + JSON schemas + ts workspace | n/a (was done earlier via Claude Code subagents) | **merged main** | Tag `plan-01-foundation` |
| 01 finalization | Commit cjk-decomp JSON + quicktype codegen | `feat(data): commit cjk-decomp.json + quicktype codegen` | merged main | Removed ref-projects/ runtime dep |
| 02 | Python core (types, geom, prototypes, decompose, constraints) | `.archon/workflows/plan-02-python-core.yaml` | **merged main via PR #1** | Tag `plan-02-python-core`, 65 tests |
| 03 | compose walker, flatten, z-layers, IoU, rules, CLI | `.archon/workflows/plan-03-python-compose-cli.yaml` | **PR #3 open, has the 清 bug** | 11 tasks committed, tag `plan-03-python-compose-cli` |
| 04 Task 1 | Scaffold @olik/glyph-schema package | `.archon/workflows/kimi-scaffold-glyph-schema.yaml` | **PR #2 open (Kimi CLI)** | Validates Kimi-as-implementer; Plan 04 Tasks 2-10 still to do |

### Multi-CLI validation

Per the "2 Codex + 1 Kimi + 1 Copilot" ask, we validated:

- **Codex (native Archon AI node)** — drove Plan 02 and Plan 03 implement loops. Self-healing: mid-run BLOCK on Plan 02 Task 8 (inconsistent spec) was resolved by merging the plan fix into the worktree during a later iteration.
- **Kimi (via `bash:` node)** — drove Plan 04 Task 1 scaffolding in one shot via `kimi --print --yolo --final-message-only`. 1m26s, exact output, correct commit. Single-task scope only (Archon's `loop:` works only for the Codex AI-node).
- **Copilot (via `bash:` node)** — workflow YAML authored (`.archon/workflows/copilot-pr-audit.yaml`) but not run yet. Needs `copilot -p ... --allow-all-tools` for non-interactive mode.
- **Codex review (via `bash:` node running `codex exec`)** — workflow YAML authored (`.archon/workflows/codex-review-worktree.yaml`) but not run yet.

### Tooling added

- `ruff` 0.13.2 + `ruff format` + `ruff check` pre-commit hooks (config in `project/py/pyproject.toml` `[tool.ruff]` + `[tool.ruff.lint]`).
- `@biomejs/biome` 2.0.6 as pnpm devDep + `project/ts/biome.json` (migrated 2.0.6 schema).
- `pre-commit` 4.3.0 hooks: trailing-ws, EOF, YAML/JSON/merge-conflict, large-files, ruff, biome (local system hook), conventional-pre-commit.
- `git-cliff` 2.12.0 + `cliff.toml` + generated `CHANGELOG.md`.
- `go-task` 3.48.0 + `Taskfile.yml` with setup / test / lint / fmt / archon / cliff / data / codegen / preview targets.
- `quicktype` 23.2.6 (already globally installed) — generates Python dataclasses + TS interfaces + zod schemas from `project/schema/cjk-decomp.schema.json`. Hooked into `task codegen:cjk-decomp`.

### Phase-1 data finalization

- Switched cjk-decomp source from the HanziJS vendored copy (under `ref-projects/`, runtime-fragile) to the upstream `amake/cjk-decomp` repo at pinned commit `c29b391fd6267e7a3541387e03a3dd60b1cd34d1`.
- Committed `project/py/data/cjk-decomp.json` (4.3 MB, 85,238 entries) + `project/py/data/LICENSE-cjk-decomp` (Apache-2.0 attribution) — `.gitignore` carve-out so the rest of `data/` stays ignored.
- Generated Python dataclasses at `project/py/src/olik_font/generated/cjk_decomp_types.py` and TS interfaces + zod at `project/ts/packages/glyph-schema/src/generated/cjk-decomp-*.ts`.
- Refactored `olik_font.sources.cjk_decomp` to consume JSON via generated types. Removed: `extract_from_hanzijs`, `fetch_cjk_decomp`, wrapper-strip regex. Public API unchanged.
- `scripts/regen-cjk-decomp.py` is the one-button refresh (fetch upstream → rewrite JSON → re-invoke quicktype).

### Preview + visualization

- `scripts/preview-glyph.py` — Python CLI that reads a `glyph-record-<char>.json` and emits a standalone SVG with animCJK-style stroke rendering + 128-unit grid + IoU badge.
- **`.preview-records/` dropbox** (gitignored) at repo root. Archon workflows' `preview` nodes copy `glyph-record-*.json` + `prototype-library.json` + `rule-trace-*.json` here so `apps/quickview` can serve them via Vite `publicDir` without depending on a specific worktree path.
- **`apps/quickview/`** — new Vite + React 18 + `@xyflow/react` 12 app on port 5174. Two-pane layout: SVG glyph render (left) + xyflow decomposition tree (right). 4-button char picker (明/清/國/森). Small Vite middleware falls back to `project/schema/examples/` when a record isn't in the dropbox.

### Docs

- `.agent/skills/00-meta/archon-workflows/SKILL.md` **fully rewritten** to reflect Archon 0.3.x reality (env-var config, manual migration, origin-remote mandatory, `.worktrees/` myth busted, zombie-state hazard + recovery playbook, CLI flag reference, auto-approve template).
- Plan 01 gained a "Phase 1 finalization" section documenting the cjk-decomp data shift.
- Plan 02 Task 8 relaxed to use relative ordering (instead of absolute pixel bounds) for the `apply_top_bottom` test.

### Zombie-running-state lessons

Plan 02's first approve attempt got the workflow stuck in "running" DB state after SIGPIPE killed the approve command mid-transition. Captured in the updated skill's hazards section. Operational rule now: never pipe Archon state-mutating commands through `head`/`tail`; use `run_in_background` + `tee`. Design rule: **no `interactive: true` on `approve` nodes** — replaced with a bash auto-approve conditional on `run-tests` passing. All workflows since follow this pattern.

---

## Architecture decisions locked in during this session

Record here so the next session doesn't re-litigate them.

1. **Runtime rendering: SVG, not CanvasKit.** Reasoning in the brief from this session: SVG handles our workload (tens of paths per frame, stroke-by-stroke animation via `stroke-dashoffset`, React integration, no bundle cost). CanvasKit's killer features (brush/ink effects, boolean path ops) are the things our architecture delegates to ComfyUI, offline. Revisit when we want live interactive styling without ComfyUI round-trips, or a 500-glyph-on-one-page grid view.

2. **Scope: Traditional Chinese only.** 明/清/國/森 are Traditional (國, not 国; 森 is same in both). cjk-decomp and MMH both support Traditional cleanly. When we expand past the 4 seed chars, prefer animCJK's `graphicsZhHant.txt` if we need a tighter scoping layer.

3. **Preview dataflow: `.preview-records/` dropbox.** Workflows copy records here so quickview can serve them live from ANY worktree's outputs, without waiting for PR merge.

4. **Approve gates: bash auto-approve, not interactive.** Avoids the zombie-state hazard, loses nothing (tests gate correctness; post-PR review handles judgment).

5. **Codex owns implement loops.** Non-Codex CLIs (Kimi, Copilot, Gemma4, Pi) via `bash:` nodes only. One task per Kimi/Copilot invocation — Archon's iterative `loop:` doesn't apply to them.

6. **Every plan should produce a visible outcome.** Plan 03 is the first visually verifiable plan (renders 4 SVGs). Future plan workflows should include similar preview nodes.

7. **No `ref-projects/` at runtime.** Planning-stage only. If runtime code needs upstream data, fetch over HTTPS from a pinned commit or commit a data snapshot with attribution.

---

## Known issues to fix next session

### #1 清 IoU = 0.0 — extraction_plan.yaml bug

**Symptom**: in Plan 03's output, 清's composed stroke count is 12, MMH has 11. IoU report records `"note": "stroke count mismatch: composed=12 mmh=11"` and mean/min are both 0.

**Root cause**: `project/py/data/extraction_plan.yaml` treats 清's right half (青) as 生 (5 strokes) + 月 (4 strokes) = 9, but real 青 is 龶 (4 strokes — shorter form, no fifth slash) + 月 (4 strokes) = 8. `proto:sheng` extracts stroke indices `[0, 1, 2, 3, 4]` from 青; should be `[0, 1, 2, 3]`. `proto:moon` may also need its 青-context indices adjusted (currently uses indices from 明 for the 月 proto, which is fine; 青's trailing 月 is a separate extraction).

**Cross-reference**: Plan 01's Adjustments section already documents the real cjk-decomp data: `青:d(龶,月)` — but the extraction_plan was authored before that adjustment landed. Fix was never propagated.

**Proposed fix** in `project/py/data/extraction_plan.yaml`:

```yaml
  - id: proto:sheng
    name: "龶"                          # was "生" — rename to the actual top-of-青 form
    from_char: "青"
    stroke_indices: [0, 1, 2, 3]        # was [0, 1, 2, 3, 4] — drop index 4
```

Then verify 清 re-generates with 11 strokes and IoU ≥ 0.85. All tests should still pass (the integration test doesn't check stroke counts; per-task tests don't care about 青).

### #2 Plan 03's PR (#3) contains the bug

Options:

- **Amend**: check out the Plan 03 worktree branch, apply the extraction_plan fix as a new commit, regenerate outputs, push. `gh pr view 3` will show the amended state.
- **Merge then fix on main**: land PR #3 as-is, open a small follow-up PR titled `fix(extraction-plan): 青 → 龶+月, not 生+月`. Cleaner history; doesn't force-push.

Either works. Prefer the follow-up commit approach — PR #3 history is accurate to what Plan 03 produced; the fix belongs to a later decision.

### #3 Plan 04 workflow is a single-task Kimi run (PR #2)

PR #2 only covers Task 1 (package scaffolding). Plan 04's Tasks 2-10 (real zod schemas for coord_space/affine/prototype/prototype-library/constraint/layout-tree/stroke-instance/glyph-record/rule-trace + validation tests + glyph-loader fs/URL/bundle + real-record tests) are still to-do. Options:

- Author `.archon/workflows/plan-04-ts-foundation.yaml` using the Codex-native pattern and let it drive Tasks 2-10 (or all of 1-10, superseding PR #2).
- Keep PR #2 as "scaffolding only" and write a `plan-04-tasks-2-10` follow-up workflow.

Preference: **supersede PR #2** with a full plan-04 workflow run, since Codex's loop is much stronger than Kimi's one-shot for multi-task plans. PR #2 becomes a validated proof-point ("Kimi can scaffold a package") that we can close unmerged if we want.

### #4 Workflows still to author

Need `.archon/workflows/` YAMLs for:

- `plan-04-ts-foundation.yaml` — TS schema + loader packages
- `plan-05-ts-viz-primitives.yaml` — `@olik/glyph-viz` component library
- `plan-06-remotion-studio.yaml` — animated presentation app
- `plan-07-xyflow-inspector.yaml` — interactive node-based inspector

All should use the auto-approve template from the updated skill. Plans 06/07 especially should include preview nodes that auto-start their dev server (Vite) + print the localhost URL to the workflow log so we can eyeball immediately.

### #5 `ollama signin` not done

Gemma4 cloud routing for reviews is still blocked. If we decide to wire Gemma4 reviews per spec D23, run `ollama signin` interactively (browser-based). Until then, `codex exec`-based review (via the `codex-review-worktree` workflow) is our substitute.

### #6 Pi (ZAI) rate limit

ZAI coding plan had a 5-hour rate window that was near exhausted AM 2026-04-21 (~10:28 UTC reset per the earlier handover). Plan 04/5/7 (originally assigned to Kimi for TS, not Pi) don't need Pi. Verify Pi status with a ZAI `/models` probe if we ever need it.

### #7 Quickview gaps (nice-to-haves, not blockers)

- Only shows 1 char at a time. A "grid view" of 4 glyphs would help spot comparative issues faster.
- No tabs for multiple presentations (Plain / Skeleton / Roles / Layers / Grid). Requires ~20 min of work; would prove the "one record, many views" claim before Plan 06 lands.
- Prototype library DAG view not in yet. Would show 日/月/氵/青/生/囗/或/木 with usage counts — useful for verifying reuse.
- No auto-refresh — must reload browser when `.preview-records/` updates. Could add Vite's file watcher to hot-reload JSON, but low priority.

### #8 Stale Archon worktree

`~/.archon/worktrees/plate-projects/olik-font/archon/task-plan-02-python-core-1776749310602` — an earlier Plan 02 attempt before the zombie-state fix. Safe to remove:

```bash
git worktree remove ~/.archon/worktrees/plate-projects/olik-font/archon/task-plan-02-python-core-1776749310602
# Or let `archon isolation cleanup --merged` sweep once PR #1 has settled.
```

---

## How to resume — concrete first actions

### Environment

```bash
cd /Users/apprenticegc/Work/lunar-horse/plate-projects/olik-font
set -a; source infra/.env; set +a
```

Every `archon` invocation needs `env -u CLAUDECODE archon ...` — the `CLAUDECODE=1` env var makes Archon hang silently inside a Claude Code shell. Alias it if you like:

```bash
alias arc='env -u CLAUDECODE archon'
```

### Fix the 清 bug (first 10 minutes of next session)

```bash
# 1. Edit project/py/data/extraction_plan.yaml per § #1 above.

# 2. Regenerate the record locally (Plan 03's CLI is on main after PR #3 merges;
#    until then, run from the Plan 03 worktree or cherry-pick the CLI):
cd project/py && .venv/bin/olik build 清 -o ../schema/examples

# 3. Verify IoU:
jq '.metadata.iou_report | {mean, min, note}' ../schema/examples/glyph-record-清.json

# 4. If mean/min >= 0.85, copy to dropbox and refresh quickview:
cp ../schema/examples/glyph-record-清.json ../../.preview-records/

# 5. Visit http://localhost:5174/ (restart `pnpm dev` if stopped).
#    Click 清. Should render without overlap. IoU badge shows >= 0.85.
```

### Start quickview

```bash
cd project/ts/apps/quickview && pnpm dev
# Port 5174; auto-opens browser; reads from .preview-records/ + fallback to project/schema/examples/.
```

### Run an Archon workflow

```bash
task archon:run WF=plan-04-ts-foundation   # (once authored)
# Or direct:
env -u CLAUDECODE archon workflow run <name>
```

Watch:

```bash
env -u CLAUDECODE archon workflow status
tail -f /tmp/archon-*.log
```

### Recovery if a workflow zombifies

```bash
env -u CLAUDECODE archon workflow abandon <run-id>
cd ~/.archon/worktrees/plate-projects/olik-font/archon/task-<slug>
git push -u origin <branch>
gh pr create --title "Plan NN: <topic>" --body "..."
```

---

## Artifacts worth inspecting before starting

- [PR #3 — Plan 03](https://github.com/GiantCroissant-Lunar/olik-font/pull/3) — the 清 bug ships here; review and plan the fix strategy.
- `project/py/data/extraction_plan.yaml` — the file to edit for issue #1.
- `.preview-records/glyph-record-*.json` — the 4 currently-copied records. `jq '.metadata.iou_report'` to see per-char scores.
- `.agent/skills/00-meta/archon-workflows/SKILL.md` — re-skim § Known hazards before running any approve command.
- `http://localhost:5174/` — quickview; restart Vite if process is gone.
- [Plan 03 spec](vault/plans/2026-04-21-03-python-compose-cli.md), [Plan 04 spec](vault/plans/2026-04-21-04-ts-foundation.md), etc. — for authoring workflows.

---

## Open decisions (to make early next session)

1. **PR #3 strategy**: amend vs. merge+follow-up? (Recommend: merge + follow-up.)
2. **PR #2 strategy**: supersede with full Plan 04 workflow, or keep as scaffolding proof-point? (Recommend: supersede; close #2 unmerged once full Plan 04 PR lands.)
3. **Quickview tabs**: add Plain / Skeleton / Roles / Layers / Grid tabs now, or wait for Plan 06's full Remotion Studio + Plan 07's Inspector? (Recommend: defer — quickview stays minimal; Plan 07 is the full Inspector.)
4. **Traditional-only scope**: record in spec Section 0 / handover? (Done in this handover; propagate to spec if we want it pinned there.)
5. **Zombie worktree cleanup cadence**: manual after each merge, or schedule `archon isolation cleanup --merged` weekly? (Recommend: manual for now — low volume.)

---

## Key files touched this session

```
.agent/skills/00-meta/archon-workflows/SKILL.md          — rewritten
.archon/workflows/                                        — 4 new YAMLs
  plan-02-python-core.yaml                               — patched to auto-approve
  plan-03-python-compose-cli.yaml                        — new, with preview node
  kimi-scaffold-glyph-schema.yaml                        — new (ran, PR #2)
  codex-review-worktree.yaml                             — new (not run yet)
  copilot-pr-audit.yaml                                  — new (not run yet)
.gitignore                                                — .preview-records/, .archon/state/, etc.
.pre-commit-config.yaml                                  — new
CHANGELOG.md                                             — bootstrapped by git-cliff
Taskfile.yml                                             — new (setup/test/lint/fmt/archon/preview/cliff/data/codegen)
cliff.toml                                               — new (conventional commits → CHANGELOG)
infra/.env                                               — DATABASE_URL, DEFAULT_AI_ASSISTANT, CODEX_BIN_PATH filled
project/py/data/cjk-decomp.json                          — committed (4.3 MB, Apache-2.0)
project/py/data/LICENSE-cjk-decomp                       — attribution
project/py/src/olik_font/generated/cjk_decomp_types.py   — quicktype-generated
project/py/src/olik_font/sources/cjk_decomp.py           — refactored to load JSON
project/schema/cjk-decomp.schema.json                    — new (Draft 07 for quicktype compat)
project/ts/biome.json                                    — new
project/ts/apps/quickview/                               — new app
project/ts/packages/glyph-schema/src/generated/          — cjk-decomp-types.ts + cjk-decomp-zod.ts
project/ts/package.json                                  — biome added
scripts/preview-glyph.py                                 — new
scripts/regen-cjk-decomp.py                              — new
vault/plans/2026-04-21-01-foundation.md                  — appended Phase-1-finalization section
vault/plans/2026-04-21-02-python-core.md                 — Task 8 test relaxed
vault/plans/2026-04-21-03-python-compose-cli.md          — no code edit; executed
~/.archon/config.yaml                                    — rewritten (not committed; machine-local)
```

---

## Reference trail

- Design spec: [[2026-04-21-glyph-scene-graph-solution-design]]
- Plan index: `vault/plans/`
- PR #1 (merged): https://github.com/GiantCroissant-Lunar/olik-font/pull/1
- PR #2 (open, Kimi scaffolding): https://github.com/GiantCroissant-Lunar/olik-font/pull/2
- PR #3 (open, Plan 03 with 清 bug): https://github.com/GiantCroissant-Lunar/olik-font/pull/3
- Archon-workflows skill: [.agent/skills/00-meta/archon-workflows/SKILL.md](.agent/skills/00-meta/archon-workflows/SKILL.md)
- Coding-providers skill (agent → provider map): `.agent/skills/04-tooling/coding-providers/SKILL.md`
