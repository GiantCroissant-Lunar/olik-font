---
name: archon-workflows
description: Use when the user wants to run deterministic, worktree-isolated AI coding workflows — plan → implement → validate → review → PR — in a repeatable way. Triggers on phrases like "use archon", "set up a workflow for X", "run this in parallel worktrees", "make this change deterministic", or when the user wants fire-and-forget multi-step AI coding automation. On this project, Archon is configured to use Codex SDK ONLY as its AI-node backend (no Claude Code SDK). Non-Codex assistants (Pi CLI, Kimi CLI, Copilot) are invoked from `bash:` nodes instead. Provider / model choice lives in @coding-providers.
category: 00-meta
layer: governance
related_skills:
  - "@coding-providers"
  - "@vault-obsidian"
---

# Archon Workflows

Archon (github.com/coleam00/Archon) is a workflow engine that encodes your development process as YAML: plan → implement → validate → review → PR. Each run goes into its own git worktree, so multiple workflows run in parallel without conflicts. Think "GitHub Actions for AI coding", not "LiteLLM".

## Architecture in one diagram

```
Platform Adapters (Web UI, CLI, Telegram, Slack, Discord, GitHub)
                         │
                         ▼
                  Orchestrator
       (Message Routing & Context Management)
                         │
    ┌────────────────────┼────────────────────┐
    ▼                    ▼                    ▼
Command Handler    Workflow Executor    AI Assistant Clients
   (Slash)              (YAML)          (Codex SDK — this project)
    │                    │                    │
    └────────────────────┴────────────────────┘
                         │
                         ▼
          SQLite / PostgreSQL (7 tables)
  Codebases • Conversations • Sessions • Workflow Runs
   Isolation Environments • Messages • Workflow Events
```

Two things to notice:

- **Only Codex SDK is wired as an AI-node backend on this project.** Archon upstream ships Claude Code SDK as another option, but we are not using it — Codex SDK handles all AI nodes, and it in turn can dispatch to OpenAI or any OpenAI-compatible provider (see `@coding-providers` for Z.ai GLM, Moonshot Kimi routing through Codex, and the Ollama cloud Gemma 4 bridge).
- **Non-Codex assistants go through `bash:` nodes.** Pi CLI (Z.ai), Kimi CLI, and Copilot CLI all have their own terminal interfaces — use a `bash:` node to invoke them. They do not plug into Archon's AI-node slot.
- **Platform adapters are interchangeable.** You drive the same workflow from a terminal, a web dashboard, a Slack thread, or a GitHub comment. Workflow definition stays in `.archon/workflows/*.yaml`, checked into the repo.

## When this skill applies

- User wants a **deterministic** AI coding flow — same phases every time, validation gates, no model-of-the-day drift.
- User wants **parallel fire-and-forget** runs — "kick off three features, come back to three PRs".
- User wants to **encode a team process** (planning template, validation gates, PR format) into something executable.
- User wants a **worktree-isolated** run — current working tree shouldn't change mid-task.

## When it doesn't

- **Any multi-provider routing question** — that's `@coding-providers`, not this skill. Archon orchestrates; it doesn't route.
- One-off exploratory coding — the overhead of a YAML workflow isn't worth it. Just use the assistant directly.
- Research / Q&A tasks — workflows are for producing diffs and PRs, not for answering questions.
- Prototyping the workflow itself — iterate in plain Claude Code first, then formalize into YAML once the steps are stable.

## One-time setup

Prereqs: Bun, `gh` CLI, **Codex CLI** (no Claude Code — we don't use its SDK adapter on this project).

```bash
# Bun
curl -fsSL https://bun.sh/install | bash

# gh
brew install gh

# Codex CLI — install per @coding-providers (exact command there)

# Archon
git clone https://github.com/coleam00/Archon ~/src/Archon
cd ~/src/Archon && bun install

# Quick-install binary alternative
curl -fsSL https://archon.diy/install | bash
# or
brew install coleam00/archon/archon
```

Minimum config — edit `~/.archon/config.yaml` so Codex is the only active assistant, Claude is disabled, and the backend is PostgreSQL:

```yaml
database:
  type: postgres                              # this project uses PostgreSQL, not SQLite
  url: postgres://archon:<pw>@localhost:5432/archon
  # or discrete host/port/user/password/database fields, per Archon's schema

assistants:
  codex:
    enabled: true
    codexBinaryPath: /Users/<you>/.local/bin/codex   # or `which codex`
    defaultProvider: openai                          # see @coding-providers for others
  claude:
    enabled: false                                   # explicitly off on this project
```

**Why PostgreSQL and not SQLite:** SQLite is the easy-mode default, but we prefer Postgres here for (a) concurrent worktree runs touching the same conversations/events tables, (b) clean backup/restore via standard tooling, (c) the option of a shared Archon instance later. Point Archon at a local Postgres container (e.g. via `infra/`) or a managed instance — just don't leave it on SQLite.

Quick local Postgres:

```bash
# Docker
docker run -d --name archon-pg \
  -e POSTGRES_USER=archon -e POSTGRES_PASSWORD=<pw> -e POSTGRES_DB=archon \
  -p 5432:5432 postgres:16

# Or Homebrew
brew install postgresql@16 && brew services start postgresql@16
createuser -s archon && createdb -O archon archon
```

Confirm with `archon doctor` (or the wizard's check command) that only Codex is listed as active and the Postgres connection resolves.

## Workflow file layout

```
<project-root>/
└── .archon/
    └── workflows/
        ├── build-feature.yaml
        ├── fix-bug.yaml
        └── refactor-module.yaml
```

Commit `.archon/workflows/*.yaml` — they're part of the team's process. Don't commit `~/.archon/config.yaml` (that's local, has credentials).

## Workflow node types

Minimal vocabulary to know when reading or writing YAML:

| Node key | Purpose |
|---|---|
| `prompt:` | AI node — runs the assistant client with the given prompt. |
| `bash:` | Deterministic node — runs a shell command, no AI. |
| `loop:` | Repeat until a condition or `APPROVED` from a human. |
| `depends_on:` | Sequence / parallelism control. |
| `fresh_context: true` | Start the AI with an empty context (prevents drift in long loops). |
| `interactive: true` | Pause for human input — approval gates, clarifying questions. |

Canonical example (AI nodes resolve to Codex SDK; other CLIs run via `bash:`):

```yaml
# .archon/workflows/build-feature.yaml
nodes:
  - id: plan
    prompt: "Explore the codebase and create an implementation plan."

  - id: implement
    depends_on: [plan]
    loop:
      prompt: "Read the plan. Implement the next task. Run validation."
      until: ALL_TASKS_COMPLETE
      fresh_context: true

  - id: run-tests
    depends_on: [implement]
    bash: "bun run validate"

  - id: review
    depends_on: [run-tests]
    prompt: "Review all changes against the plan. Fix any issues."

  - id: glm-second-opinion
    depends_on: [review]
    # Non-Codex assistant via bash: — Pi routing to ZAI GLM for a cross-provider review
    bash: |
      git diff HEAD~1 | pi --model "zai/glm-4.6" -p "Review this diff for correctness. List issues as bullets."

  - id: approve
    depends_on: [glm-second-opinion]
    loop:
      prompt: "Present the changes + Kimi's notes. Address feedback."
      until: APPROVED
      interactive: true

  - id: create-pr
    depends_on: [approve]
    prompt: "Push changes and create a pull request."
```

The `glm-second-opinion` pattern generalizes — swap in Kimi CLI for long-context review, or Copilot CLI for a GitHub-native take. See `@coding-providers` for the exact invocations.

## Running a workflow

From the target project, invoke Archon via its CLI (we don't chain through Claude Code since the Claude SDK is off):

```bash
archon run build-feature --arg "issue=42"
```

Or via whichever platform adapter is configured (Web UI, Slack, Telegram, GitHub comment). Archon's own skill, when installed into a host assistant, works the same way — it'd invoke `archon run` under the hood.

What actually happens:

1. Archon creates a new worktree on branch `archon/task-<slug>`.
2. Nodes run in dependency order. AI nodes dispatch to the configured assistant client (Claude / Codex).
3. `bash:` nodes run deterministically — failures stop the workflow unless the node says `continue_on_error: true`.
4. Interactive nodes pause and wait for input via whichever platform adapter you're on.
5. On success, the worktree is cleaned up; the PR stays.

## Archon's own skill vs. this skill

Archon installs its own skill into host assistants that support skills. That skill knows how to invoke workflows from a prompt. **This skill you're reading is higher-level** — it explains *when* to reach for Archon at all, our project-specific constraint (Codex SDK only, no Claude SDK), and how Archon fits with `@coding-providers` and `@vault-obsidian`.

If the Archon-installed skill and this one disagree on a command, trust the Archon-installed one — it's generated against the exact installed version. If they disagree on **assistant choice** (the installed one says "use Claude"), trust this one — the project-level rule wins.

## When to write a new workflow vs. one-shot

Write a `.archon/workflows/*.yaml` when:

- You've done the same multi-step task 3+ times.
- The team wants the same validation gates every time (e.g. "always run biome + ruff before PR").
- Steps must be parallelizable (run 5 of these concurrently).

Stay one-shot (plain `claude`) when:

- You're still figuring out the right steps.
- The task is unique — no future repeats likely.
- You need flexibility mid-task in a way YAML can't express.

## Relation to other skills

- **`@coding-providers`** — pick which model/provider runs inside Archon's AI nodes. Archon orchestrates; `@coding-providers` routes.
- **`@vault-obsidian`** — archive the PR plan / review notes into the vault when a workflow produces a design artifact worth keeping long-term.
- **`@ref-projects`** — if a workflow needs to read upstream source, it reads from `ref-projects/` (read-only).

## Gotchas

- **Don't commit `~/.archon/config.yaml`.** It has credentials and per-machine paths.
- **Worktrees can stack up.** Archon cleans after success; failed runs may leave worktrees around. Periodically `git worktree list` and prune.
- **Interactive nodes block the platform adapter** — on Slack/Telegram, the bot waits for a reply. Don't set `interactive: true` in a workflow you intend to run truly fire-and-forget.
- **Model drift inside long loops.** `fresh_context: true` inside a `loop:` is usually what you want — without it, the assistant accumulates context and reasoning quality degrades.
- **`bash:` nodes run in the worktree's cwd.** Assume a freshly checked-out state; don't depend on side effects from earlier bash nodes unless they're deterministic.
