---
title: Skeleton and Font Generation Network — zero-shot Chinese character generation (arXiv 2501.08062)
created: 2026-04-22
tags: [type/distilled, topic/chinese-font, topic/skeleton, topic/zero-shot]
source: external
source-url: https://arxiv.org/html/2501.08062v1
paper-arxiv: 2501.08062
status: draft
---

# Skeleton and Font Generation Network (SFGN) — zero-shot Chinese character generation

**Summary (one line).** Two-stage generator: a skeleton builder turns radical-and-stroke captions into a 4×4×D content-feature tensor (rendered to a 64×64 skeleton image), then a font generator uses a transitive-attention mechanism across 415 radicals to apply a style from reference images.

> WebFetch on `arxiv.org/html/2501.08062v1` succeeded (HTML version only; PDF binary was unreadable). ResearchGate blocked as expected.

## Ideas we could borrow

1. **Radical-level dictionary size (415 radicals over 3,755 common chars) is a realistic target bound for our prototype library.** Our current library is 8 prototypes for the seed set; this gives us an upper bound to plan Plan 9.2 bulk extraction against. *Cost: documentation in the bulk-extraction spec; 0.25 day; no code.*
2. **Skeleton as a separate artifact from the styled glyph.** They produce a standard-font skeleton image before applying style. We already separate composition (geometry) from styling (deferred `packages/glyph-styler/`). Their "skeleton image" is our composed glyph record pre-styling — we can reuse their evaluation split (skeleton-correct but style-wrong vs. skeleton-wrong) for our own QA once a styler exists. *Cost: spec note only today; becomes real with glyph-styler.*
3. **Transitive-attention alignment across components.** Their mechanism chains aI2T × aT2T × aT2I attentions to match style-image components to content-caption components. A non-ML version of the same idea exists in our pipeline: radical identity in the prototype library drives cross-character reuse (月 is the same prototype in 明 and 清). Confirms we are on a defensible path; no new code needed. *Cost: nil — validation, not adoption.*

## INCOMPATIBLE ideas (on record)

- **Using the 4×4×D feature tensor as our composition representation.** That replaces measured affines with a learned low-res feature map; the renderer is a deconvolution, not an affine applier. `INCOMPATIBLE: violates .agent/skills/05-engine/glyph-geometry/SKILL.md — do not adopt.`
- **Their radical dictionary as a source of placement.** The paper does not measure per-instance bboxes in reference glyphs; placement is implicit in the learned features. Any attempt to derive `transform` from this model's outputs would be synthesised, not measured. `INCOMPATIBLE: violates .agent/skills/05-engine/glyph-geometry/SKILL.md — do not adopt.` (Using their radical *list* as a naming scheme is fine; using their *model* to decide placement is not.)

## What it would cost us to adopt the compatible parts

- Near-term: only bullet 1 (a number in a doc). ~15 minutes.
- Medium-term: bullet 2 — reshape our styler spec once we start one.
- Bullet 3 is pure validation; zero cost.

## See also

- [[2026-04-22-vector-component-composition]] — similar per-component decomposition but with explicit affines, much more directly reusable.
- [[2026-04-22-ccfont]] — same image-domain generation family as SFGN.
- `vault/specs/glyph-scene-graph-spec.md` §Deferred — styling stage is named but not built; SFGN is one of the models that would eventually inform it.
