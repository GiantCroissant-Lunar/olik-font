---
title: Plan 14 Task 6 productive-count measurement
created: 2026-04-23
tags: [type/reference, topic/plan-14, topic/prototype-graph]
source: self
status: active
---

# Plan 14 Task 6 — productive_count measurement

Command run:

```bash
project/py/.venv/bin/olik db recompute-counts
```

CLI summary:

```text
recomputed productive_count for 6649 prototypes
  proto:u0033 42
  proto:u31d0 34
  proto:u961d 29
  proto:u8fb6 17
  proto:u31d4 15
  proto:u4ebb 15
  proto:u31d1 13
  proto:u31d2 9
  proto:u31df 9
  proto:u5202 9
```

Top 10 productive prototypes from the current `productive_count` field:

| rank | prototype_id | name | productive_count | source |
|---|---|---|---:|---|
| 1 | `proto:u0033` | `38469` | 42 | `extracted from 38469` |
| 2 | `proto:u31d0` | `㇐` | 34 | `extracted from ㇐` |
| 3 | `proto:u961d` | `阝` | 29 | `extracted from 阝` |
| 4 | `proto:u8fb6` | `辶` | 17 | `extracted from 辶` |
| 5 | `proto:u31d4` | `㇔` | 15 | `extracted from ㇔` |
| 6 | `proto:u4ebb` | `亻` | 15 | `extracted from 亻` |
| 7 | `proto:u31d1` | `㇑` | 13 | `extracted from ㇑` |
| 8 | `proto:u31d2` | `㇒` | 9 | `extracted from ㇒` |
| 9 | `proto:u31df` | `㇟` | 9 | `extracted from ㇟` |
| 10 | `proto:u5202` | `刂` | 9 | `extracted from 刂` |

Reference set from the plan:

`氵`, `口`, `人`, `日`, `月`, `木`, `心`, `水`, `火`, `土`

Measured overlap with the direct `productive_count` top 10:

- Exact-name overlap: `0/10`

Diagnostic note:

- Collapsing along the current `variant_of` graph raises the overlap to `4/10`
  (`口`, `氵`, `木`, `土`), but the direct per-prototype metric requested by
  Task 6 remains `0/10` on the current corpus.
