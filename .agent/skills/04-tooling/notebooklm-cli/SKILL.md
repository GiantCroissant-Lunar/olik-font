---
name: notebooklm-cli
description: Use when the user wants to drive Google NotebookLM from the terminal — creating/listing notebooks, adding URLs/files/Drive docs as sources, querying a notebook, or managing logins. Triggers on any mention of "nlm", "NotebookLM", "notebooklm-mcp-cli", or tasks like "pull these references into NotebookLM", "organize notes into NotebookLM", "log back into NotebookLM". This skill covers installation, frequent re-login (sessions expire often), profile management, and free-tier-aware usage patterns. CLI only — do NOT use for setting up the MCP server inside agents.
category: 04-tooling
layer: tooling
related_skills:
  - "@vault-obsidian"
---

# NotebookLM CLI (`nlm`)

Programmatic access to Google NotebookLM via the `nlm` CLI from the `notebooklm-mcp-cli` PyPI package. Use for note organization: pulling external references into a notebook, letting NotebookLM index them, and querying/summarizing the corpus.

## When this skill applies

- User asks to add URLs/files/Drive docs to a NotebookLM notebook.
- User asks to query or summarize an existing NotebookLM notebook from the terminal.
- User says they've been "logged out of NotebookLM again" or asks how to re-authenticate.
- User wants to script or batch-organize notes into NotebookLM.

## When this skill does NOT apply

- Setting up the `notebooklm-mcp` server for another AI tool — that's a separate flow (`nlm setup add <tool>`).
- Anything involving the paid/Enterprise tier's advanced features — free-tier limits apply here.
- Pure Obsidian vault organization — see the `vault-obsidian` skill instead.

## Install and verify

The CLI isn't always installed. Check first, install only if missing.

```bash
# Check
which nlm && nlm --version

# Install (preferred — uv tool isolates it)
uv tool install notebooklm-mcp-cli

# Upgrade later
uv tool upgrade notebooklm-mcp-cli
```

If `uv` is not available, fall back to `pipx install notebooklm-mcp-cli` or `pip install --user notebooklm-mcp-cli`. Do not install globally with `sudo pip`.

After install, both `nlm` and `notebooklm-mcp` binaries are available. This skill only uses `nlm`.

## Login — expect to do this often

The tool uses internal Google APIs and extracts session cookies from a real browser. Cookies expire frequently (days, sometimes hours), so re-login is a normal part of using `nlm`. Don't treat a login failure as broken — just re-run `nlm login`.

```bash
# Check current auth status before any real command
nlm login --check

# Normal login — opens a browser, user signs in, cookies are captured
nlm login

# Named profile (use this when the user has multiple Google accounts)
nlm login --profile work
nlm login --profile personal

# Manual cookie import (for headless environments)
nlm login --manual --file cookies.txt
```

Profile management:

```bash
nlm login profile list            # show all profiles + emails
nlm login switch <profile>        # set default profile
nlm login profile rename <old> <new>
nlm login profile delete <profile>
```

**Before any non-trivial command, run `nlm login --check` first.** If it reports not-logged-in, stop and tell the user — don't try to force a browser login silently during an agent turn.

## Free-tier discipline

The free tier has tight limits on source count per notebook, audio/video generation quotas, and query volume. Use the CLI mostly for **organization**, not heavy generation:

- Prefer `notebook list`, `notebook create`, `source add`, `notebook query`.
- Avoid `audio create`, `studio create`, `research start` in loops or batch scripts unless the user explicitly asks for one.
- When adding many sources, batch them in a single `nlm batch` call rather than many individual `source add` calls — same quota, fewer round-trips.
- If a command fails with a quota/429-style error, stop and report; don't retry automatically.

## Core commands

```bash
# Notebooks
nlm notebook list
nlm notebook create "Title of Notebook"
nlm notebook query <notebook-id-or-name> "your question"
nlm notebook delete <notebook-id>

# Sources (URL, text, Drive doc, local file)
nlm source add <notebook> --url "https://..."
nlm source add <notebook> --file path/to/file.pdf
nlm source add <notebook> --text "pasted content"
nlm source add <notebook> --drive <drive-doc-id>
nlm source list <notebook>
nlm source sync <notebook>          # re-index Drive sources

# Download generated artifacts (audio, slides, etc.)
nlm download <type> <notebook> <artifact-id>

# Batch + pipelines
nlm batch query  --file queries.yaml
nlm batch create --file notebooks.yaml
nlm pipeline run <pipeline.yaml>

# Sharing
nlm share public <notebook>         # enable public link
nlm share invite  <notebook> <email>

# Diagnose
nlm doctor
nlm --ai                            # prints the full AI-assistant help
```

Run `nlm --ai` once per session if you need a fuller command reference — it dumps comprehensive docs designed for agent consumption.

## Notebook identification

`nlm` accepts both notebook IDs and titles. Prefer IDs in scripts (stable) and titles in interactive commands (readable). When a title is ambiguous across notebooks, the CLI errors out — resolve by listing and picking the ID.

## Suggested workflow: intake external references

A common use in this project is turning a pile of links into a NotebookLM notebook you can query.

1. `nlm login --check` — confirm auth.
2. `nlm notebook list` — reuse an existing notebook if one matches the topic.
3. `nlm notebook create "Topic"` — or create a new one; record the returned ID.
4. `nlm source add <id> --url "..."` for each URL (or `nlm batch create` with a YAML file of sources).
5. `nlm source list <id>` — verify everything landed.
6. `nlm notebook query <id> "summarize the key claims across these sources"` — sanity check the index.

Echo the notebook ID back to the user so they can open it in the NotebookLM web UI.

## Cross-tool notes

This skill targets the shell, not a specific agent harness. It should work identically whether invoked from Claude Code, Copilot CLI, or Codex. All commands go through `nlm` in a normal shell — no platform-specific tool APIs needed.

## Troubleshooting

- **"Not authenticated" / 401 / 403** — run `nlm login` again. Don't guess at cookie fixes.
- **"Unknown notebook"** — run `nlm notebook list` and use the exact title or ID.
- **Quota-like errors** — stop, report to the user. Free tier is easy to hit.
- **Weird internal API errors** — `nlm doctor` dumps environment info and known-issue checks.
- **After `uv tool upgrade`** — restart any agent tool that embeds the MCP server; the CLI itself just works.
