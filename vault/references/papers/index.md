---
title: Papers — Map of Content
created: 2026-04-22
tags: [type/moc, topic/chinese-font, topic/scene-graph]
---

# Papers

Distilled notes on external research on Chinese-character / font generation, filtered through this project's design constraint: **component placement is a measured affine transform in 1024² virtual space, not a preset bucket**. See `.agent/skills/05-engine/glyph-geometry/SKILL.md`.

Each note lists 3–5 concrete "idea we could borrow" bullets; ideas that would re-introduce preset-style categorical placement are explicitly flagged INCOMPATIBLE.

## Notes

- [[2026-04-22-ccfont]] — CCFont (Park et al., Applied Sciences 2022). 17-component GAN; local style per component. Borrow: component-level style conditioning and radical extraction via CJKradlib. Most placement/composition machinery is INCOMPATIBLE — operates on raster images, not measured transforms.
- [[2026-04-22-ahp-component-deformation]] — Tian/Yang/Gao, Applied Sciences 2022 (12/19/10059). Uses AHP to assign affine-deformation weights per component. Flagged INCOMPATIBLE for our pipeline: replaces measured geometry with AHP-derived weights over preset layout categories. Kept in the vault for completeness.
- [[2026-04-22-vector-component-composition]] — arXiv 2404.06779. Vector-first, per-component 6-parameter affine, 11K components over 90K characters. Directly compatible: learned affine matches our `InstancePlacement.transform` shape; centroid/inertia losses are candidates for extraction QA.
- [[2026-04-22-sfgn-skeleton]] — arXiv 2501.08062 (Applied Sciences, 2025). Skeleton builder → feature tensor → raster; radical-level transitive attention over 415 radicals. Borrow (narrow): radical-level skeleton as an extraction QA signal. Most of the generator stack is image-domain and not reusable.
- [[2026-04-22-mmh-metadata]] — Make Me a Hanzi dataset audit. Confirms we already ingest `strokes` and `medians` but are leaving `matches`, `decomposition`, `radical`, `etymology` on the floor. Borrow: drive `source_stroke_indices` (introduced in Plan 11 Task 2) from `matches` automatically.

## Reading order

- Quick: start with [[2026-04-22-vector-component-composition]] + [[2026-04-22-mmh-metadata]] — both plug directly into Plan 11's measurement path.
- Broader context: [[2026-04-22-ccfont]] then [[2026-04-22-sfgn-skeleton]] for the deep-learning component-composition lineage.
- For-the-record: [[2026-04-22-ahp-component-deformation]] — documents the preset-with-weights approach we explicitly reject.

## Adoption status

- ACTIVE borrow: `matches`-driven `source_stroke_indices` prefill — see [[2026-04-22-borrow-mmh-matches-prefill]].
- Remaining borrows: parked; revisit after Plan 11 lands.
