---
title: Make Me a Hanzi metadata — what we ingest and what we leave on the floor
created: 2026-04-22
tags: [type/distilled, topic/chinese-font, topic/mmh, topic/data-sources]
source: external
source-url: https://github.com/skishore/makemeahanzi
status: draft
---

# Make Me a Hanzi metadata — what we ingest and what we leave on the floor

**Summary (one line).** MMH gives us two flat files (`dictionary.txt`, `graphics.txt`), and we currently consume strokes + medians but leave four richer fields unused: `matches`, `decomposition`, `radical`, `etymology`.

> WebFetch on the MMH GitHub README succeeded. Field names below are exact.

## Fields available in MMH

**`dictionary.txt` (per character)**

| Field | Consumed today? | Notes |
|---|---|---|
| `character` | yes | Unicode glyph |
| `definition` | no | English-language hint only |
| `pinyin` | no | Could feed the Dong-Chinese role tagging |
| `decomposition` | partial | We parse via `cjk-decomp` separately; MMH's field is an IDS string |
| `etymology` | no | Formation type: ideographic / pictographic / pictophonetic |
| `radical` | no | Primary Unicode radical |
| `matches` | **no** | **Mapping from strokes of this character to strokes of its components** — path down the decomposition tree per stroke |

**`graphics.txt` (per character)**

| Field | Consumed today? | Notes |
|---|---|---|
| `character` | yes | |
| `strokes` | yes | SVG path per stroke, in stroke order |
| `medians` | yes | Stroke medians in 1024×1024 space |

## Ideas we could borrow

1. **Use `matches` to auto-populate `source_stroke_indices` on every `GlyphNodePlan` leaf.** Plan 11 Task 2 adds the field but leaves it hand-authored in `extraction_plan.yaml`. `matches` is the exact mapping we would otherwise write by hand — a path down the decomposition tree per stroke. For the 4 seed characters this replaces ≈ 40 hand-authored integers. For bulk extraction (Plan 9.2) it is the difference between "feasible" and "needs 9K hours of human time". *Cost: one adapter function in `sources/makemeahanzi.py` (which exists but doesn't export this); one loader change in `prototypes/extraction_plan.py`. ~0.5 day after Plan 11 lands. Prerequisite: Plan 11 finished (it's editing `extraction_plan.py` right now).*
2. **Radical field as a sanity cross-check against our prototype-library IDs.** MMH's `radical` field gives the Kangxi radical for each character; any prototype in our library whose role is "radical of character X" should match. Good fit for a pre-commit test (ties into D24). *Cost: ~0.25 day; one test file.*
3. **Etymology as a role-tag hint.** Our `roles/` module hand-seeds Dong-Chinese tags (meaning / sound / iconic / distinguishing / unknown) for the 4 seed chars (D3). MMH's `etymology` field carries "pictophonetic" with sound+meaning hints embedded; parseable into Dong-Chinese tags for free on pictophonetic characters (most of the corpus). *Cost: ~0.5 day — parser + test; feeds bulk extraction.*
4. **`decomposition` field as a second parse source beside `cjk-decomp`.** We already chose `cjk-decomp` (D10), but cross-checking the two lists surfaces disagreements that are worth reviewing. *Cost: trivial — already ingesting both files; just add a comparator.*

## INCOMPATIBLE ideas (on record)

- None. MMH is geometric source data; there is nothing in it that reintroduces preset-style placement. Everything we borrow from MMH feeds the measured side of the skill's rule.

## What it would cost us to adopt bullet 1 (the `matches`-driven prefill)

- **File(s):** new `project/py/src/olik_font/sources/mmh_matches.py` (adapter) and a call from `prototypes/extraction_plan.py`'s loader. Both off-limits during Plan 11, but a starter can be written as `vault/` or `.agent/` scaffolding today.
- **Effort:** half a day of engineer time once Plan 11 lands.
- **Prerequisite:** Plan 11 Task 2 done so `source_stroke_indices` is a real field on `GlyphNodePlan`.

## See also

- [[2026-04-22-borrow-mmh-matches-prefill]] — action doc for the borrow we start adopting now.
- `vault/plans/2026-04-22-11-virtual-coordinates-only.md` — Plan 11 adds `source_stroke_indices` to `GlyphNodePlan`; this borrow fills that field automatically.
- `project/py/src/olik_font/sources/makemeahanzi.py` — current MMH adapter (do not edit during Plan 11).
- `vault/references/discussion/discussion-0003.md` — original MMH reference in project history.
