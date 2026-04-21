---
name: ref-projects
description: Use whenever the user wants to clone an upstream repo for LOCAL reference (read-only study of its source), or asks to look something up inside an already-cloned repo under `ref-projects/`. Triggers on phrases like "clone X for reference", "check how Y does it", "pull that repo into ref-projects", "look at the excalidraw source". Enforces the hard rule that NOTHING under `ref-projects/` is ever edited, staged, or committed — the directory is gitignored precisely because these are scratch references, not fork work. If the user actually wants to modify an upstream project, that belongs in a different directory and a different workflow.
category: 04-tooling
layer: tooling
related_skills:
  - "@vault-obsidian"
---

# `ref-projects/` — Read-Only Upstream References

`ref-projects/` holds git clones of upstream projects kept locally so we can read the source, search it, and cite it from notes and skills. It is **not** a workspace for modifying those projects.

`ref-projects/` is listed in the repo's `.gitignore`. Nothing inside it is ever part of our git history.

## The one hard rule

**Never edit, stage, commit, delete, or push anything under `ref-projects/`.**

This rule exists because:

- These are upstream projects with their own maintainers and license terms. Accidental local edits create confusing "is this the real source?" situations.
- Agents that happily run `git add -A` from the repo root could otherwise stage thousands of upstream files if `ref-projects/` weren't gitignored. The gitignore is the safety net; this rule is the intent.
- We cite these repos from our own notes/skills by path. If we modify them, our citations become lies.

If an upstream bug or improvement is worth making, that's a **separate workflow**: fork the repo elsewhere outside this directory, send a PR upstream, then pull the updated release back into `ref-projects/` via a clean re-clone.

## Current contents

```
ref-projects/
└── excalidraw/    # upstream: https://github.com/excalidraw/excalidraw
                   # used by: vault-obsidian skill (diagrams)
```

When adding a new entry, update this list (or better, just `ls ref-projects/` — it's self-documenting).

## Adding a new reference project

```bash
# From repo root
cd ref-projects
git clone --depth 1 https://github.com/<owner>/<repo>.git
cd ..
```

Notes:

- `--depth 1` keeps the clone small. We don't need history for reference.
- If the user wants a specific tag/commit, use `git clone --branch <tag> --depth 1 ...` or clone full and `git checkout <sha>` once. Either way, note the pinned ref in whichever skill/MOC cites this project.
- Confirm with the user before cloning anything large (> ~500MB) or anything outside the stated purpose of this directory.

## Updating a reference project

Refreshing to a newer upstream version:

```bash
cd ref-projects/<repo>
git fetch --depth 1 origin
git reset --hard origin/HEAD    # or a specific tag
```

This is the **one time** a destructive git command is acceptable inside `ref-projects/` — because we are deliberately resyncing to upstream, not preserving local work. Still, confirm with the user first: "refresh ref-projects/<repo> to latest upstream?"

## Reading and searching

Standard tools work fine:

- `Read` / `cat` for files by path.
- `Grep` across the whole ref-project to find symbols.
- `Glob` for file discovery.

When citing a ref-project from another skill, a vault note, or the user's code, use the repo-relative path: `ref-projects/excalidraw/packages/excalidraw/data/encode.ts`. That path is stable as long as we don't reclone with a breaking upstream restructure.

## Removing a reference project

```bash
rm -rf ref-projects/<repo>
```

Confirm with the user first. Also check whether any vault notes or skills cite it — if yes, either update those citations or leave the clone in place.

## Anti-patterns to watch for

- **Editing upstream source to "just fix this one thing"**. Don't. If the fix matters, it belongs upstream or in a real fork outside this directory.
- **Running the upstream project's build tooling from within `ref-projects/`** in a way that generates untracked artifacts (node_modules, dist, .cache). The gitignore hides them from git, but they still clutter the clone and can confuse later Greps. If a user actually wants to run the ref-project, do it in a scratch copy elsewhere.
- **Copy-pasting whole files from a ref-project into our own code**. Prefer importing via package manager when possible, or link by path when the reference is just for understanding. Copying obscures licensing and diverges from upstream.
- **Staging `ref-projects/` manually to bypass the gitignore**. Never do this. If an agent sees a reason to commit something from here, that reason is wrong.

## Cross-tool notes

The git clone / read / search commands are standard shell — works identically from Claude Code, Copilot CLI, or Codex. No platform-specific logic.

## Interaction with other skills

- **`vault-obsidian`** — when a note needs a diagram, `ref-projects/excalidraw/` is the source of truth for the `.excalidraw.md` file format. Link by path; don't duplicate code.
- **Any skill that cites an upstream library** — prefer `ref-projects/<repo>/path/to/file` over inline code quotes when the source is long. The reader can jump to the exact file locally.
