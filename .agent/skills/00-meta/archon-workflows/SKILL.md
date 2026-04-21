---
name: archon-workflows
description: Use when the user wants to run deterministic, worktree-isolated AI coding workflows — plan → implement → validate → review → PR — in a repeatable way. Triggers on phrases like "use archon", "set up a workflow for X", "run this in parallel worktrees", "make this change deterministic", or when the user wants fire-and-forget multi-step AI coding automation. On this project, Archon is configured to use Codex SDK ONLY as its AI-node backend (no Claude Code SDK). Non-Codex assistants (Pi CLI, Kimi CLI, Copilot, Gemma4) are invoked from `bash:` nodes instead. Provider / model choice lives in @coding-providers.
category: 00-meta
layer: governance
related_skills:
  - "@coding-providers"
  - "@vault-obsidian"
---

# Archon Workflows

Archon ([github.com/coleam00/Archon](https://github.com/coleam00/Archon)) is a workflow engine that encodes your development process as YAML: plan → implement → validate → review → PR. Each run goes into its own git worktree, so multiple workflows run in parallel without conflicts. Think "GitHub Actions for AI coding", not "LiteLLM".

This skill reflects Archon 0.3.6 behavior as validated on this project on 2026-04-21 (Plan 02 end-to-end + Kimi-scaffold smoke). Earlier versions of this document described a YAML-centric config and a `.worktrees/` repo-root layout; both turned out to be **wrong** for 0.3.x. What's below is what actually works.

## Architecture in one diagram

```
Platform Adapters (CLI, Web UI, Slack, Telegram, Discord, GitHub)
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
          SQLite (default) / PostgreSQL (this project)
  Codebases • Conversations • Sessions • Workflow Runs
   Isolation Environments • Messages • Workflow Events
```

Two hard project rules:

- **Codex SDK is the only active AI-node backend.** Archon upstream ships Claude Code SDK as an option; we do not use it. All `prompt:` nodes and `loop:` AI nodes route to Codex, which in turn dispatches to OpenAI or any OpenAI-compatible provider via `@coding-providers`.
- **Non-Codex assistants run in `bash:` nodes.** Pi, Kimi, Copilot, Gemma4 have their own terminal CLIs. Archon's AI-node slot cannot drive them. Use `bash:` and invoke their non-interactive modes (flags below).

## When this skill applies

- Deterministic AI coding flow — same phases every time, validation gates, no model-of-the-day drift.
- Parallel fire-and-forget runs — "kick off three features, come back to three PRs".
- Encoding a team process (planning template, validation gates, PR format) as executable YAML.
- Worktree-isolated runs — current working tree shouldn't change mid-task.

## When it doesn't

- Multi-provider routing questions — that's `@coding-providers`, not this skill.
- One-off exploratory coding — the YAML overhead isn't worth it.
- Research / Q&A — workflows produce diffs and PRs, not answers.
- Prototyping the workflow itself — iterate in plain Claude Code first, then formalize.

---

## One-time setup (validated path, 2026-04-21)

### Prerequisites

```bash
bun --version       # >= 1.3
gh --version        # >= 2.80
codex --version     # ChatGPT OAuth — run `codex login` once
psql --version      # >= 16 — Homebrew install recommended
brew list archon    # Archon CLI; installed via: brew install coleam00/archon/archon
```

If `archon` is missing:

```bash
brew install coleam00/archon/archon
# OR the clone path:
git clone https://github.com/coleam00/Archon ~/src/Archon
cd ~/src/Archon && bun install
```

### PostgreSQL database (**required on this project**)

SQLite is Archon's default and works for single-user toy runs. On this project we use Postgres for:
- concurrent worktree runs (SQLite serializes under contention)
- clean backup/restore
- room to grow to a shared Archon instance later

```bash
brew install postgresql@16
brew services start postgresql@16

# Once-off: create the archon role + database
psql -h localhost -U "$USER" -d postgres <<'SQL'
CREATE ROLE archon LOGIN PASSWORD '<generated-password>';
CREATE DATABASE archon OWNER archon;
GRANT ALL PRIVILEGES ON DATABASE archon TO archon;
SQL

# Verify the role can log in
PGPASSWORD='<generated-password>' psql -h localhost -U archon -d archon -c '\conninfo'
```

Password goes into `infra/.env` as `DATABASE_URL` (see below). Keep a second copy locked somewhere; Archon reads it from the live env every run.

### Apply the schema migration

**Archon 0.3.x does NOT auto-migrate on first connect.** First attempt to run a workflow against a fresh Postgres database fails with `relation "remote_agent_isolation_environments" does not exist`. Apply the combined migration once:

```bash
curl -fsSL \
  https://raw.githubusercontent.com/coleam00/Archon/dev/migrations/000_combined.sql \
  -o /tmp/archon-000_combined.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 < /tmp/archon-000_combined.sql
```

Creates 8 tables: `remote_agent_codebases`, `_conversations`, `_sessions`, `_messages`, `_workflow_runs`, `_workflow_events`, `_isolation_environments`, `_codebase_env_vars`. When Archon bumps its schema version in a future release, re-apply the current combined file (it's idempotent) or run the new incremental migrations 0NN_*.sql.

### Environment variables

Archon 0.3.x reads most config from **environment variables**, not `~/.archon/config.yaml`. This caught us earlier — the YAML `database.url` field I once documented is not honored. Put these in `infra/.env` (gitignored) and source before running Archon:

```bash
# infra/.env — relevant entries
DATABASE_URL=postgresql://archon:<pw>@localhost:5432/archon
ARCHON_DATABASE_URL=$DATABASE_URL              # alias for non-Archon tools
DEFAULT_AI_ASSISTANT=codex                     # disables Claude default
CODEX_BIN_PATH=/opt/homebrew/bin/codex         # required for the compiled binary
```

Run pattern:

```bash
set -a; source infra/.env; set +a
env -u CLAUDECODE archon workflow list         # unset to suppress the nested-session warning
```

### `~/.archon/config.yaml` (minimal, local-only, not committed)

This file still matters for assistant defaults, streaming settings, and concurrency caps. It does **not** configure the database — that's env-var only.

```yaml
# ~/.archon/config.yaml — do not commit; credentials/machine-paths live here.

defaultAssistant: codex

assistants:
  codex:
    enabled: true
    codexBinaryPath: /opt/homebrew/bin/codex
    # Auth is Codex CLI OAuth (~/.codex/auth.json). No env-var tokens on this project.
    # model: gpt-5.4
    # modelReasoningEffort: medium
  claude:
    enabled: false
```

### Worktree locations (Archon decides, not you)

Archon 0.3.x puts worktrees under:

- `~/.archon/workspaces/<owner>/<repo>/source/` — the per-repo baseline checkout
- `~/.archon/worktrees/<parent-dir>/<repo>/archon/task-<slug>-<timestamp>/` — one per workflow run

There is no config key to redirect these to the repo's own `.worktrees/` directory — we tried. Our spec D20 originally claimed `.worktrees/` at repo root; that was aspirational. Reality: Archon's worktrees live in `~/.archon/`, distinct from any manually-created `.worktrees/` in the repo. Both valid; they just don't share a directory.

### Origin remote required

Archon attempts `git symbolic-ref refs/remotes/origin/HEAD` when creating a worktree. A local-only repo fails with "Cannot detect default branch". Create a GitHub remote (or equivalent) before the first workflow run:

```bash
gh repo create <org>/<repo> --private --source . --remote origin --push
# OR point at an existing repo:
git remote add origin https://github.com/<org>/<repo>.git
git push -u origin main
gh repo edit <org>/<repo> --default-branch main
```

Without this, every workflow halts at worktree creation.

---

## Workflow file layout

```
<project-root>/
└── .archon/
    └── workflows/
        ├── plan-02-python-core.yaml
        ├── kimi-scaffold-glyph-schema.yaml
        ├── codex-review-worktree.yaml
        └── copilot-pr-audit.yaml
```

Commit `.archon/workflows/*.yaml`. Gitignore `~/.archon/config.yaml` (machine-local, credentials). Runtime state: `.archon/state/` and `.archon/.log/` (if Archon writes there per-project) — also gitignore.

Validate a YAML before running it:

```bash
env -u CLAUDECODE archon validate workflows <workflow-name>
```

Catches the most common mistakes: missing `loop.max_iterations`, missing `loop.gate_message` on interactive loops, malformed `depends_on`.

## Workflow node types

| Node key | Purpose |
|---|---|
| `prompt:` | AI node — runs the assistant client with the given prompt (Codex SDK on this project) |
| `bash:` | Deterministic node — runs a shell command, no AI |
| `loop:` | Repeat until a condition, `APPROVED` from a human, or `max_iterations` cap |
| `depends_on:` | Sequence / parallelism control |
| `fresh_context: true` | Start the AI with empty context each iteration — prevents drift in long loops |
| `interactive: true` | Pause for human input — requires `gate_message` and `max_iterations`. **See hazards below.** |
| `idle_timeout: <ms>` | Kill a node after N ms of no progress |

Variable refs in `bash:` nodes: `$<nodeId>.output` contains the stdout of a prior node. Example: `echo "$run-tests.output" | grep "passed"`.

## Canonical workflow template (tested shape)

This template is the one we validated with Plan 02. It avoids the interactive-approve hazard (covered below) by auto-approving on test pass.

```yaml
name: plan-NN-<topic>
description: >-
  <One-line summary of what this workflow ships.>
provider: codex
model: gpt-5.4

# Archon auto-creates a worktree under ~/.archon/worktrees/... Don't set a
# custom path — there's no config key for it.

nodes:
  # ── 1. Environment setup ───────────────────────────────────────────
  - id: setup-venv
    bash: |
      set -e
      cd project/py
      if [ ! -x .venv/bin/pytest ]; then
        python3 -m venv .venv
        .venv/bin/pip install --upgrade pip
        .venv/bin/pip install -e ".[dev]"
      fi

  # ── 2. Warm any runtime caches (fetched from upstream) ─────────────
  - id: warm-caches
    depends_on: [setup-venv]
    bash: |
      set -e
      cd project/py
      .venv/bin/python -c "
      from pathlib import Path
      from olik_font.sources.makemeahanzi import fetch_mmh
      fetch_mmh(Path('data/mmh'))
      "

  # ── 3. The implementation loop ─────────────────────────────────────
  - id: implement
    depends_on: [warm-caches]
    loop:
      prompt: |
        You are Codex, implementing Plan NN task-by-task.
        The plan is at vault/plans/YYYY-MM-DD-NN-<topic>.md.

        Your single-iteration job:
        1. Read the plan.
        2. Check `git log --oneline -20` to see what's committed.
           Match commit messages to task-specific commit messages in the plan.
        3. Find the next unfinished task. If all tasks done, output the
           single word COMPLETE and stop.
        4. Implement every step exactly as written. TDD: fail-first,
           implement, pass.
        5. Run the commit command from the task.
        6. Output NEXT (continue loop) or COMPLETE (done) on the last line.
           Never invent a deviation; if blocked, output BLOCKED: <reason>.
      until: COMPLETE
      fresh_context: true
      max_iterations: 20
      idle_timeout: 1200000  # 20 min per iteration

  # ── 4. Regression tests ────────────────────────────────────────────
  - id: run-tests
    depends_on: [implement]
    bash: |
      set -e
      cd project/py && .venv/bin/pytest -v 2>&1 | tail -20

  # ── 5. Auto-approve on test pass (avoids interactive-gate hazard) ──
  - id: approve
    depends_on: [run-tests]
    bash: |
      set -e
      if echo "$run-tests.output" | grep -qE '[0-9]+ passed'; then
        echo "AUTO-APPROVED: tests green"
      else
        echo "REJECTED: tests did not pass cleanly"
        exit 1
      fi

  # ── 6. Open the PR ──────────────────────────────────────────────────
  - id: create-pr
    depends_on: [approve]
    prompt: |
      Push the current branch to origin and open a pull request against main.
      Use `gh pr create`.

      Title: "Plan NN: <topic>"
      Body: include commit list (git log main..HEAD), test count, and
      any Adjustments findings discovered during the run.

      Output the final PR URL on the last line.
    idle_timeout: 300000
```

Key differences from what was documented earlier:

- **No `interactive: true`** on `approve`. That was the zombie-state trigger (see below). Auto-approval on test pass is safer and loses nothing — post-PR review happens via a separate `codex-review-worktree` workflow.
- **`loop.max_iterations` is required.** Archon's YAML validator rejects loops without it.
- **`fresh_context: true`** inside the implement loop — Codex re-reads the plan each iteration; prevents drift across N tasks.

---

## Running workflows

From the project root, with env sourced:

```bash
set -a; source infra/.env; set +a
env -u CLAUDECODE archon workflow run <workflow-name>
```

To check status:

```bash
env -u CLAUDECODE archon workflow status
```

Lists active runs with run-id, path, status, age.

Abandon a stuck run:

```bash
env -u CLAUDECODE archon workflow abandon <run-id>
```

(See recovery playbook below.)

### Workflow CLI subcommands reference

```
archon workflow list                       # list available workflows
archon workflow run <name>                 # start a new run
archon workflow status                     # list active/paused runs
archon workflow approve <run-id> [msg]     # reply APPROVED to a paused interactive gate
archon workflow resume <run-id>            # resume a PAUSED or FAILED run (not "running")
archon workflow abandon <run-id>           # mark as abandoned (destructive; last resort)
archon workflow reject <run-id> [msg]      # reject at a gate
archon workflow cleanup [days]             # remove old completed workspace data
archon workflow event                      # append an event to a run
archon validate workflows [name]           # validate YAML
```

---

## Non-Codex CLIs in `bash:` nodes (flag reference)

These are the non-interactive incantations we tested. Always capture stdout; never leave these as interactive TUI processes.

**Codex (non-interactive, also used for review outside the AI-node path)**:

```bash
codex exec --skip-git-repo-check --full-auto "$(cat <<'PROMPT'
<your prompt>
PROMPT
)"
```

The native Codex AI-node path (no `exec`) only fires when `provider: codex` and the node is `prompt:` or `loop:`. For a `bash:` node that wants Codex, use `codex exec`.

**Copilot**:

```bash
copilot --allow-all-tools -p "<your prompt>"
```

`--allow-all` is equivalent to `--allow-all-tools --allow-all-paths --allow-all-urls`. Non-interactive mode requires at minimum `--allow-all-tools` or it prompts for every shell call. OAuth auth is honored automatically.

**Kimi**:

```bash
kimi \
  --work-dir <dir> \
  --add-dir <another-dir> \
  --print \
  --yolo \
  --final-message-only \
  -p "<your prompt>"

# OR the shorthand:
kimi --quiet -p "<your prompt>"
```

`--print` triggers non-interactive + `--yolo` (auto-approves actions). `--final-message-only` prints just the answer. `--quiet` is an alias for the whole trio.

Kimi validated successfully on Plan 04 Task 1 (scaffolding a pnpm package from a plan spec). ~1m26s for a 4-file + git commit scope.

**Pi**:

```bash
pi --model <provider-id/model-id> -p "<your prompt>"
```

But Pi is currently rate-limited on ZAI's coding plan (5-hour window). Check status before relying on it.

---

## ⚠ Known hazards — **READ BEFORE RUNNING `archon workflow approve`**

### The zombie "running" state

**What happens**: Archon's `approve` command transitions the run's DB row from "paused" → "running" before it does any actual work. If the command dies mid-transition (SIGPIPE, SIGINT, crash), the DB stays in "running" with nothing attached. Subsequent `approve` and `resume` refuse: *"Cannot approve run with status 'running'."*

**Common triggers**:

- Piping through line-limited filters: `archon workflow approve ... | head -30`. After 30 lines, `head` closes stdin; kernel sends SIGPIPE to archon; archon dies mid-transition. **This is the one I hit.**
- Ctrl-C partway through approve.
- Backgrounded shell that closes while archon is running.
- Any crash / OOM during the brief transition window.

Archon 0.3.x has no transactional rollback for approve — the DB state isn't tied to process liveness. This is a design fragility in the CLI, not a misconfig.

### Operational rule (compensating)

When running state-mutating Archon commands (approve, resume, continue):

- **Always** use `run_in_background: true` (or a shell `&`) and `tee` to a log file. Read the log file afterward. Never truncate the stdout of a mutating command.

  ```bash
  env -u CLAUDECODE archon workflow approve <run-id> "APPROVED" 2>&1 | tee /tmp/archon-approve.log &
  # OR if using Claude Code harness:
  # Bash tool with run_in_background: true
  ```

- Poll `archon workflow status` until the run exits the list (terminal state) before reading the log.
- **NEVER** `archon workflow approve <id> | head -N` or `| tail -N` or `| grep -m1`. If you need the first N lines, `tee` to file, then `head -N <file>`.

### Design rule (permanent)

Don't use `interactive: true` on `approve` nodes in pass-1 workflows. Replace with a bash auto-approve conditional on `run-tests` passing (see the template above). The gate adds:

- Zombie-state risk
- CLI ergonomics friction (find run-id, run separate approve command)
- No additional safety (tests already catch correctness; post-PR review catches judgment)

Reserve `interactive: true` for workflows where a human really must type something — e.g., creative direction, not correctness gates.

### Recovery playbook — when a run is zombie

```bash
# 1. Unstick the DB row (destructive: the run becomes non-resumable)
env -u CLAUDECODE archon workflow abandon <run-id>

# 2. If the worktree has real work, push it manually
cd ~/.archon/worktrees/<parent-dir>/<repo>/archon/task-<slug>-<timestamp>
git push -u origin <branch-name>
git push origin <any-tag>

# 3. Open the PR by hand
gh pr create --title "Plan NN: <topic>" --body "<summary>"

# 4. Move on. The abandoned run stays in PostgreSQL as a record.
#    Use `archon isolation cleanup --merged` to clean up stale worktrees later.
```

Time cost: ~30s. Much cheaper than trying to coax Archon back to paused state.

### Other gotchas (less common, worth knowing)

- **`CLAUDECODE=1` env var.** When Archon is launched from inside a Claude Code shell, it warns and can hang silently on interactive nodes. Always unset: `env -u CLAUDECODE archon ...`. Suppress the warning entirely with `ARCHON_SUPPRESS_NESTED_CLAUDE_WARNING=1`.

- **Global default assistant seeps into logs**. You may see `assistant_default_claude` in early startup logs even when your YAML declares `provider: codex`. That's a pre-config log line; what matters is `workflow_provider_resolved` which shows the real final provider. If it says `codex (source: workflow definition)`, you're good.

- **Loops can't honor top-level `model:`**. Validator warns `loop_node_ai_fields_ignored fields=["model"]`. Loop bodies use Codex's default model (gpt-5.x). Benign — all our loops work fine without per-loop overrides.

- **Draft 2020-12 JSON Schema crashes quicktype.** Unrelated to Archon but comes up in the same codegen plumbing. Use Draft 07 for any schema you'll feed through quicktype.

- **Stale worktrees accumulate.** Failed / abandoned runs leave `~/.archon/worktrees/*/archon/task-*` directories behind. `archon isolation list` shows them. `archon isolation cleanup --merged` removes ones whose branches merged into main. Schedule this occasionally.

- **`bash:` node variable syntax is `$nodeId.output`.** Dot-prefix of the prior node's id. For nodes with hyphens in the id, the shell interpolation still works in zsh/bash — tested with `$run-tests.output`.

---

## Archon's own skill vs. this skill

Archon installs its own skill into host assistants that support skills. That one knows how to invoke workflows from a prompt. **This skill is higher-level**: it explains *when* to reach for Archon at all, our project-specific constraints (Codex SDK only, Postgres required, no interactive approve), and how Archon fits with `@coding-providers` and `@vault-obsidian`.

If the two disagree on a command, trust the Archon-installed one — it tracks the exact installed version. If they disagree on **assistant choice** (installed one says "use Claude"), trust this one — the project-level rule wins.

## When to write a new workflow vs. a one-shot

Write `.archon/workflows/*.yaml` when:

- You've done the same multi-step task 3+ times.
- The team wants the same validation gates every time (e.g., always run ruff + biome + pytest before PR).
- Steps must be parallelizable (run 5 of these concurrently).
- You need audit trail — Archon persists every node's output in Postgres.

Stay one-shot (plain `claude` or `codex exec`) when:

- You're still figuring out the right steps.
- The task is unique — no future repeats likely.
- You need flexibility mid-task in a way YAML can't express.

## Relation to other skills

- **`@coding-providers`** — pick which model/provider runs inside Archon's AI nodes. Archon orchestrates; `@coding-providers` routes.
- **`@vault-obsidian`** — archive the PR plan / review notes into the vault when a workflow produces a design artifact worth keeping long-term.
- **`@ref-projects`** — if a workflow needs to read upstream source, it reads from `ref-projects/` **at planning time only**. Runtime workflows MUST NOT reach into `ref-projects/` — it's gitignored and doesn't exist in Archon's worktrees. Fetch from upstream over HTTPS (`requests.get(raw.githubusercontent.com/...)`) or commit a data snapshot into the repo instead. See Plan 01 Phase-1-finalization for a worked example.
