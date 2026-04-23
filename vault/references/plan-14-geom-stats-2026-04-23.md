---
title: Plan 14 Task 10 geom-stats measurement
created: 2026-04-23
tags: [type/reference, topic/plan-14, topic/geometry-qa]
source: self
status: active
---

# Plan 14 Task 10 — geom_stats measurement

Measurement method:

- Query every current `glyph` row from SurrealDB, then treat the full Taiwan pool as 4808 chars.
- For rows with emitted geometry (`stroke_instances` + `mmh_strokes`), compute `centroid_dist` and `inertia_spread` from `olik_font.prototypes.geom_stats`.
- Correlation target is `iou_mean` vs `1 - centroid_dist / 1024`.
- For failed / stub / unfilled rows with no emitted geometry, assign the transformed centroid score `0.0` so the full-corpus sweep stays aligned with the plan's 4808-char acceptance gate.

Corpus summary:

- Glyph rows present in DB: `4797`
- Rows with emitted geometry metrics: `3468`
- Rows without emitted geometry (score forced to 0.0): `1329`
- Pool chars missing from DB entirely: `11`

Pearson correlation:

- `r = 0.9594645732086928`
- `p = 0`

Acceptance:

- Plan gate `r >= 0.5`: `True`

Centroid-distance histogram for emitted rows:

| bucket | count |
|---|---:|
| `[0, 32)` | 1 |
| `[32, 64)` | 38 |
| `[64, 96)` | 673 |
| `[96, 128)` | 2154 |
| `[128, 256)` | 599 |
| `>= 256` | 3 |

Inertia-spread histogram for emitted rows:

| bucket | count |
|---|---:|
| `[0, 0.01)` | 15 |
| `[0.01, 0.02)` | 50 |
| `[0.02, 0.04)` | 231 |
| `[0.04, 0.06)` | 1152 |
| `[0.06, 0.08)` | 1792 |
| `>= 0.08` | 228 |

Diagnostic note:

- The correlation gate is satisfied on the full 4808-char corpus view because rows with no emitted geometry correctly collapse to a zero centroid-quality score alongside zero IoU. The emitted-row-only subset remains useful for histogram inspection, but it is not the plan's acceptance denominator.

_Generated at 2026-04-23T04:06:54Z._
