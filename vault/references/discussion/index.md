---
title: Discussions — Map of Content
created: 2026-04-21
tags: [type/moc]
---

# Discussions

AI-threaded research branches, preserved raw. Each file is one branch snapshot — later branches extend the content of earlier ones (that's how the upstream thread was exported, not a mistake).

The distilled design output of this chain lives in [[glyph-scene-graph-spec]] under `vault/specs/` — read that first if you just want the conclusions. A pipeline diagram stub sits alongside it: [[glyph-scene-graph-pipeline.excalidraw]].

> This folder holds **external raw material only**. Our own specs and distilled notes live under `vault/specs/`.

## Branch chain

1. **[[discussion-0001]]** — Existing projects for coloring Chinese character components. _Surveys Dong Chinese, HanziCraft, HanziVG, Make Me a Hanzi as component/decomposition references._
2. **[[discussion-0002]]** — Can ComfyUI + existing font-gen repos (pix2pix, zi2zi, DP-Font, CCFont, qiji-font) produce styled Chinese fonts? _Conclusion: styled text images yes; full installable font only as a staged system with ComfyUI as orchestration, not core algorithm._
3. **[[discussion-0003]]** — Component-first pipeline. _Shift from per-character to per-component + layout. Proposes a glyph scene graph using IDS structure + normalized vector coords + separate styling layer. Introduces stroke data from HanziVG / animCJK / Make Me a Hanzi._
4. **[[discussion-0004]]** — Replace categorical IDS relations (left_right, top_bottom, …) with a general constraint-based scene graph. _IDS becomes a bootstrap parse layer, not the atomic representation. Nodes support keep/refine/replace to compose any logographic symbol, not just CJK._

## Reading order

- **Quick takeaway only:** [[glyph-scene-graph-spec]]
- **Full context:** 0001 → 0002 → 0003 → 0004 in order. Each extends the previous, so later files contain more. If skimming, 0004 has the most mature thinking.

## Key external references surfaced in the chain

- Dong Chinese / Chinese Character Wiki — color-codes character parts by function (meaning / sound / iconic / distinguishing).
- HanziCraft — decomposition and productive-component frequency.
- HanziVG, Make Me a Hanzi — stroke-order SVG + IDS decomposition data (1024×1024 coord space, stroke medians, matches field).
- animCJK / animHanzi — stroke-by-stroke SVG rendering of CJK data.
- zi2zi, pix2pix, CycleGAN, CCFont, DP-Font, IF-Font — font-generation models at various maturity levels.
- qiji-font — OCR → cleanup → Potrace → FontForge pipeline for packaging generated glyphs into a real font.
- ComfyUI — orchestration layer for the styling stage only, not reconstruction.

## Status

Raw material — preserved verbatim. Do not edit the discussion files in place. If a conclusion needs revision, update [[glyph-scene-graph-spec]] instead.
