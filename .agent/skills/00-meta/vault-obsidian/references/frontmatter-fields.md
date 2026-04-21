# Frontmatter Fields

Reference for YAML frontmatter on notes under `vault/`. Load this when writing frontmatter for a note type not covered by the minimum fields in SKILL.md.

## Minimum (every note)

```yaml
---
title: Short human-readable title
created: YYYY-MM-DD
tags: [topic/..., type/...]
source: external | self | ai-thread
---
```

## By note type

### `type/discussion` — raw AI thread or conversation dump

```yaml
branch-root: true          # only for the root of a branching thread
branch-from: "[[prev]]"    # wiki-link to the parent branch
seq: 1                     # ordinal in the thread
```

### `type/distilled` — a cleaned-up spec derived from raw material

```yaml
distilled-from:
  - "[[discussion-0003]]"
  - "[[discussion-0004]]"
status: draft | review | stable | archived
```

### `type/moc` — Map of Content / index

No extra fields. Body is a structured list of wiki-links with one-line summaries.

### `type/diagram` — Excalidraw or image-based note

```yaml
excalidraw-plugin: parsed  # required for .excalidraw.md
# or, for a regular note embedding an image:
cover: path/to/image.png
```

### `type/spec` — design document

```yaml
status: draft | accepted | superseded
supersedes:
  - "[[old-spec]]"
superseded-by: "[[new-spec]]"   # set when archiving
```

### `type/daily` — daily log / journal

```yaml
date: YYYY-MM-DD            # same as created, but required for dataview queries
```

## Tag conventions

- `topic/*` — subject matter: `topic/chinese-font`, `topic/scene-graph`, `topic/comfyui`.
- `type/*` — note role: `type/discussion`, `type/distilled`, `type/spec`, `type/moc`.
- Keep values lowercase-kebab. Avoid spaces.
- Prefer hierarchical tags over flat ones — `topic/chinese-font/decomposition` is fine.

## Linking from frontmatter

Wiki-links inside YAML must be quoted strings: `"[[note-name]]"`. Without the quotes, YAML treats `[[` as array syntax and the link breaks.

## Don't put in frontmatter

- Long-form content (put it in the body).
- Timestamps more precise than a date, unless the note is a log entry.
- Redundant copies of info that lives in the body (e.g. a one-line summary is fine, a full abstract is not).
