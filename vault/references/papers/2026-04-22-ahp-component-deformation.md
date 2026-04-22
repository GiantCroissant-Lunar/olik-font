---
title: AHP-based Chinese character component deformation (Tian, Yang, Gao, 2022)
created: 2026-04-22
tags: [type/distilled, topic/chinese-font, topic/component-deformation]
source: external
source-url: https://www.mdpi.com/2076-3417/12/19/10059
paper-doi: 10.3390/app121910059
status: draft
---

# AHP-based Chinese character component deformation

**Summary (one line).** Uses the Analytic Hierarchy Process (a multi-criteria decision technique) to derive the affine-transformation parameters for deforming components into a target style, instead of authoring those parameters manually.

> MDPI blocked WebFetch (403). Content here is from the WebSearch result summary that paraphrased the abstract; I did not read the full paper. Flagged accordingly in each bullet.

## Ideas we could borrow

1. **AHP as a manual-authoring aid** — when a human has to choose between several candidate transforms for a component in an unfamiliar style, AHP's pairwise-comparison matrix is a structured way to fall back from "guess". *Cost: this is a tooling idea for a future style adapter, not our current pipeline. ~1 day if ever adopted; no prerequisite.*
2. **Consistency-ratio check for authored placements** — AHP computes a consistency ratio on its pairwise matrix; we could adopt the same sanity check on any authored preset-adapter output (before it emits concrete transforms) to detect contradictions in the author's intent. *Cost: small utility in `prototypes/` authoring; ~0.25 day; not urgent.*

## INCOMPATIBLE ideas (on record)

- **Using AHP weights to drive composition at runtime.** The paper's core contribution is deriving component deformation parameters from decision weights over layout categories. That is exactly the preset-with-global-weights pattern `.agent/skills/05-engine/glyph-geometry/SKILL.md` rules out. `INCOMPATIBLE: violates .agent/skills/05-engine/glyph-geometry/SKILL.md — do not adopt.`
- **Per-layout-category deformation tables.** Any attempt to map "left-right → weight X", "top-bottom → weight Y" would reintroduce the D4 violation we just removed (commit `7b9f8d8` revert). `INCOMPATIBLE: violates .agent/skills/05-engine/glyph-geometry/SKILL.md — do not adopt.`

## What it would cost us to adopt the compatible parts

- The only bit we could defensibly adopt is AHP as an **authoring-time** aid (bullet 1 above), not a runtime layout rule. No immediate file-level change; would live in a future authoring tool.

## Verdict

File kept for completeness. **Do not pick this as a borrow candidate** — the core method is the exact anti-pattern our project is currently deleting.

## See also

- `.agent/skills/05-engine/glyph-geometry/SKILL.md` — the rule this paper's method would violate.
- `vault/plans/2026-04-22-11-virtual-coordinates-only.md` — the plan removing preset weights from our code right now.
