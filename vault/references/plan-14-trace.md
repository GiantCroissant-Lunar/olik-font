---
title: Plan 14 trace ledger
created: 2026-04-23
tags: [type/trace, topic/plan-14]
source: self
status: active
---

# Plan 14 — Trace ledger

Append-only record of measurements taken while implementing
`[[2026-04-23-14-authored-decomp-and-prototype-graph]]`. Every task in
the plan writes one or more rows here. Reviewers and downstream
sessions use this ledger to re-verify claims without re-running the
workflow.

## Schema

| Column | Meaning |
|---|---|
| `task` | Plan 14 task number (0..12). Task 11 contributes 3 rows. |
| `commit` | Short SHA of the commit that landed the work. |
| `metric` | Name of the measurement (machine-comparable string). |
| `value` | Measured value. Numeric, boolean, or short string. |
| `kimi_verdict` | `n/a` for programmatic measurements; a relative path under `vault/references/plan-14-kimi-verdicts/` for visual ones. |
| `timestamp` | UTC ISO-8601 when the measurement was taken. |

## Append rules

1. **Append only.** Never edit historical rows. If a measurement was
   wrong, append a corrected row with the same `task` + `metric` and a
   note in the value field (e.g. `0.91 (supersedes earlier 0.78 — bug in test fixture)`).
2. **One commit per task.** The `commit` column is the single Plan 14
   commit that landed that task's work. Task 11's three rows share the
   same commit SHA.
3. **Kimi verdict files are immutable.** Once written, do not edit. If
   you re-verify, write a new file with a `-rerun-N` suffix and link
   to it from a new ledger row.

## Ledger

| task | commit | metric | value | kimi_verdict | timestamp |
|---|---|---|---|---|---|
| 0 | pending | guard_violations | 0 | n/a | 2026-04-23T01:45:31Z |

## Cross-reference

- Plan: `[[2026-04-23-14-authored-decomp-and-prototype-graph]]`
- Design: `[[2026-04-23-authored-decomp-and-prototype-graph-design]]`
- Workflow: `.archon/workflows/plan-14-authored-decomp-and-prototype-graph.yaml`
- Verdict transcripts: `vault/references/plan-14-kimi-verdicts/`
- Geometry rule: `.agent/skills/05-engine/glyph-geometry/SKILL.md`
