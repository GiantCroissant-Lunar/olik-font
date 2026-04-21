---
title: Existing projects for coloring Chinese character components
created: 2026-04-21
tags: [topic/chinese-font, topic/decomposition, type/ai-thread]
source: ai-thread
branch-root: true
seq: 1
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
