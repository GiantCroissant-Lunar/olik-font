# Map of Content (MOC) Patterns

An MOC is the landing page for a bucket — an entry point a reader lands on first. Not a dump of wiki-links, and not a substitute for the notes themselves.

Load this when building or revising an `index.md` for a bucket that's grown to 3+ notes, or when the current MOC feels like "just a file list".

## The three usable patterns

### Pattern A — Linear / chronological chain

Use when notes extend each other in a clear sequence (e.g. a branching AI thread, a design evolution, a daily log).

```markdown
## Branch chain

1. **[[discussion-0001]]** — Initial question. _Surveys existing projects._
2. **[[discussion-0002]]** — Extends with ComfyUI angle. _Conclusion: styled text yes, full font harder._
3. **[[discussion-0003]]** — Component-first pipeline. _Introduces scene-graph idea._
4. **[[discussion-0004]]** — Constraint-based scene graph. _IDS as bootstrap, not atomic._
```

- Numbered list preserves order.
- One-line italic summary per entry.
- Bold the wiki-link so it stands out in reading view.

### Pattern B — By role / kind

Use when a bucket has notes of different types: raw + distilled + diagrams + specs. Group by role, not by date.

```markdown
## Distilled output

- [[glyph-scene-graph-spec]] — the usable conclusion. **Start here.**
- [[glyph-scene-graph-pipeline.excalidraw]] — pipeline diagram.

## Raw sources

- [[discussion-0001]] … [[discussion-0004]] — AI thread branches.

## Pending
- [[open-questions]] — still unresolved.
```

- Every section has a short rubric.
- "Start here" is an explicit signpost for readers who don't want the whole pile.

### Pattern C — Reading orders

Use when the same material can be read several ways by different audiences.

```markdown
## If you want the quick takeaway
Read [[glyph-scene-graph-spec]] and look at [[glyph-scene-graph-pipeline.excalidraw]].

## If you want the full reasoning
Read [[discussion-0001]] → [[discussion-0002]] → [[discussion-0003]] → [[discussion-0004]] in order.

## If you're looking up external references
Jump to [Key external references](#key-external-references) below.
```

- Prose framing, not tables.
- Multiple valid paths through the same material.

## Opening paragraph

Every MOC needs 1–3 sentences at the top that answer "what is this folder, and why am I here?". Without it, wiki-link scanners can't tell the MOC apart from its contents.

## What an MOC is not

- Not an auto-generated file list. Use Dataview / folder listing for that, not a hand-written MOC.
- Not a copy of each note's intro. Summaries in the MOC are one-liners; full thoughts belong in the notes.
- Not a TODO board. Project state goes in a separate note.
- Not immortal. When a bucket collapses into one distilled note, the MOC can be deleted (and the single note promoted to landing page).

## Maintenance

- When a new note is added: add a line in the MOC.
- When a note is renamed: let Obsidian update the wiki-link automatically, or do it by hand if the edit came from outside Obsidian.
- When a note is archived: move the entry to an `## Archived` section at the bottom, don't delete.

## Naming

Prefer `index.md` per bucket (Obsidian promotes it as the folder's landing note). Acceptable alternatives: `<topic>-moc.md` when the MOC crosses buckets (e.g. a cross-cutting "all glyph-related notes" view).
