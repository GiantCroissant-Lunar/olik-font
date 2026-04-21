---
name: youtube-gemma
description: Use when the user wants to extract, summarize, or analyze the content of a YouTube video LOCALLY using Gemma 4 via Ollama. Triggers on phrases like "check this YouTube reference", "summarize this video", "what does this YouTube clip say about X", or when the user drops a youtube.com / youtu.be URL and wants its content pulled into the vault. Pipeline is local-only: yt-dlp → whisper transcription → Gemma 4 analysis. Do NOT use this skill for live YouTube search or for videos the user wants to watch interactively — this is strictly for offline ingestion of a specific URL.
category: 04-tooling
layer: tooling
related_skills:
  - "@vault-obsidian"
  - "@notebooklm-cli"
---

# YouTube → Gemma 4 (local)

Download a YouTube video's audio locally, transcribe it, then hand the transcript to Gemma 4 via Ollama for summarization / analysis / fact extraction. Nothing hits a paid API — this is the local-first counterpart to `@notebooklm-cli` for when you want privacy or are offline.

## When this skill applies

- User pastes a specific YouTube URL and asks to summarize, outline, or extract claims from it.
- User wants video content filed into the vault as a reference note.
- User wants to cross-check something a video says ("does this video actually claim X?").
- User explicitly wants local processing ("don't send this to NotebookLM").

## When it doesn't

- Live / streaming videos — transcription will fail or be incomplete.
- Videos in a language Gemma 4 doesn't handle well — verify first (Gemma 4 is strong at English and major world languages but check before committing).
- Pure search ("find videos about X") — this skill only processes URLs the user provides.
- Copyrighted content the user has no right to archive.

## One-time setup

Three pieces: Ollama + Gemma 4 model, yt-dlp, a whisper implementation.

```bash
# 1. Ollama + Gemma 4 (cloud is the only viable path — 31b doesn't fit locally)
# Install Ollama: https://ollama.com/download (Mac: brew install ollama)
ollama serve &                       # run the daemon (or use the menu-bar app)
ollama signin                        # one-time — enables cloud inference
# DO NOT `ollama pull gemma4:31b`. The 31b tag is too large to run on a normal
# machine; pulling it would fail or thrash. When signed in, Ollama routes the
# request to cloud inference transparently — same model name, different path.

# 2. yt-dlp (audio extraction)
brew install yt-dlp ffmpeg           # ffmpeg needed for audio extraction

# 3. A whisper implementation (transcription)
# Pick ONE of these — don't install multiple:
#   faster-whisper (recommended for CPU-only machines)
uv tool install faster-whisper
#   OR whisper.cpp via homebrew (fastest with Metal on Apple Silicon)
brew install whisper-cpp
#   OR openai-whisper (Python reference impl, slowest)
uv tool install openai-whisper

# Verify
which yt-dlp ffmpeg && ollama list | grep gemma4
```

Check `nlm`-style: run `ollama list` before each use to confirm the Gemma model is still available. Ollama doesn't auto-unload, but a cleanup can have pruned it.

## The pipeline

```
YouTube URL
   │
   ▼  yt-dlp -x --audio-format mp3
audio file (mp3)
   │
   ▼  whisper / faster-whisper / whisper.cpp
transcript (txt, with timestamps)
   │
   ▼  ollama run gemma4:31b  (piped prompt)
summary / outline / extracted claims
   │
   ▼
vault note under vault/references/youtube/
```

## Command recipe

```bash
# Pick a working directory under infra/ or /tmp — do NOT download into the repo
WORKDIR="/tmp/yt-$(date +%s)"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

# 1. Download audio only
yt-dlp -x --audio-format mp3 --output "audio.%(ext)s" "$YOUTUBE_URL"

# 2. Capture metadata (title, channel, upload date) — needed for the vault note
yt-dlp --skip-download --print "%(title)s|%(uploader)s|%(upload_date)s|%(duration_string)s|%(webpage_url)s" "$YOUTUBE_URL" > meta.txt

# 3. Transcribe (pick one matching your install)
# faster-whisper:
faster-whisper audio.mp3 --model medium --output_format txt --output_dir .
# whisper.cpp (Metal, Apple Silicon):
whisper-cpp -m /opt/homebrew/share/whisper-cpp/ggml-medium.bin -f audio.mp3 -otxt
# openai-whisper:
whisper audio.mp3 --model medium --output_format txt --output_dir .

# 4. Analyze with Gemma 4
TRANSCRIPT="$(cat audio.txt)"
PROMPT="Summarize this YouTube transcript in the structure: TL;DR (2 lines), key claims (bullet), notable timestamps if present, open questions. Transcript follows:\n\n$TRANSCRIPT"
echo "$PROMPT" | ollama run gemma4:31b > analysis.md
```

## Writing it into the vault

After analysis, file both the raw transcript and the Gemma analysis via the `@vault-obsidian` skill:

```
vault/references/youtube/
├── index.md                          # MOC — update with each new entry
├── <slug>-NNNN-transcript.md         # raw transcript + yt-dlp metadata (source: external)
└── <slug>-NNNN-analysis.md           # Gemma's output (source: self, distilled-from the transcript)
```

Use the same intake pattern as `@vault-obsidian` — preserve raw, distill separately, update MOC. See `references/intake-checklist.md` in the vault-obsidian skill for the full checklist.

Frontmatter for the transcript note:

```yaml
---
title: <video title>
created: YYYY-MM-DD
tags: [topic/..., type/youtube-transcript]
source: external
url: <YouTube URL>
channel: <uploader>
upload_date: YYYY-MM-DD
duration: "HH:MM:SS"
model_used: whisper-medium
---
```

Frontmatter for the analysis note:

```yaml
---
title: Analysis — <video title>
created: YYYY-MM-DD
tags: [topic/..., type/distilled]
source: self
distilled-from: "[[<slug>-NNNN-transcript]]"
model_used: gemma4:e4b
---
```

## Model selection

- **`gemma4:31b`** (default) — too large to run on a normal machine, so when you're signed in via `ollama signin` and haven't pulled it, Ollama routes to cloud inference. That cloud path is the only practical way to use this tag.
- **Smaller tags** (`gemma4:e2b`, `:e4b`, `:26b`) — will run locally, but the user has judged them too weak for real work on this project. Only reach for one if the user explicitly asks for a smaller / offline model.
- **Don't `ollama pull gemma4:31b`.** It would fail or thrash on local hardware. The only supported path for 31b is cloud routing.

If a transcript exceeds the model's context window, chunk it:

```bash
split -b 500000 audio.txt chunk_
for c in chunk_*; do
  echo "Summarize this chunk: $(cat $c)" | ollama run gemma4:31b >> chunks.md
done
# Then summarize the summaries
cat chunks.md | ollama run gemma4:31b > analysis.md
```

## Gotchas

- **Large videos take time.** Audio download + transcription for a 1-hour video is 2–10 min on Apple Silicon depending on model size. Gemma 4 analysis is fast after that.
- **Auto-generated captions (via `yt-dlp --write-auto-sub --skip-download`) are a shortcut** but lower quality than Whisper. Use them when you need speed and the audio is clean speech. Prefer Whisper for anything with background noise, accents, or technical vocabulary.
- **Gemma 4 can hallucinate timestamps** if the transcript doesn't have them. Use Whisper with `--output_format srt` if you need real timestamps back, then convert.
- **Don't download into the repo.** Use `/tmp/` or `~/Downloads/`. The audio + transcript are intermediate artifacts, not vault content.
- **Copyright.** If the user is pulling content they don't own, the raw transcript should be kept local and not committed — only the distilled analysis (which is transformative) goes into the vault.

## Relation to `@notebooklm-cli`

Both answer "turn a URL into something I can query". They differ on:

| | `@notebooklm-cli` | `@youtube-gemma` |
|---|---|---|
| Network | Google NotebookLM (online) | Fully local |
| Privacy | Content uploaded to Google | Nothing leaves the machine |
| Quality | Very strong (Gemini + RAG) | Decent (Gemma 4, single-shot) |
| Multi-source corpora | Yes | No (one video at a time) |
| Persistence | NotebookLM notebook | Vault note |
| Free-tier limits | Yes (strict) | None (local) |

Use `@notebooklm-cli` when you're curating a corpus you'll query over time. Use this skill when the video is one-shot, private, or offline.
