# Diagram Embedding

Reference for adding diagrams to `vault/` notes via the Obsidian Excalidraw plugin. Load this when a note needs a visual and SKILL.md's brief "use Excalidraw" line isn't enough.

## When to reach for a diagram

Pick one:

- **Pipeline / data flow** — stages transform inputs into outputs.
- **Hierarchy / scene graph** — parent-child structure.
- **State machine** — nodes = states, edges = transitions.
- **Component relationships** — how parts connect/overlap without a strict tree.

Skip a diagram when:

- The concept is still fluid. Draw once the design stabilizes.
- The content is a list or a table. Use a list or table.
- A screenshot or code listing would communicate the same thing.

## File format

Obsidian Excalidraw stores drawings as `.excalidraw.md`. These files:

- Render as Excalidraw drawings inside Obsidian.
- Round-trip cleanly to the upstream Excalidraw web editor.
- Can be embedded in other notes via `![[filename.excalidraw]]` (no `.md` suffix).

Minimum viable file:

````markdown
---
excalidraw-plugin: parsed
tags: [excalidraw]
---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠==

# Text Elements

# Drawing
```json
{"type":"excalidraw","version":2,"source":"obsidian-excalidraw-plugin","elements":[],"appState":{"gridSize":null,"viewBackgroundColor":"#ffffff"},"files":{}}
```
%%
````

## Seed vs. stub vs. finished

Three honest authoring modes:

- **Seed** — a file with ~3 labeled shapes + a TODO callout. Agent-authored. Purpose: save the user the first click. They finish in Excalidraw view.
- **Stub** — same as seed but includes arrow bindings and zones. Still rough geometry; user repositions before using for real.
- **Finished** — hand-polished in Excalidraw view. Never agent-authored.

Agents should usually produce a stub, not a finished diagram. Hand-authored JSON geometry is always coarser than what a human produces with the editor.

## Embedding in a host note

```markdown
## Diagram

Pipeline overview:

![[my-diagram.excalidraw]]

Open the source at [[my-diagram.excalidraw|diagram source]] to edit.
```

The `![[...]]` embed renders the drawing inline in reading view. A plain `[[...]]` link opens the file.

## Where to put diagrams

- **Next to the note they illustrate** when 1:1 (most common).
- **In `vault/<bucket>/diagrams/`** when many notes in a bucket share them.
- **Never under `assets/`** as a raw PNG — prefer editable `.excalidraw.md` so the diagram can evolve.

## Citing Excalidraw internals

When a diagram needs behavior beyond what's documented on the plugin page (custom element types, programmatic manipulation), read the upstream source at `ref-projects/excalidraw/`. See the `@ref-projects` skill for the clone — **never edit** that directory.

## Common authoring issues

- **Hand-authored JSON looks crooked on first open.** Expected. The plugin normalizes the file on its first real edit. Drag an element, save, done.
- **Arrows don't follow moved boxes.** `startBinding` / `endBinding` must reference the target element's `id`. If they don't, Excalidraw treats the arrow as unbound geometry.
- **Embed shows nothing.** Check the `.excalidraw.md` file actually parses — the plugin silently fails on malformed frontmatter. The `excalidraw-plugin: parsed` line is required.
- **Diagram renders but text is missing in reading view.** Text elements need both a `text` field and a matching `originalText`. Omitting `originalText` causes this.
