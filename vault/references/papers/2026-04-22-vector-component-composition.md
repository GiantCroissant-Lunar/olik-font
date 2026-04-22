---
title: Efficient and scalable Chinese vector-font generation via component composition (arXiv 2404.06779)
created: 2026-04-22
tags: [type/distilled, topic/chinese-font, topic/vector-font, topic/component-composition, topic/affine-transforms]
source: external
source-url: https://arxiv.org/html/2404.06779v1
paper-arxiv: 2404.06779
status: draft
---

# Efficient and scalable Chinese vector font generation via component composition

**Summary (one line).** Predicts a 6-parameter affine transform per component (scale_x, scale_y, skew_x, skew_y, tx, ty) through a learned Component Affine Regressor (CAR), applies the matrices to each component's Bézier curves, and sums the transformed components — with centroid and inertia losses enforcing balanced placement.

> WebFetch on `arxiv.org/html/2404.06779v1` succeeded. Numbers and quotes below are from that fetch.

## Ideas we could borrow

1. **The 6-parameter affine representation `[scale_x, skew_x, skew_y, scale_y, tx, ty]` is the same object as our `InstancePlacement.transform`.** This confirms our data model is on the right shape and gives us a concrete import/export format for interop with learned composers later. *Cost: no code change today — document the alignment; when we add a "learned layout adapter" (solution-design §Deferred work), it emits this exact 6-tuple. Effort to formalise: ~0.25 day of spec work after Plan 11.*
2. **Centroid loss + inertia loss as composition sanity checks.** Their paper uses these to train the regressor, but the metrics are also standalone geometric measurements: centroid distance from "expected" and second-moment spread. We can compute both on each composed glyph and add them to `metadata.iou_report` as secondary signals (today we only have IoU). *Cost: ~0.5 day — add `prototypes/geom_stats.py` with two pure functions; wire into `compose/` after Plan 11 lands.*
3. **"approximately 11K components over 90K characters"** — useful scaling signal for the prototype library. Our pass-1 library is 8 prototypes across 4 characters. The 11K/90K ratio (~1 component per 8.2 characters) suggests a well-designed library should be ≈ unicode_count / 8 prototypes for bulk coverage. *Cost: just a target number; informs Plan 9.2 bulk-extraction scope.*
4. **Per-component regressor architecture** (MLP with zero-initialised weights + identity-affine bias) is a clean template for the eventual "learned layout adapter" deferred in the solution design. We would replace their content+style image encoder with our prototype-library + measured-bbox inputs. *Cost: ~3–5 days when/if we add this adapter; not now.*

## INCOMPATIBLE ideas (on record)

- **Their six layout categories (NL00–NL05: Left-Right, Top-Bottom, Enclosed, etc.) as training labels** — only compatible if the categories are *input features* to a model that still outputs concrete per-instance affines. Using the labels as the *output* (i.e. "classify, then look up a weight table") is the preset pattern. Not incompatible as stated in the paper, but the project could easily mis-adopt this. Note of caution, not a ban.

## What it would cost us to adopt the compatible parts

- Near-term: bullet 2 only. Module `project/py/src/olik_font/prototypes/geom_stats.py` (new file — safe under Plan 11 since it's new); call site added in a follow-up to Plan 11 Task 4.
- Medium-term: bullet 4 as the concrete shape of the "learned layout adapter" deferred slot in the solution design.
- No prerequisite other than Plan 11 completing its compose rewrite.

## See also

- [[2026-04-22-ccfont]] — same decomposition spirit, image-domain composition, less directly compatible.
- `vault/specs/2026-04-21-glyph-scene-graph-solution-design.md` §Section 3 — our `InstancePlacement.transform` definition, which this paper validates.
- `vault/plans/2026-04-22-11-virtual-coordinates-only.md` Task 3 `measure_instance_transform` — our current source of measured affines (from source glyphs, not from a regressor).
