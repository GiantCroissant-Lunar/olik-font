---
title: Component-first pipeline — glyph scene graph with HanziVG / animCJK / Make Me a Hanzi
created: 2026-04-21
tags: [topic/chinese-font, topic/scene-graph, topic/component-composition, type/ai-thread]
source: ai-thread
branch-from: "[[discussion-0002]]"
seq: 3
---

Is there any existing project to color Chinese symbol as Canjile does?

I’m checking what “Canjile” refers to and looking for similar Chinese-character coloring projects so I can compare actual existing tools, not guess.

Thought for 2m 23s
Assuming you mean coloring parts of a Chinese character by role or component rather than tone coloring, then yes, there are related projects. The closest ready-made example I found is Dong Chinese / Chinese Character Wiki: it explicitly color-codes character parts by function, such as meaning components in red, sound components in blue, iconic components in green, distinguishing components in purple, and unknown components in gray.

Other useful projects are a bit more “decomposition/data” than “finished colorizer.” HanziCraft breaks characters into components and highlights phonetic patterns; HanziVG provides SVGs plus metadata for radicals/components; Make Me a Hanzi provides downloadable dictionary and stroke-order vector data for 9,000+ common characters; and Radically is a component-based CJK search engine. Those are good foundations if you want to build a Canjile-like renderer yourself.

So the practical answer is:

Closest existing learner-facing project: Dong Chinese.

Best building blocks for your own project: HanziVG + Make Me a Hanzi, optionally with HanziCraft or Radically for decomposition/search.

If you want, I can also narrow this down to open-source libraries specifically suited to implement the same coloring style in a web app.


https://kaonashi-tyc.github.io/2017/04/06/zi2zi.html
https://github.com/phillipi/pix2pix
https://github.com/kaonashi-tyc/zi2zi
https://github.com/LingDong-/qiji-font?tab=readme-ov-file
https://new.chine-culture.com/en/chinese-calligraphy/chinese-calligraphy-pattern-generator
https://arxiv.org/html/2508.06900v1
https://ui.adsabs.harvard.edu/abs/2023SPIE12596E..2EL/abstract
https://www.sciengine.com/parse/pdf/1003-9775/E4A1967F61E545D5803BBAED2BADF507.pdf?attname=Chinese+Font+Generation+from+Stroke+Semantic+and+Attention+Mechanism.pdf
https://github.com/kaonashi-tyc/Rewrite
https://www.mdpi.com/2076-3417/12/16/8005https://www.mdpi.com/2076-3417/12/16/8005
https://www.ijcai.org/proceedings/2024/0863.pdf

These are for ai gen Chinese font, do you think that we can combine the existing projects with the help of ComfyUI to create styled Chinese font(text)

Show more

I’m checking the linked repos and papers to separate what already works in practice from what is only a research prototype, then I’ll map that onto a realistic ComfyUI pipeline.

Thought for 31s
Yes — but the workable way is to use ComfyUI as the orchestration layer, not as the core font-generation algorithm. ComfyUI is built around modular graph workflows, supports custom nodes/extensions, and only re-executes the parts of a graph that change, which makes it a good fit for batch glyph rendering, preprocessing, inference, cleanup, and export.

The big distinction is the output target. Styled Chinese text images are very feasible now. A real installable Chinese font is also feasible, but much harder because you need consistent results across thousands of glyphs, plus vectorization, spacing, punctuation, numerals, and packaging. Recent surveys note that bitmap-based methods are easier to plug into mainstream generative models, while vector fonts are much better for scalability and editing but are harder to generate well. The same survey also treats creating fonts directly from textual descriptions as more of a future direction than a solved production pipeline.

Your links actually cover almost the whole stack:

pix2pix is the old image-to-image base model. zi2zi explicitly says it is an application/extension of pix2pix for Chinese/CJK glyphs, with multi-style training and style embeddings, so it is still a sensible baseline for paired font-to-font transfer.

Rewrite is an earlier proof of concept, and its own repo says to use zi2zi for better results. It is also very old technically.

The stroke semantic + attention paper is more structurally aware: it says it adds stroke-semantic priors plus an attention skip-connection module, and reports better results than pix2pix, zi2zi, and DCFont on public datasets.

The SPIE paper is useful if you do not have neatly paired source/target glyph datasets, because it frames the problem as improved CycleGAN-based style migration and explicitly targets missing structure, blur, and paired-data dependence.

CCFont is probably the strongest structural idea in your list for complex characters: its README describes a component-based GAN using up to 17 components, aiming to reduce information loss and support first-seen characters/styles.

DP-Font is the most modern calligraphy-oriented item you linked. It uses a diffusion model with multi-attribute guidance, explicit stroke-order conditioning, and a PINN loss to improve realism and calligraphic plausibility.

qiji-font is not a generator, but it is extremely useful for the back end of the pipeline: scan/OCR extraction, cleanup, raster-to-vector conversion with Potrace, and final font assembly with FontForge.

The Chinese calligraphy pattern generator is only a template/PNG renderer for entered text, so it is a UI/reference tool, not a model component.

The main catch is that the older public repos are dated. zi2zi still lists Python 2.7 and TensorFlow >= 1.0.1; Rewrite says it was tested on TensorFlow 0.10.0. So I would not try to smash all of this into one native ComfyUI codebase. A better route is to wrap legacy pieces behind custom nodes or subprocess/container boundaries, or reimplement the chosen model in modern PyTorch and let ComfyUI handle the workflow around it.

A realistic ComfyUI architecture would be:

Text → base glyph rasterizer
Render the input text from a neutral source font into per-character images.

Optional structure branch
Add component/stroke hints when available. This is where CCFont-style decomposition or stroke-order/stroke-semantic priors help most on Chinese.

Generator node
Pick one core model, not five:

zi2zi for the fastest paired baseline,

improved CycleGAN if your style references are unpaired,

DP-Font if the target is expressive calligraphy,

CCFont-like if consistency on complex characters matters more than brush realism.

Cleanup/postprocess
Thresholding, denoising, edge cleanup, centering, size normalization.

Text compositor
Reassemble generated glyphs into lines, paragraphs, posters, banners, etc.

Optional font export
Use a qiji-font-style tail: raster cleanup → Potrace/SVG → FontForge packaging.

So my honest view is:

For styled Chinese text rendering: yes, absolutely realistic.

For a full Chinese font generator: yes, but only as a staged system, and only if you accept that consistency and export quality will take more engineering than the model itself.

For “prompt-only, describe a style in words and get a complete font”: not really production-ready yet; the survey still frames text-conditioned font creation as an open direction.

If I were building this, I would start with ComfyUI + one generator + qiji-font-style export, specifically:

fast PoC: neutral font rasterizer → zi2zi-like generator → compose text images

better Chinese structure: replace generator with CCFont-like or stroke-semantic model

best calligraphy look: DP-Font-like generator for raster output, then vectorize only after cleanup

One last practical note: if you redistribute a combined system, review the repo licenses carefully, because your links span different licenses, including Apache-2.0 for zi2zi, GPL-3.0 for Rewrite, OFL-1.1 for qiji-font, and GPL-3.0 for ComfyUI.

I can sketch a concrete ComfyUI node graph for the best version of this stack next.

Branched from Branch · Chinese Character Color Projects


But I think as we already have components from HanzCraft, we basically store a set of components and reconstruct Chinese symbol using these components, in such case, we don't treat styling each reconstructed symbol, but we style components. This should reduce lots of Chinese symbol issue, as there might be more than 10000 Chinese Symbols
Show more

I’m checking whether HanziCraft-style decomposition is enough for font reconstruction, because the key question is not just “reuse components,” but whether the decomposition also preserves usable layout geometry for typography.

Thought for 31s
Yes — I think that is the right direction, and it matches where the stronger recent work has gone.

What you are proposing is a shift from character-level generation to component-level generation + layout composition. That is attractive for Chinese because HanziCraft already exposes decomposition views down to radicals and lower graphical parts, and it also highlights highly reused “productive components,” which is exactly the kind of reuse signal you want in a scalable system. HanziCraft’s own pages show decomposition levels such as “once,” “radical,” and “graphical,” plus lists of productive components and phonetic sets.

In other words, instead of learning 10,000+ glyphs independently, you learn a much smaller library of styled components, then learn how to place, deform, and combine them per character. That is not just a nice idea; it is already supported by recent font-generation research. CCFont explicitly generates Chinese characters from components and says it handles up to 17 components per character. A 2024 vector-font paper goes even further: it argues that most Chinese characters can be disassembled into frequently reused components, then composes large-scale vector characters from a small set of components plus layout information.

The key refinement is this: components alone are not enough. You also need a representation of structure. Modern work often uses IDS or similar structural encodings, not just a bag of parts. IF-Font, for example, explicitly follows Ideographic Description Sequence structure so the model can control content through component hierarchy and spatial relations. IDS-based work is useful here because Chinese characters are not only “which parts,” but also “which arrangement”: left-right, top-bottom, enclosure, and nested structures.

So I would phrase your idea like this:

Best formulation:
style the components, but compose the characters with a structural/layout model.

That gives you three big wins:

Coverage scales better.
You do not need fully separate style learning for every character. A reusable component bank can cover many more glyphs than pure per-character transfer. That is exactly the motivation behind the component-composition vector-font paper.

Rare characters become more feasible.
If a rare character is just a new arrangement of known parts, you can synthesize it without ever seeing that whole character during training. That is one of the selling points behind component-based and IDS-following methods.

Vector output becomes much more realistic.
If you store styled components as vector outlines or strokes, then compose them with transforms, you are much closer to a real font pipeline than with pure raster GAN output. The 2024 component-composition paper is explicitly about scalable vector font generation.

The main caveat is that a component is not visually identical in every context. In real fonts, a component often changes depending on where it appears. For example, the same radical may become narrower on the left, flatter on top, compressed inside an enclosure, or optically adjusted to avoid collisions. So a practical system needs more than “retrieve component A and paste it.” It needs at least:

a decomposition tree,

a layout classifier/predictor,

context-aware affine or nonlinear deformation for each component,

and optical correction after composition.

That is also why the vector component-composition paper emphasizes not just components, but layout information and learned transformations.

So my answer is:

Yes, your component-first idea is better than styling each full Chinese character independently.
But the real unit is not just “component.” It is:

component style + structural relation + context-dependent deformation.

For ComfyUI, that means the graph should probably look like this:

Node 1: input text

Node 2: decompose each character into IDS / HanziCraft-style component tree

Node 3: fetch styled component prototypes from your component bank

Node 4: predict layout transforms for each component

Node 5: compose raster or vector glyph

Node 6: optional refinement model for stroke cleanup / consistency

Node 7: assemble text line or export font glyph data

One important nuance: HanziCraft is very useful as a symbolic decomposition source, but based on its public pages it looks learner/decomposition-oriented rather than font-geometry-oriented. So I would treat it as a source for what parts a character contains, not as a complete source for how those parts should be drawn and positioned in a font. That second part still has to come from your own layout data or a trained model. That is an inference from the site’s published decomposition/frequency/phonetic focus.

So the shortest version is:

Your idea is sound.
The scalable path is not “generate 10,000 whole glyphs.”
It is learn a styled component inventory, then generate glyphs by structured composition.

The next design question is whether you want the system to be raster-first or vector-first. For a real font product, I would lean vector-first.


Other useful projects are a bit more “decomposition/data” than “finished colorizer.” HanziCraft breaks characters into components and highlights phonetic patterns; HanziVG provides SVGs plus metadata for radicals/components; Make Me a Hanzi provides downloadable dictionary and stroke-order vector data for 9,000+ common characters; and Radically is a component-based CJK search engine. Those are good foundations if you want to build a Canjile-like renderer yourself.

From the original thread.
And I find "http://gooo.free.fr/animHanzi/" that is using HanziVG to show each stroke to form a Chinese symbol

I am thinking that ComfyUI does not go over reconstruct, only style, leave reconstruction to other pipeline.
We need to adopt virtual coordinate concept and possible space partition such as quadtree, with the layer(z depth), etc.
Show more

I’m checking the stroke-data sources you mentioned against your proposed split—reconstruction outside ComfyUI, styling inside ComfyUI—because that separation is probably the make-or-break design choice here.

The stroke/vector side is looking promising: Make Me a Hanzi already exposes IDS decomposition plus per-stroke SVG paths on a fixed coordinate system, which fits your “virtual coordinates first, styling second” idea very well.

Thought for 1m 17s
Yes — that split makes sense to me.

I would treat reconstruction as a deterministic geometry pipeline and ComfyUI as a styling/refinement pipeline. That fits the available data sources surprisingly well: HanziCraft is useful for decomposition and “productive components,” HanziVG is aimed at stroke-order SVGs plus component/radical metadata, and Make Me a Hanzi already provides IDS-style decomposition, stroke-to-component matching, stroke SVG paths, medians, and even experimental animated SVGs.

Your virtual coordinate idea is especially strong because Make Me a Hanzi already uses a fixed coordinate system for strokes: its graphics.txt stores stroke SVG paths on a 1024×1024 coordinate space, and also provides medians for each stroke. It also includes a matches field that maps a character’s strokes back into its decomposition tree, which is exactly the kind of bridge you need between symbolic structure and drawable geometry.

So I would make the canonical representation:

Level 1: character structure tree
IDS / decomposition tree, not pixels.

Level 2: layout frames
each node gets a local box in normalized glyph space.

Level 3: component geometry
vector outlines, stroke paths, skeletons, medians.

Level 4: rendering/style layers
fill, edge roughness, brush texture, bleed, damage, ink pooling.

Level 5: export
raster preview, SVG, then font packaging.

That matches the way the public data is organized: HanziCraft and Make Me a Hanzi are strong on decomposition, while qiji-font shows that the downstream reconstruction/export side can live in a separate pipeline using OCR/selection, vector tracing, and FontForge packaging.

I would not make the quadtree your primary model. I would make the IDS/layout tree the primary model, and use a quadtree only as a helper for:

collision detection,

nearest-neighbor stroke queries,

tiled rasterization,

local repainting,

overlap/ink-bleed simulation.

Chinese glyph construction is fundamentally relational — left-right, top-bottom, enclosure, overlay, nested enclosure — and that is better captured by a decomposition/layout tree than by pure spatial partitioning. The quadtree is still useful, but as an acceleration structure, not the authoring structure. The matches and IDS fields in Make Me a Hanzi are a strong hint in that direction.

For z-depth, I think you are also right, but I would apply it carefully. In regular printed styles, z-depth can stay fairly shallow: component fill, stroke body, stroke edge, texture/effect overlays. In more handwritten or cursive styles, z-depth becomes more important because stroke crossings, stroke joins, dry-brush effects, and partial occlusions are part of the look. Since Make Me a Hanzi provides stroke order and stroke medians, you can use that as the base ordering signal before adding style-specific layering rules.

So the clean pipeline would be:

Text → character list

Character → decomposition tree
from HanziCraft / Make Me a Hanzi

Tree → normalized layout boxes
deterministic composition engine

Leaf components → canonical vector/stroke geometry

Geometry + masks → ComfyUI styling nodes
brush texture, roughness, aging, ink spread, emboss, carving, etc.

Styled components/strokes → compositor
obey layout tree and z-order

Final glyph → text layout / SVG / FontForge export

That division also fits ComfyUI’s role well: its strength is being a node/graph workflow interface that can chain multiple processing stages, not being the source of truth for CJK structural reconstruction.

The biggest technical risk is this: a component is not visually identical in every context. A left-side component often becomes narrower; a top component flatter; an enclosed component more compressed; some styles even change terminals or stroke joins depending on position. So the stored object should not just be “component bitmap.” It should be something like:

component ID

canonical local coordinate system

anchors / attachment points

deformation policy by context

style parameters

optional stroke graph

That is where your “virtual coordinates + space partition + layers” idea becomes much more than a renderer — it becomes a glyph scene graph.

My recommendation would be:

use IDS/layout tree as the canonical structure,

use normalized vector coordinates as the canonical geometry space,

use quadtree/BVH only for acceleration,

use z-depth mainly in the rendering layer,

and keep ComfyUI limited to styling/refinement, not reconstruction.

That gives you a system that can scale beyond 10,000 characters much better than full-glyph generation.

One extra useful detail: although I could not directly verify your exact animHanzi page because it timed out during fetch, Make Me a Hanzi explicitly points to a related gooo.free.fr stroke-order demo in its README, which reinforces that this ecosystem already supports animation/rendering from structured stroke data rather than from flat glyph images.

I can turn this into a concrete data schema next — for example, a JSON format for glyph_tree, component_instances, virtual_boxes, stroke_layers, and ComfyUI I/O nodes.


Might be this one "https://github.com/parsimonhi/animCJK"? not so sure.
So yes, glyph scene graph, that is what I want to define it.

I’m verifying animCJK and then I’ll pin down what a “glyph scene graph” should contain so it can drive both reconstruction and ComfyUI styling cleanly.

Thought for 18s
Yes — animCJK is very likely the repo you were looking for.

Why I think so:

animCJK says its purpose is to display kanji, kana, hanja, and hanzi stroke by stroke, and each character is stored as one or more SVG files with path data and CSS animation.

animHanzi is the older hanzi-specific project, and its README explicitly points to the demo at gooo.free.fr/animHanzi/ and lists KanjiVG and HanziVG as related work.

Make Me a Hanzi separately provides dictionary + graphics data for 9000+ common characters, including stroke-order vector graphics and an experimental tarball of animated SVGs.

So the rough lineage is:

HanziVG / KanjiVG / Make Me a Hanzi → structured stroke/vector data

animHanzi / animCJK → animated SVG rendering of that kind of data

your system → glyph scene graph as the canonical internal model, with ComfyUI only doing style/refinement

That is a solid architecture.

What the glyph scene graph should be
I would define it as a hierarchical, geometry-aware scene representation for a glyph, where the source of truth is not pixels but structured drawable objects.

A good top-level shape is:

{
  "glyph_id": "漢",
  "unicode": "U+6F22",
  "coord_space": {
    "type": "virtual",
    "width": 1024,
    "height": 1024,
    "origin": "top-left",
    "y_axis": "down"
  },
  "layout_tree": {},
  "component_instances": [],
  "stroke_instances": [],
  "render_layers": [],
  "constraints": [],
  "metadata": {}
}
Core objects
1. layout_tree
This is the most important part.

It should encode:

structural relation: left_right, top_bottom, enclose, overlay, surround, grid, single

parent-child nesting

normalized bounding boxes for each node

layout weights / ratios

optional deformation policy

Example:

{
  "id": "root",
  "type": "left_right",
  "bbox": [0, 0, 1024, 1024],
  "children": [
    {
      "id": "left_comp",
      "type": "leaf",
      "component_ref": "氵",
      "bbox": [0, 0, 360, 1024],
      "deform_policy": "compress_x"
    },
    {
      "id": "right_subtree",
      "type": "subtree",
      "bbox": [360, 0, 664, 1024]
    }
  ]
}
This should be the canonical reconstruction layer, not ComfyUI.

2. component_instances
These are reusable parts.

Each instance should have:

component_ref

local canonical geometry

anchors

attachment points

deformation parameters

style channels

{
  "id": "comp_01",
  "component_ref": "氵",
  "source": "component_bank",
  "canonical_bbox": [0, 0, 300, 1000],
  "placed_bbox": [0, 0, 360, 1024],
  "anchors": {
    "top": [150, 60],
    "center": [150, 500],
    "bottom": [150, 940]
  },
  "transform": {
    "scale_x": 1.18,
    "scale_y": 1.02,
    "shear_x": 0.0,
    "rotation": 0.0
  },
  "style_ref": "style_brush_ink_03"
}
3. stroke_instances
If you want fine-grained styling, this is where it gets powerful.

Each stroke can store:

SVG path

median / skeleton

stroke order

semantic label

parent component

z-order hint

{
  "id": "stroke_07",
  "component_id": "comp_01",
  "order": 2,
  "role": "dot",
  "path": "M ... Z",
  "median": [[120,140],[160,210],[185,290]],
  "bbox": [110, 130, 90, 180],
  "z": 20,
  "style_channels": {
    "pressure": 0.72,
    "dryness": 0.35,
    "edge_noise": 0.18
  }
}
This matches well with the kind of SVG-path stroke data exposed by animCJK and Make Me a Hanzi.

4. render_layers
This is where your z-depth idea belongs.

Keep z-depth mostly in rendering, not in logical decomposition.

Suggested layers:

skeleton

stroke_body

stroke_edge

texture_overlay

damage_mask

shadow_or_emboss

[
  {"name": "stroke_body", "z_min": 10, "z_max": 49},
  {"name": "stroke_edge", "z_min": 50, "z_max": 69},
  {"name": "texture_overlay", "z_min": 70, "z_max": 89}
]
Where quadtree fits
I would not use quadtree to define the glyph itself.

Use quadtree or BVH for:

hit testing

overlap detection

collision avoidance

local redraw

spatial lookup for nearby strokes/components

texture tiling

So:

scene graph = semantic + geometric truth

quadtree = acceleration/index structure

Best system split
I think your current split is the right one:

Outside ComfyUI
parse text

decompose characters

build layout tree

assign virtual boxes

instantiate components/strokes

perform deterministic composition

optionally export SVG masks / depth maps / control maps

Inside ComfyUI
style transfer on components or strokes

brush simulation

edge roughening

ink bleed / erosion / carving / printing defects

consistency refinement

optional raster finishing

That keeps ComfyUI where it is strongest: modular visual processing, not symbolic glyph assembly.

Minimal scene graph contract
If you want a first usable spec, I would define these required fields only:

{
  "glyph_id": "",
  "coord_space": {"width": 1024, "height": 1024},
  "layout_tree": {},
  "component_instances": [],
  "stroke_instances": [],
  "render_layers": [],
  "style_slots": {}
}
And these optional ones later:

constraints

anchors

collision_map

phonetic_semantic_tags

export_hints

font_metrics

My recommendation
Define the glyph scene graph around three invariants:

Structure is hierarchical

Geometry lives in a normalized virtual coordinate system

Styling is a separate transform, not part of reconstruction

That will scale much better than per-glyph generation.

A good next step is to formalize the node types:

GlyphNode

LayoutNode

ComponentNode

StrokeNode

StyleNode

MaskNode

and write one example end to end for a character like 語 or 漢.
