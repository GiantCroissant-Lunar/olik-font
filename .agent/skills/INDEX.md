# Skills Index

Numbered categories create an implicit dependency hierarchy — lower numbers are more foundational and consumed by higher-numbered layers. Gaps (e.g. no `01`, `02`, `03`) are intentional placeholders that align with sibling projects; don't renumber to remove them.

## 00-meta — Governance & Organization

| Skill | Description | Related Skills |
|---|---|---|
| `vault-obsidian` | Manage the Obsidian vault at `vault/`: frontmatter conventions, wiki-links, MOCs, intake workflow for external material, Excalidraw diagrams. All notes-as-knowledge-graph discipline lives here. | `@notebooklm-cli`, `@ref-projects`, `@youtube-gemma` |
| `archon-workflows` | Deterministic, worktree-isolated AI coding workflows (plan → implement → validate → review → PR). Codex SDK only on this project — no Claude Code SDK. Non-Codex assistants run via `bash:` nodes. | `@coding-providers`, `@vault-obsidian` |

## 05-engine — Domain engineering discipline

| Skill | Description | Related Skills |
|---|---|---|
| `glyph-geometry` | **Invoke whenever anything touches component placement** (decomposition schemas, compose, extraction plans, slot logic, variant matching, renderer math). Enforces the virtual-coordinate rule from the glyph scene graph spec (D4): a component instance carries a measured affine transform in 1024² virtual space. Presets (left_right / top_bottom / enclose / repeat_triangle) are never primary data; global slot-weight constants are forbidden. | `@vault-obsidian`, `@archon-workflows` |

## 04-tooling — Automation & Reference

| Skill | Description | Related Skills |
|---|---|---|
| `notebooklm-cli` | Drive Google NotebookLM from the terminal via `nlm`: install, frequent re-login, profiles, sources, query. Free-tier-aware usage — organization over heavy generation. | `@vault-obsidian` |
| `ref-projects` | Manage read-only upstream clones under `ref-projects/`. Hard rule: never edit, stage, or commit anything in there. Clone / update / cite by path only. | `@vault-obsidian` |
| `youtube-gemma` | Local-leaning YouTube intake: `yt-dlp` → whisper transcription → Gemma 4 (`gemma4:31b` by default) analysis → vault note. Counterpart to `@notebooklm-cli` for offline / private / one-shot videos. | `@vault-obsidian`, `@notebooklm-cli` |
| `coding-providers` | One CLI, one job. **Pi** (`@mariozechner/pi-coding-agent`) scoped to ZAI / GLM only. **Codex CLI** = OpenAI + Archon's SDK backend. **Kimi CLI** = Moonshot. **Copilot CLI** = optional GitHub-native. **Ollama cloud** = Gemma 4. Includes deliberately-not-used rationale for LiteLLM / Mastra. | `@archon-workflows`, `@youtube-gemma` |

## Typical Workflows

**Intake external references into the vault**

```
@notebooklm-cli  (pull URLs into a NotebookLM notebook, query for summary)
      ↓
@vault-obsidian  (save raw + distilled notes with frontmatter, update MOC, add diagram)
```

**Intake a YouTube video locally**

```
@youtube-gemma   (yt-dlp → whisper → gemma4:31b analysis)
      ↓
@vault-obsidian  (transcript + distilled analysis under vault/references/youtube/)
```

**Study upstream code while writing a spec**

```
@ref-projects    (clone repo, read/grep — never modify)
      ↓
@vault-obsidian  (cite files by path from a spec note)
```

**Deterministic multi-step AI coding task**

```
@coding-providers  (pick Codex provider + optional bash-node assistants)
      ↓
@archon-workflows  (plan → implement → validate → review → PR in isolated worktree)
      ↓
@vault-obsidian    (archive the plan / review notes if worth keeping long-term)
```

## Frontmatter Schema

Every `SKILL.md` has YAML frontmatter with these fields:

```yaml
---
name: skill-name                    # unique identifier
description: ...                    # triggers skill loading — be specific + a little pushy
category: 00-meta                   # matches the numbered directory
layer: governance|tooling           # implicit dependency tier (see below)
related_skills:                     # @skill-name cross-references
  - "@other-skill"
---
```

**Layers** (lower consumes higher):

- `governance` — meta-skills that shape how other skills and agents operate (vault organization, workflow orchestration).
- `tooling` — automation, external-service wrappers, provider routing, reference-material management.

Additional layers (`presentation`, `world`, `gameplay`, …) are reserved for future categories if this project grows into them. See the sibling `legend-dad` project for precedent. The `engine` layer is already active (see `05-engine/glyph-geometry`).

## Project-level conventions

These apply to every skill and every agent session on this project:

- **Archon uses Codex SDK only** for AI nodes. No Claude Code SDK. Non-Codex assistants (Pi / Kimi / Copilot) run via `bash:` nodes. See `@archon-workflows`.
- **Archon's backing store is PostgreSQL**, not SQLite. Local container or managed instance, never the default SQLite file.
- **One CLI, one job.** Pi is scoped to ZAI / GLM only on this project (even though upstream Pi supports many providers). Codex CLI = OpenAI + Archon's SDK backend. Kimi CLI = Moonshot. Copilot CLI = optional GitHub shell helpers. Don't blend roles.
- **Cloud Gemma 4, not local.** Default is `gemma4:31b`. That size is too large to run locally — cloud routing via `ollama signin` is the only practical path. Never `ollama pull gemma4:31b`. Smaller Gemma 4 tags (`:e2b`, `:e4b`, `:26b`) can run locally but are too weak for real work here, so we don't use them either.
- **No LiteLLM / Mastra.** Pi already unifies providers; adding a router is overhead. Revisit only if the project outgrows Pi + Codex + Archon.
- **`ref-projects/` is read-only.** Enforced by `@ref-projects`.
- **OAuth-only for Codex and Copilot CLIs.** Both CLIs *support* env-var auth (`OPENAI_API_KEY`, `COPILOT_GITHUB_TOKEN`) but on this project we log in interactively. Keeps auth rotation tied to the subscription and avoids plaintext keys in env files. Kimi CLI is OAuth-only anyway.
- **Secrets in `infra/.env`, not in skills or committed configs.** On this project env-var auth applies only to Pi (ZAI), Ollama, and the optional Kimi SDK fallback.

## Conventions

- **Cross-references** use `@skill-name` notation everywhere — in frontmatter, INDEX tables, and SKILL.md prose.
- **Category folders are numbered + zero-padded** (`00-meta`, `04-tooling`). Lexical sort matches reading order.
- **One SKILL.md per folder.** Companion files (references, assets, scripts) live inside that same folder as per the skill-creator spec.
- **Read-only directories** (`ref-projects/`, external vendor trees) are enforced by their owning skill, not by a global rule.

## See also

- `/AGENTS.md` (local, gitignored) — project-level agent instructions, tool preferences, scratch notes. Each developer maintains their own copy.
- `/CLAUDE.md` — pointer to `AGENTS.md` for Claude Code / other AGENTS.md-aware harnesses.
- `vault/references/discussion/index.md` — entry point for the current design thread (glyph scene graph).
