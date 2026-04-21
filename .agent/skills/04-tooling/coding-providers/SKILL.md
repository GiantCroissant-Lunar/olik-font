---
name: coding-providers
description: Use whenever the user wants to route an AI coding task through a specific provider on this project. Each CLI has ONE job — Pi (`@mariozechner/pi-coding-agent`) is scoped to ZAI / GLM only, Codex CLI is OpenAI + Archon's SDK backend, Kimi CLI is Moonshot, Copilot CLI is GitHub, Ollama cloud is Gemma 4. Triggers on phrases like "use GLM for this", "try with Kimi", "route through Codex", "let Copilot draft it", or any setup question about API keys, CLI config, or picking the right model. Also feeds into @archon-workflows — AI nodes go through Codex SDK, other CLIs via bash nodes. Explicitly does NOT cover Claude Code SDK (not used on this project).
category: 04-tooling
layer: tooling
related_skills:
  - "@archon-workflows"
  - "@youtube-gemma"
---

# Coding Providers

The user has paid / plan access to several provider ecosystems. This skill is the single place that documents which CLI/SDK to reach for, how to configure it, and how each one plugs into `@archon-workflows`.

**Scope rule for this project:** we use Codex CLI, Pi (scoped to ZAI/GLM), Kimi CLI, Copilot CLI/SDK, and Ollama (cloud Gemma 4 primarily). **One CLI, one job** — we don't use Pi's subscription flows or its other API-key providers here, even though upstream supports them. **We do NOT use Claude Code SDK as an Archon AI-node backend.**

## Client ↔ provider map — one CLI, one job

| Client (what you run)     | Reaches (on this project)                 | Role                                |
|---------------------------|-------------------------------------------|-------------------------------------|
| **Pi** (`@mariozechner/pi-coding-agent`) | ZAI only (`glm-4.6`, `glm-5.x`, `glm-turbo`) | GLM-specific coding sessions       |
| **Codex CLI**             | OpenAI                                    | OpenAI-native use **and** `@archon-workflows`'s SDK backend |
| **Kimi CLI** (MoonshotAI)  | Moonshot Kimi family                      | Moonshot-native long-context work  |
| **Copilot CLI**           | GitHub-hosted models                      | Optional — GitHub-native shell helpers |
| **Ollama** (cloud-routed)  | Gemma 4 (`:31b`, routed to cloud when signed in) | `@youtube-gemma` + bash-node use |

Rule of thumb:

- **Need GLM?** Pi. Don't use Pi for anything else on this project.
- **Need OpenAI or running an Archon workflow?** Codex CLI.
- **Need Moonshot / long context?** Kimi CLI.
- **Need Gemma 4 / YouTube intake?** Ollama + `@youtube-gemma`.
- **Need GitHub-native shell help?** Optional Copilot CLI.

Pi upstream supports a lot more (Anthropic, Groq, OpenRouter, Bedrock, subscriptions for Claude Pro / ChatGPT / Copilot / Gemini) — but on this project we explicitly don't use those flows through Pi. Keeping each CLI scoped to one provider keeps the mental model simple and failure modes obvious.

## Pi (ZAI / GLM only)

[github.com/badlogic/pi-mono](https://github.com/badlogic/pi-mono) → `@mariozechner/pi-coding-agent`. Pi upstream is a multi-provider coding harness, but on this project **we scope it to ZAI only**. Other providers have their own CLIs.

```bash
npm install -g @mariozechner/pi-coding-agent
```

Auth — only the ZAI API-key path on this project:

```bash
export ZAI_API_KEY="<your key>"
pi
```

Inside pi:

```
/model                 # pick a GLM model — glm-4.6, glm-5.x, glm-turbo
```

Modes used:

- **Interactive** — `pi` (default REPL for GLM sessions).
- **Print** — `pi -p "…"` for one-shot piping into `bash:` nodes from `@archon-workflows`.

Example bash-node use (from an Archon workflow):

```bash
git diff HEAD~1 | pi --model "zai/glm-4.6" -p "Review this diff. List issues as bullets."
```

**Do not** use Pi's `/login` subscription flows on this project. Claude Pro / ChatGPT (Codex) / Copilot / Gemini subscriptions are handled by their own native CLIs (or skipped). This is a deliberate scope choice — one CLI, one provider, one job.

**Doesn't cover Moonshot Kimi** — that's Kimi CLI below.

## Kimi CLI (Moonshot)

Moonshot's official agentic terminal tool — [github.com/MoonshotAI/kimi-cli](https://github.com/MoonshotAI/kimi-cli).

```bash
# One-liner installer (installs uv if missing, then kimi-cli)
curl -LsSf https://code.kimi.com/install.sh | bash

# Or, if uv is already present
uv tool install --python 3.13 kimi-cli

# Windows
# Invoke-RestMethod https://code.kimi.com/install.ps1 | Invoke-Expression
```

First-run auth:

```bash
kimi
> /login               # pick "Kimi Code" — opens browser for OAuth
```

Features worth knowing:

- `Ctrl-X` toggles shell command mode inside the REPL.
- `kimi acp` runs Kimi as an Agent Client Protocol server — usable from Zed / JetBrains agent panels.
- VS Code extension: "Kimi Code" on the marketplace.
- MCP support via `kimi mcp add/list/remove/auth` — same MCP ecosystem you use elsewhere.
- Zsh integration via `MoonshotAI/zsh-kimi-cli` plugin (Ctrl-X switches to agent mode in your regular shell).

One-shot use:

```bash
git diff HEAD~1 | kimi -p "Review this diff for correctness."
```

## Codex CLI

Primary reason to have Codex CLI installed: **`@archon-workflows` dispatches its AI nodes through Codex SDK**. Even if you rarely invoke `codex` interactively, Archon needs the binary and auth present.

```bash
# Install — exact command varies by OpenAI release. Check their install docs.
# Typical paths:
npm install -g @openai/codex
# or
brew install codex-cli
```

Auth — **OAuth only on this project**:

```bash
codex login                             # interactive OAuth (ChatGPT or OpenAI API auth)
codex login status                      # safe read-only check
```

Codex CLI *also* accepts `OPENAI_API_KEY` / `--with-api-key`, but **don't use those here**. Project convention is OAuth-only — it avoids plaintext keys in env files and keeps auth rotation in one place (the ChatGPT subscription). On this project, Codex CLI is OpenAI-only and doubles as Archon's SDK backend. Don't route ZAI/GLM through Codex — that's Pi's job.

Features:

- `Ctrl-X` toggles shell command mode inside the REPL.
- ACP (Agent Client Protocol) → works as backend for VS Code / IDEs that speak ACP.
- MCP server support → same MCP servers you use elsewhere generally work here.
- Long context makes it a strong choice for whole-file review or multi-file reasoning.

One-shot use:

```bash
git diff HEAD~1 | kimi -p "Review this diff for correctness."
```

## Copilot CLI (optional)

Standalone Copilot CLI is **optional** on this project. Install only if you specifically want GitHub-native shell helpers (`copilot suggest "..."`) or Copilot access wired into scripts via env-var auth. Don't route Copilot through Pi here — we're keeping Pi scoped to ZAI.

```bash
npm install -g @github/copilot         # recommended
# or
brew install copilot-cli
# or
curl -fsSL https://gh.io/copilot-install | bash
```

Auth — **OAuth only on this project**:

```bash
copilot
> /login                                # interactive GitHub auth
```

Copilot CLI *also* accepts `COPILOT_GITHUB_TOKEN` (or `GH_TOKEN` / `GITHUB_TOKEN`) for non-interactive use, but **don't use that here**. Project convention is OAuth-only. Skip this CLI entirely unless you specifically need GitHub-native shell helpers.

## Ollama (cloud Gemma 4)

Used for tasks best handled by Gemma 4 — primarily YouTube analysis (see `@youtube-gemma`) and long-context review.

```bash
# Setup
brew install ollama                     # or download from ollama.com
ollama serve &
ollama signin                            # one-time — enables cloud inference
# NO `ollama pull gemma4:31b`. The 31b tag is too large to run locally and
# the pull would fail / thrash. When signed in, Ollama routes the request
# to cloud inference transparently — same model name, different path.
```

**Cloud routing is the only viable path for 31b.** Smaller Gemma 4 tags (`:e2b`, `:e4b`, `:26b`) can run locally but the user has judged them too weak for real work on this project, so we don't default to them.

OpenAI-compatible bridge (so Codex CLI / any OpenAI SDK can talk to it):

- Base URL: `http://localhost:11434/v1`
- Auth: any non-empty string (Ollama ignores the value)

## Credential hygiene

`infra/.env` (gitignored) holds the keys that actually need env entries on this project:

```bash
# infra/.env — the full template is in the file itself, abbreviated here
ZAI_API_KEY=...                     # Pi reads this natively
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4/
OLLAMA_API_KEY=...                  # Ollama cloud routing
OLLAMA_BASE_URL=http://localhost:11434/v1
KIMI_API_KEY=...                    # OPTIONAL — SDK/curl use only, Kimi CLI is OAuth
```

**Intentionally not in `.env` on this project:**

- `OPENAI_API_KEY` — Codex CLI is OAuth-only here.
- `COPILOT_GITHUB_TOKEN` — Copilot CLI is OAuth-only here.
- `ANTHROPIC_API_KEY` — Anthropic Claude isn't used as a coding provider on this project.

Even though these CLIs support env-var auth, the project convention is to go through OAuth for anything that supports it. Rationale: one rotation surface (the subscription), no plaintext keys sitting in env files.

Don't:

- Commit `.env`, `~/.archon/config.yaml`, `~/.codex/config.toml`.
- Put keys in `.archon/workflows/*.yaml` (those are committed).
- Echo keys into logs, PR descriptions, or agent responses.

Per-developer defaults (e.g. "I prefer glm-4.6 for review tasks") belong in `AGENTS.md` (gitignored).

## Plugging into `@archon-workflows`

Archon's AI nodes dispatch **only via Codex SDK** on this project. That means:

- **OpenAI (via Codex SDK)** → primary path for AI nodes. Configured once in `~/.archon/config.yaml`.
- **Pi / Kimi CLI / Copilot CLI / Ollama** → invoke from `bash:` nodes. Pi is particularly useful here because one `bash:` node can hit ZAI/Groq/OpenRouter/etc. depending on `--model`.

Example bash-node patterns:

```yaml
  - id: glm-review
    bash: |
      git diff HEAD~1 | pi --model "zai/glm-4.6" -p "Review for correctness."

  - id: kimi-longcontext
    bash: |
      cat path/to/big-file.ts | kimi -p "Point out any architectural issues."

  - id: gemma-analysis
    bash: |
      cat transcript.txt | ollama run gemma4:31b
```

Why this split: the SDK adapter gives Archon full control (streaming, tool-use, context management) — that's what you want for the main plan/implement/review loop. Bash nodes are simpler but the CLI's UX is fixed — perfect for "get a second opinion with a different model's strength".

## On LiteLLM and Mastra (deliberately not used)

LiteLLM (local OpenAI-compatible proxy) and Mastra (TypeScript agent framework) are both legitimate ways to unify multi-provider LLM access. **We are not using either on this project**, for one reason: Pi already covers the day-to-day multi-provider need (ZAI + Anthropic + OpenAI + Google + Groq + OpenRouter + Bedrock + subscriptions all in one CLI), and Codex SDK is sufficient as Archon's AI-node backend.

Adding LiteLLM would mean:

- Running a local proxy on port 4000 alongside everything else.
- A second place where provider configs live (now it's: `.env`, `~/.codex/config.toml`, `~/.archon/config.yaml`, **plus** `~/.litellm/config.yaml`).
- One more moving part to debug when a workflow fails.

Adding Mastra would mean:

- Re-implementing our agent workflows in its framework.
- Learning another abstraction on top of the assistant CLIs.

**Reach for either only if:**

- You need cost-based routing or automatic fallback between providers mid-conversation (LiteLLM's strength).
- You're building a product with custom agent topology that neither Pi nor Archon expresses well (Mastra's strength).

For the current scope — organize notes, iterate on designs, run Archon workflows against Codex — Pi + Codex + Archon is enough. Revisit this decision if the project outgrows them.

## Model selection heuristics

| Task | Good choice |
|---|---|
| Structured plan → implement → validate (Archon AI nodes) | Codex SDK → OpenAI |
| GLM iteration / second opinion / bulk chores | Pi with `glm-4.6` / `glm-5.x` / `glm-turbo` |
| Long diff / whole-file review | Kimi CLI (long-context strength) |
| GitHub-native chores (issue triage, shell one-liners) | Copilot CLI |
| YouTube intake, transcript analysis | Ollama `gemma4:31b` via `@youtube-gemma` |
| Offline / air-gapped | Local Ollama tag (exception to the cloud-first rule) |

These are starting points — defer to `AGENTS.md` if the user has recorded measured preferences.

## Gotchas

- **"OpenAI-compatible" ≠ "identical."** Tool-calling JSON shape and streaming format diverge across providers. If tool-use breaks, strip tools and retry in plain chat to isolate the issue.
- **Rate limits per plan.** Z.ai coding plan and Moonshot coding plan have different per-minute / per-day caps than OpenAI. Hitting a limit mid-Archon run is a common failure — mark non-critical nodes `continue_on_error: true` if appropriate.
- **Model name drift.** `glm-4.6`, `glm-5.1`, `glm-5-turbo`, `kimi-k2.6` etc. shift as providers release new versions. Query the provider's model list endpoint when a 404 shows up:
  ```bash
  curl -H "Authorization: Bearer $ZAI_API_KEY" https://api.z.ai/api/paas/v4/models
  ```
- **Copilot CLI scope.** Tokens with `Copilot Requests` permission cost credits against your GitHub Copilot subscription — don't embed in shared CI without understanding the usage impact.
- **Ollama cloud auth survives reboot** via `~/.ollama/auth`. If the daemon loses auth mid-session, re-run `ollama signin`.
- **Don't leak between providers.** If you pipe Kimi's output into Codex's prompt, sanitize — different providers have different prompt-injection resistance and bake different system instructions into replies.
