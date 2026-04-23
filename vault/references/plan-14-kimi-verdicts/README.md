---
title: Plan 14 — Kimi verdict transcripts
created: 2026-04-23
tags: [type/index, topic/plan-14]
---

# Plan 14 — Kimi verdict transcripts

One file per visual verification taken during Plan 14 implementation.
The trace ledger at `[[plan-14-trace]]` references each file by
relative path.

## Naming

`task-NN-<short-slug>.md` — e.g. `task-07-decomp-explorer.md`,
`task-09-proto-browser.md`, `task-11-e2e.md`. Re-runs append `-rerun-N`
(e.g. `task-07-decomp-explorer-rerun-1.md`).

## File contents (per verdict)

```markdown
---
task: 7
commit: <sha>
char: 森
screenshot: /tmp/plan14-screenshots/task-07-森.png
captured_at: 2026-04-23T11:42:00Z
kimi_version: <output of `kimi --version`>
---

## Prompt sent to kimi

<verbatim prompt string>

## Raw kimi stdout

<verbatim>

## Parsed verdict

```json
{"char":"森","is_tree":true,"colors_correct":true,"mode_chips_present":true,"verdict":"pass"}
```

## Notes

(Optional — operator commentary if the verdict needed manual review.)
```

## Binding rules

- **Never substitute a smaller vision model.** If kimi is unreachable,
  the verdict is `BLOCKED: kimi unavailable`. Do not call gemma3 / any
  ≤4B local model. See `feedback_visual_verifier_model.md`.
- **Files are immutable once written.** A re-verification produces a
  new file with `-rerun-N` suffix; the original stays.
- **Screenshots go to `/tmp/plan14-screenshots/`** (gitignored). The
  transcript records the path; the image itself is not committed.
