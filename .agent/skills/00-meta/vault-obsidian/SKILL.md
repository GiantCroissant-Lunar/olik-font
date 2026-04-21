---
name: vault-obsidian
description: Use when working with anything under `vault/` — this is an Obsidian vault, not a plain docs folder. Triggers whenever the user asks to add, organize, rename, index, link, or diagram notes under vault/, especially under vault/references/ (external material being curated). Also use when the user pastes raw content (NotebookLM threads, articles, conversation dumps) and wants it filed cleanly into the vault. Follow Obsidian conventions: YAML frontmatter, wiki-links, Maps of Content, and Excalidraw diagrams for visual explanations. Do NOT treat vault/ files as ordinary markdown — they are part of a graph-linked knowledge base.
category: 00-meta
layer: governance
related_skills:
  - "@notebooklm-cli"
  - "@ref-projects"
---

# Obsidian Vault Management (`vault/`)

`vault/` is an Obsidian vault. Edits here need to respect Obsidian conventions so links, graph view, and future-you all keep working.

## Current layout

```
vault/
└── references/           # external material curated into the vault
    └── discussion/       # branching AI discussion threads, numbered
        ├── discussion-0001.md
        ├── discussion-0002.md
        └── ...
```

Expect this to grow. New top-level buckets under `vault/` are fine when needed (e.g. `vault/ideas/`, `vault/specs/`, `vault/daily/`), but don't invent one before asking if the user already has a home for the content.

## Obsidian conventions to follow

### 1. Frontmatter on every note

Every `.md` file gets YAML frontmatter at the very top. Minimum fields:

```yaml
---
title: Short human-readable title
created: 2026-04-21
tags: [topic/font-gen, type/discussion]
source: external | self | ai-thread
---
```

Extend with note-type-specific fields (`branch-from`, `url`, `project`, `status`, etc.) as the content calls for it. Keep tag values hierarchical and lowercase-kebab.

### 2. Wiki-links, not relative paths

Link between notes with `[[Note Name]]` or `[[Note Name|display text]]`, not `[path/to/file.md](path/to/file.md)`. Obsidian resolves by note title, so wiki-links survive moves and renames.

Exception: for files outside the vault (e.g. skill files, source code), use normal markdown links with repo-relative paths.

### 3. Maps of Content (MOCs)

For any bucket with 3+ related notes, add an `index.md` (or `<topic>-moc.md`) that:

- Lists the notes in a sensible order (chronological, dependency, or reading order).
- Gives each a one-line summary.
- Calls out which note is the distilled conclusion vs. which are raw source material.

An MOC is the entry point — treat it as a landing page, not a dump of links.

### 4. Numbered sequences stay zero-padded

Existing convention: `discussion-0001.md`, `discussion-0002.md`. Keep the 4-digit padding so lexical sort matches chronological order. Do the same for any future numbered series.

### 5. Don't rename raw external material in place

When the user pastes a raw NotebookLM thread / article / conversation, preserve it as-is (just add frontmatter and maybe a trailing `## Links` section). Distillation, cleanup, and restructuring go into a *separate* note that links back to the raw one. That way the source of truth is never lost.

## Intake workflow: turning external content into vault notes

When the user drops raw references (URLs, pasted conversations, PDFs, etc.) and asks to "organize" them:

1. **Identify the right bucket.** `vault/references/<kind>/` for external material. If no existing bucket fits, propose a name before creating one.
2. **Preserve raw first.** Save the raw material under `vault/references/<kind>/<name>-NNNN.md` with frontmatter. Don't edit the body.
3. **Distill second (optional).** If the content has a clear thesis or design conclusion, write a separate `<topic>.md` note that captures just the distilled claim + links back to the raw note(s).
4. **Link with an MOC.** Create or update an `index.md` in the bucket that orders the notes and summarizes each.
5. **Add a diagram if it helps.** For design-heavy content, a single diagram often replaces several paragraphs — see below.

## Diagrams — use Excalidraw

When a note would benefit from a picture (scene graphs, pipelines, state machines, component hierarchies), embed an Excalidraw drawing. Obsidian's Excalidraw plugin stores them as `.excalidraw.md` files that both render in Obsidian and round-trip cleanly to the upstream Excalidraw editor.

- Store drawings next to the note they illustrate, or in a `vault/<bucket>/diagrams/` folder if many notes share them.
- Reference Excalidraw's own source when you need to understand its file format — see the `ref-projects` skill for how to read the cloned repo at `ref-projects/excalidraw/` without modifying it.
- Prefer one clear diagram over multiple overlapping ones. If the user's design concept is still fluid (e.g. the glyph scene graph discussions), add the diagram only after the design stabilizes — otherwise you're drawing noise.

## When to ask before acting

- Creating a **new top-level folder** under `vault/` — ask.
- **Renaming or moving** an existing note — ask, because wiki-links elsewhere may depend on the current name. (Obsidian auto-updates links inside the app, but agents editing files on disk don't get that magic.)
- **Rewriting** raw external material — don't; distill into a separate note instead.
- **Deleting** anything — always ask.

Fine to do without asking:

- Adding frontmatter to a note that lacks it.
- Creating or updating an MOC `index.md`.
- Writing a new distilled note that links to existing raw notes.
- Fixing obviously broken wiki-links.

## Cross-tool notes

Obsidian itself isn't required to be running. All operations here are plain filesystem edits on `.md` files — they'll work identically from Claude Code, Copilot CLI, or Codex. When Obsidian is running, it will pick up changes on its own.

## Deeper references (load on demand)

The files under `references/` next to this SKILL.md expand on specific tasks. Load the one you need; don't pre-read all of them.

- `references/frontmatter-fields.md` — full frontmatter field reference by note type (discussion, distilled, spec, diagram, daily). Use when writing frontmatter for a note type not covered above.
- `references/intake-checklist.md` — step-by-step checklist for filing raw external material into the vault. Use when the user drops URLs / pasted threads / article text and wants them "organized".
- `references/moc-patterns.md` — three patterns for structuring an `index.md` (linear chain, by role, multiple reading orders). Use when building or revising an MOC.
- `references/diagram-embedding.md` — Excalidraw file format, seed vs. stub vs. finished distinction, embedding syntax, common authoring pitfalls. Use when a note needs a diagram.

## Interaction with other skills

- **`notebooklm-cli`** — intake often starts there (pull URLs into a NotebookLM notebook, query for a summary) and ends here (save the summary + raw material into the vault).
- **`ref-projects`** — when referencing upstream library source in a note, link by repo-relative path into `ref-projects/`, never copy the code in.
