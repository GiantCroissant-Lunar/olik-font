# Intake Checklist

Use when the user drops raw external material (URLs, pasted AI threads, article text, PDFs) and asks to "organize it" or "file it into the vault".

## Before touching any files

- [ ] Confirm the target bucket. Usually `vault/references/<kind>/`. If no existing bucket fits, propose a name and ask.
- [ ] Check for a numbering convention already in use in that bucket (e.g. `discussion-0001.md`). Match it, zero-padded.
- [ ] Check whether an MOC (`index.md`) already exists in the bucket. If yes, plan to update it. If no, plan to create one once there are 3+ related notes.

## Preserve raw

- [ ] Save the raw material under `vault/references/<kind>/<name>-NNNN.md`.
- [ ] Add minimum frontmatter (`title`, `created`, `tags`, `source`). See [[frontmatter-fields]] for note-type-specific fields.
- [ ] For branching threads (NotebookLM-style), add `branch-from`, `branch-root`, `seq`.
- [ ] **Do not edit the body** of raw material. Formatting tweaks (e.g. fixing garbled whitespace) are fine; rewriting the content is not.

## Distill (optional but usually worth it)

- [ ] If the raw material has a clear thesis, design conclusion, or list of claims, write a separate `<topic>-spec.md` or `<topic>-notes.md`.
- [ ] Link back to the raw note(s) via `distilled-from` frontmatter.
- [ ] Body structure: one-line summary → why → key points → pending questions → see-also.
- [ ] Keep opinions / claims attributed to the raw note, not stated as settled fact, unless they are.

## Diagram (optional)

- [ ] If the design has spatial, hierarchical, or flow structure, a diagram is worth one. See [[diagram-embedding]] for the Excalidraw approach.
- [ ] Skip the diagram if the design is still fluid. Drawing unstable ideas creates noise.

## Index

- [ ] Create or update `vault/references/<kind>/index.md`.
- [ ] List notes in reading order (chronological, dependency, or most-important-first).
- [ ] Give each a one-line summary — not a dump of titles.
- [ ] Mark which note is the distilled conclusion vs. raw source material.

## Verify

- [ ] Open one of the notes and check wiki-links resolve (unresolved links show up differently in Obsidian).
- [ ] Check the MOC lists every new note exactly once.
- [ ] If the distilled note references a diagram, check the `![[...]]` embed renders.

## Don't

- Don't rename raw notes in place after publishing. Wiki-links elsewhere will break silently.
- Don't copy raw content into the distilled note. Link, don't duplicate.
- Don't put intake-stage metadata ("need to review", "TODO categorize") in frontmatter tags. Put it in the body as a checklist, and remove it when done.
