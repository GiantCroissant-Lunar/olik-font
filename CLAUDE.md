# CLAUDE.md

This project uses `AGENTS.md` as the canonical agent-instruction file. `AGENTS.md` is **local and gitignored** — each developer maintains their own copy.

**If `AGENTS.md` exists in this repo root, read it now and treat its contents as authoritative for this project.** Fall back to `.agent/skills/INDEX.md` for the committed skill inventory when `AGENTS.md` is absent (e.g. on a fresh clone before the developer has populated one).

## Why the indirection

- `AGENTS.md` is the emerging cross-tool convention (Claude Code, Cursor, Aider, etc. all read it).
- Keeping it gitignored lets each developer customize tool preferences, machine-specific paths, and in-progress agent notes without polluting shared history.
- Shared, committed agent guidance lives under `.agent/skills/` (with `INDEX.md` as its entry point), not here.

## On a fresh clone

If `AGENTS.md` is missing, start from the template commented at the top of `.agent/skills/INDEX.md` or copy a teammate's structure. Don't commit your populated version.
