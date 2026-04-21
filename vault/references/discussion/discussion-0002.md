---
title: Can ComfyUI + existing font-gen repos produce styled Chinese fonts?
created: 2026-04-21
tags: [topic/chinese-font, topic/comfyui, topic/font-generation, type/ai-thread]
source: ai-thread
branch-from: "[[discussion-0001]]"
seq: 2
---

Is there any existing project to color Chinese symbol as Canjile does?

I’m checking what “Canjile” refers to and looking for similar Chinese-character coloring projects so I can compare actual existing tools, not guess.

Thought for 5m 4s
Assuming you mean coloring parts of a Chinese character by role or component rather than tone coloring, then yes, there are related projects. The closest ready-made example I found is Dong Chinese / Chinese Character Wiki: it explicitly color-codes character parts by function, such as meaning components in red, sound components in blue, iconic components in green, distinguishing components in purple, and unknown components in gray.

Other useful projects are a bit more “decomposition/data” than “finished colorizer.” HanziCraft breaks characters into components and highlights phonetic patterns; HanziVG provides SVGs plus metadata for radicals/components; Make Me a Hanzi provides downloadable dictionary and stroke-order vector data for 9,000+ common characters; and Radically is a component-based CJK search engine. Those are good foundations if you want to build a Canjile-like renderer yourself.

So the practical answer is:

Closest existing learner-facing project: Dong Chinese.

Best building blocks for your own project: HanziVG + Make Me a Hanzi, optionally with HanziCraft or Radically for decomposition/search.

If you want, I can also narrow this down to open-source libraries specifically suited to implement the same coloring style in a web app.

Branched from Chinese Character Color Projects


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

Thought for 5m 4s
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
