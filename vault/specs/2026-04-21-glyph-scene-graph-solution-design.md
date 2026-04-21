---
title: Glyph scene graph — pass-1 solution design
created: 2026-04-21
tags: [type/design, topic/chinese-font, topic/scene-graph, topic/spec]
source: self
distilled-from:
  - "[[glyph-scene-graph-spec]]"
  - "[[discussion-0003]]"
  - "[[discussion-0004]]"
status: draft
scope: pass-1 (end-to-end walkthrough of 明, 清, 國, 森)
---

# Glyph scene graph — pass-1 solution design

First concrete implementation plan for the glyph scene graph concept distilled in [[glyph-scene-graph-spec]]. Pass-1 goal: walk four characters (明, 清, 國, 森) end-to-end through decomposition → prototype extraction → constraint-driven reconstruction → validated JSON record → animated + inspectable presentation. The schema, module boundaries, and dev workflow are designed to absorb later work (HanziCraft productive-component data, HanziVG metadata, Dong-Chinese role colors, IF-Font / CCFont layout priors, DP-Font styling, qiji-font export, ComfyUI styling) without structural churn.

> Terminology in this doc follows [[glyph-scene-graph-spec]]. "Decision" bullets (D1, D2, …) are revisable design calls, collected in [§ Reviewable decisions](#reviewable-decisions) at the end for easy diffing.

## Seed character set

Four characters chosen to stress different parts of the schema without bloating scope:

| Char | Decomp | What it proves |
|---|---|---|
| 明 | `⿰(日, 月)` — left_right | Baseline. Simple left_right preset, two level-1 prototypes. |
| 清 | `⿰(氵, 青)` — left_right, with 青 refined to `⿱(生, 月)` | Prototype reuse: 月 shared with 明. Refinement mode: 青 expands one level deeper. |
| 國 | `⿴(囗, 或)` — enclose | Non-axis-aligned relation. Tests `inside` / `contain` constraints. |
| 森 | 木 × 3 (top, bottom-left, bottom-right) | Instance multiplicity: one prototype, three transforms. Direct-authored (no preset). Stroke-crossing z-depth matters. |

Prototype union across all 4 chars: `{日, 月, 氵, 青, 生, 囗, 或, 木}` = 8 prototypes covering ~42 stroke instances.

## Section 1 — Architecture & repo layout

Two coordinated sub-projects under `project/`, plus a shared language-agnostic schema. The JSON record is the **only** coupling between them.

```
project/
├── schema/                         # language-agnostic
│   ├── glyph-record.schema.json    # contract between py ↔ ts
│   └── examples/
│       ├── 明.json  清.json  國.json  森.json
│       └── prototype-library.json
├── py/                             # Python — data, decomposition, composition
│   ├── pyproject.toml
│   ├── src/olik_font/
│   │   ├── sources/                # adapters: makemeahanzi, cjk_decomp (impl); hanzicraft, hanzivg (stubs)
│   │   ├── prototypes/             # extraction + prototype-library DAG (shared graph)
│   │   ├── decompose/              # char → instance tree (multi-depth, cjk-decomp-driven)
│   │   ├── constraints/            # primitives (align_*, attach, inside, repeat, ...) + preset adapter
│   │   ├── compose/                # walk instance tree → resolve transforms → flatten strokes → IoU check
│   │   ├── rules/                  # engine + rules.yaml + decomp/compose/prototype rule modules
│   │   ├── roles/                  # Dong-Chinese role tags (schema slot, seed data for 4 chars)
│   │   └── cli.py                  # `olik build 明 清 國 森 -o ../schema/examples`
│   └── data/                       # fetched MMH graphics.txt / dictionary.txt, cjk-decomp.txt (gitignored)
└── ts/                             # pnpm workspace root
    ├── pnpm-workspace.yaml
    ├── package.json                # root: dev deps + shared scripts
    ├── .npmrc                      # engine-strict, frozen-lockfile
    ├── tsconfig.base.json
    ├── apps/
    │   ├── remotion-studio/        # @olik/remotion-studio — animated presentation
    │   └── inspector/              # @olik/inspector — xyflow-based interactive inspection
    └── packages/
        ├── glyph-schema/           # @olik/glyph-schema — TS types + zod validators (from schema/)
        ├── glyph-loader/           # @olik/glyph-loader — fs/URL load + validate
        ├── glyph-viz/              # @olik/glyph-viz — framework-neutral React/SVG primitives
        ├── flow-nodes/             # @olik/flow-nodes — xyflow custom node types
        └── rule-viz/               # @olik/rule-viz — rule-graph view primitives
```

Growth seams (named, not built in pass 1): `packages/glyph-styler/` (ComfyUI bridge), `packages/glyph-export/` (Potrace/FontForge), `packages/prototype-editor/` (authoring), `apps/docs/` or `apps/playground/` (web viewer).

Tooling defaults:
- pnpm workspace protocol (`workspace:*`) for internal deps
- TypeScript project references, `tsconfig.base.json` at root
- Single root `package.json` owns dev deps; apps/packages only declare runtime deps
- No turborepo/nx yet — pnpm's `--filter` + `-r` is enough for pass-1 package count

## Section 2 — Data flow & JSON schema

### Pipeline

```
MMH graphics.txt + dictionary.txt         sources/makemeahanzi
cjk-decomp.txt (HanziJS source)           sources/cjk_decomp
          │
          ▼
   decompose/     → instance tree (multi-depth via cjk-decomp)
          ▼
   prototypes/    → prototype-library.json (DAG, shared)
          ▼
   compose/       → glyph-record-<char>.json (flattened, post-transform)
          ▼
   + rule trace   → rule-trace-<char>.json (decisions emitted by rules/)
          │
          ▼
      schema/examples/  (validated by @olik/glyph-schema)
          │
          ├──▶  @olik/remotion-studio   (animated presentation)
          └──▶  @olik/inspector         (xyflow interactive inspection)
```

Single CLI call produces: 4 × `glyph-record-*.json` + 4 × `rule-trace-*.json` + 1 × `prototype-library.json`.

### Two artifacts: tree (per glyph) + graph (shared)

1. **`prototype-library.json`** — the graph. Prototypes keyed by ID; edges express `refines-to` relationships. Carries canonical geometry (stroke paths + medians in local 1024² space), anchors, role tags, refinement hints. Shared across all glyphs.
2. **`glyph-record-<char>.json`** — the tree for one glyph. References prototypes by ID. Carries `coord_space`, `layout_tree`, `component_instances`, `stroke_instances` (flattened post-transform), `constraints` (resolved), `render_layers`, `roles`, `metadata` (source, IoU report, generator version).

### Schema draft (normative in pass 1; revisable)

**prototype-library.json**:

```jsonc
{
  "schema_version": "0.1",
  "coord_space": { "width": 1024, "height": 1024, "origin": "top-left", "y_axis": "down" },
  "prototypes": {
    "proto:water_3dots": {
      "id": "proto:water_3dots",
      "name": "氵",
      "kind": "component",
      "source": { "kind": "mmh-extract", "from_char": "清", "stroke_indices": [0,1,2] },
      "canonical_bbox": [0, 0, 1024, 1024],
      "strokes": [
        { "id": "s0", "path": "M...Z", "median": [[..],[..]], "order": 0, "role": "dot" }
      ],
      "anchors": { "center": [512,512], "right_edge": [1024,512], "top": [512,0] },
      "roles": ["meaning"],
      "refinement": { "mode": "keep", "alternates": [] }
    }
    // ... 日, 月, 青, 生, 囗, 或, 木
  },
  "edges": [
    // future: { "from": "proto:speech", "kind": "refines-to", "to": "proto:speech_split_5" }
  ]
}
```

**glyph-record-<char>.json** (abbreviated):

```jsonc
{
  "schema_version": "0.1",
  "glyph_id": "清",
  "unicode": "U+6E05",
  "coord_space": { "width": 1024, "height": 1024, "origin": "top-left", "y_axis": "down" },
  "source": { "stroke_source": "make-me-a-hanzi", "decomp_source": "cjk-decomp" },

  "layout_tree": {
    "id": "root",
    "bbox": [0, 0, 1024, 1024],
    "decomp_source": { "adapter": "cjk-decomp", "operator": "c", "raw": "c(氵,青)" },
    "input_adapter": "preset:left_right",
    "children": [
      { "id": "inst:shui3", "prototype_ref": "proto:water_3dots",
        "mode": "keep", "depth": 1, "transform": { /* ... */ } },
      { "id": "inst:qing1",  "prototype_ref": "proto:qing",
        "mode": "refine", "depth": 1,
        "decomp_source": { "adapter": "cjk-decomp", "operator": "b", "raw": "b(生,月)" },
        "input_adapter": "preset:top_bottom",
        "transform": { /* placement of 青 as a unit */ },
        "children": [
          { "id": "inst:sheng", "prototype_ref": "proto:sheng",
            "mode": "keep", "depth": 2, "transform": { /* ... */ } },
          { "id": "inst:yue",   "prototype_ref": "proto:yue",
            "mode": "keep", "depth": 2, "transform": { /* ... */ } }
        ]
      }
    ]
  },

  "component_instances": [ /* derived from layout_tree leaves */ ],
  "stroke_instances":    [ /* flattened + post-transform — what Remotion animates */ ],
  "constraints":         [ /* resolved primitives after preset/anchor-binding expansion */ ],
  "render_layers": [
    { "name": "skeleton",        "z_min": 0,  "z_max": 9  },
    { "name": "stroke_body",     "z_min": 10, "z_max": 49 },
    { "name": "stroke_edge",     "z_min": 50, "z_max": 69 },
    { "name": "texture_overlay", "z_min": 70, "z_max": 89 },
    { "name": "damage",          "z_min": 90, "z_max": 99 }
  ],
  "roles": { "inst:shui3": { "dong_chinese": "meaning" }, /* ... */ },
  "metadata": {
    "generated_at": "2026-04-21T00:00:00Z",
    "generator":    "olik-font py/0.1",
    "iou_report":   { "mean": 0.93, "min": 0.88, "per_stroke": { /* ... */ } }
  }
}
```

### Decisions

- **D1.** `stroke_instances` is flattened + post-transform. Tree is for visualization; strokes are for rendering. Simpler consumer; direct diff against MMH.
- **D2.** Prototype extraction uses a hand-authored `py/data/extraction_plan.yaml` in pass 1. MMH's `matches` field is a cross-check, not ground truth.
- **D3.** Roles seeded by hand for the 4 chars using Dong-Chinese tags `{meaning, sound, iconic, distinguishing, unknown}`.
- **D4.** Data model has no preset/relation enum. Only `transform` + `anchor_bindings`. Preset names live in `input_adapter` metadata for debugging; they are not primary data.
- **D5.** Anchors are first-class on every prototype, even in pass 1.
- **D6.** At least one placement per seed char is authored via anchor-binding or direct mode (not preset), to keep the general path exercised.
- **D7.** Recursive decomposition via cjk-decomp (from HanziJS), not IDS-only. Richer operator set feeds the preset adapter.
- **D8.** `refine` mode is implemented in pass 1; `replace` stays schema-only.
- **D9.** Per-character depth choices are authored in `extraction_plan.yaml`, not inferred. A future heuristic can replace authored choices; the schema won't change.
- **D10.** HanziJS is reference-only. We re-read `cjk-decomp.txt` in Python directly.

## Section 3 — Composition in virtual coordinates

### Authoring primitive

One primitive places a node:

```python
@dataclass
class InstancePlacement:
    instance_id:     str
    prototype_ref:   str
    transform:       Affine                    # prototype local → glyph virtual coord
    anchor_bindings: list[AnchorBinding] = []  # optional refinements
    mode:            Literal["keep","refine","replace"] = "keep"
    children:        list[InstancePlacement] = []
```

A character — real CJK or invented — is a tree of these. Presets and IDS relations live **one level up**, in input adapters. The compose algorithm only knows `transform` and `anchor_bindings`.

### Four authoring strategies (all emit the same `InstancePlacement`)

| Strategy | Input | Use case |
|---|---|---|
| **direct** | Hand-authored affine per instance | Invented symbols, 森 (pass 1) |
| **anchor-binding** | `(proto.anchor_a → sibling.anchor_b, distance)` pairs | Organic arrangements; 清's 3-dot internal layout; 國's inner |
| **preset** | `(name, params)` from cjk-decomp operator | Classical CJK fast path; 明, 清, 國 |
| **learned** (deferred) | Component list + style ref | IF-Font / CCFont layout prediction |

### Constraint primitives (pass 1 subset)

Only what the 4 chars need; the rest are named stubs.

| Primitive | Used by |
|---|---|
| `align_x`, `align_y` | all presets |
| `order_x`, `order_y` | left_right, top_bottom, 森 ordering |
| `anchor_distance` | left_right gap, enclose padding |
| `inside` | 囗 containing 或 |
| `avoid_overlap` | post-check across siblings |
| `repeat` | 森's three 木 (direct-authored) |

Presets ship in `py/constraints/presets.py` as pure functions `(children, params) → List[Primitive]`. Presets emit a resolved constraint list into the glyph record so Remotion / Inspector can visualize the *why*.

### Composition algorithm

```
compose(instance_tree, prototype_library) -> glyph_record:

  1. resolve_placements(instance_tree):
        post-order; for each node:
          if node.transform is set:                  # direct or preset-expanded
              use it
          elif node.anchor_bindings is non-empty:    # anchor-binding
              solve affine from bindings + child bboxes
          else:
              error: under-specified placement

  2. flatten_strokes(instance_tree):
        for each leaf, apply accumulated transform to its prototype strokes

  3. assign_z_by_role(stroke_instances):
        role → layer base; order → offset

  4. post_checks(stroke_instances):
        avoid_overlap scan across siblings → warnings
        IoU vs MMH per stroke → metadata.iou_report

  5. emit glyph_record (layout_tree, component_instances, stroke_instances,
                        constraints (resolved), render_layers, metadata)
```

Deterministic, single-pass, no iterative solver. Presets are fully constructive in pass 1; the algorithm is preset-agnostic.

### Per-char exercise plan

- **明** — preset `left_right`. Two level-1 prototypes. Baseline.
- **清** — preset `left_right` at root + `refine` mode on 青 (one level deeper via cjk-decomp) + anchor-binding inside 氵's 3-dot layout. 月 shared with 明.
- **國** — preset `enclose` at root + inner 或 via anchor-binding (`inner.center → outer.center`, `inner.bbox inside outer.inner_frame`), not preset-expanded. Proves `enclose` isn't hard-coded.
- **森** — direct mode entirely. Three 木 instances with explicit transforms. Invented-symbol test path.

### Decisions

- **D4–D6.** (See Section 2 — same data-model principles.)
- **D11.** Deterministic single-pass composition; no iterative solver in pass 1. Swap point: step 1 → cassowary/SAT when circular constraints appear.
- **D12.** `avoid_overlap` is a post-condition check in pass 1, not a solver input.
- **D13.** IoU-vs-MMH is the acceptance test for compose correctness (`metadata.iou_report`). Threshold: `min ≥ 0.85` warns; `min ≥ 0.80` fails.
- **D14.** All-`keep` is not mandatory: 清 exercises `refine` so the code path is real, not aspirational.

## Section 4 — Presentation: Remotion + xyflow Inspector

Two separate surfaces. Remotion for animated linear presentation; xyflow for interactive inspection. Both are **read-only** in pass 1 — all authoring happens in Python + YAML.

### Python rule library (feeds both surfaces)

`py/src/olik_font/rules/` names the implicit decisions so they become reviewable.

```
rules/
├── __init__.py
├── engine.py              # applies an ordered rule set; emits rule-trace
├── decomp_rules.py        # depth choice per node
├── compose_rules.py       # input-adapter choice per node
├── prototype_rules.py     # MMH stroke → prototype carving
└── rules.yaml             # declarative ordered rule set for pass 1
```

**Rule kinds**:
- Decomposition rules — choose `keep` / `refine` / `replace` given char + cjk-decomp result
- Composition rules — choose `direct` / `preset` / `anchor-binding` given node context
- Prototype extraction rules — carve MMH strokes into prototype geometry

**Rule-trace artifact** (`rule-trace-<char>.json`), per decision:

```jsonc
{
  "decision_id":  "d:qing_right.depth",
  "rule_id":      "decomp.refine_compound_on_seed_list",
  "inputs":       { "char": "青", "operator": "b", "is_seed": true },
  "output":       { "mode": "refine", "depth": 2 },
  "alternatives": [ { "rule_id": "decomp.default_keep", "would_output": { "mode": "keep" } } ],
  "applied_at":   "2026-04-21T..."
}
```

Rules are **YAML + engine**, not pure code, so rule sets are diffable, swappable (pass-1 vs. future learned), and experiment-friendly.

### Remotion Studio — `apps/remotion-studio/`

Five compositions + one storyboard. Each is a pure function of `(glyphRecord, prototypeLibrary, config)`.

1. **CharacterAnim** — animCJK-style stroke-order animation. Side-by-side composed vs. MMH original. IoU badges per stroke + per glyph. The "does it reconstruct?" artifact.
2. **DecompositionTree** — tidy-tree over `layout_tree`, synchronized with `CharacterAnim`. Shows `mode`, `depth`, `input_adapter` (colored chip per authoring strategy). 清's `refine` node visibly expands.
3. **PrototypeGraph** — force-directed DAG across all 4 chars. Node size ∝ instance count. 月 lights twice (明, 清); 木 lights three times (森). The "is reuse real?" artifact.
4. **LayerZDepth** — exploded 3D-ish layer planes. Strokes materialize plane-by-plane; collapse to the composed glyph. Pass-1 layers are mostly `stroke_body` only — the view validates the mechanic, not the content.
5. **VirtualCoord** — 1024×1024 grid overlay that can toggle over any other composition. Per-instance bboxes, anchors, resolved anchor-binding arrows, transforms. The "receipt" view.
6. **Storyboard** — meta-composition stitching 4.1 → 4.5 per char into one ~60s-per-char demo.

### xyflow Inspector — `apps/inspector/`

Interactive exploration; separate interaction model from Remotion.

1. **Decomposition Explorer** — xyflow graph of cjk-decomp for a char. Click a node to see which rule(s) would apply for `keep` vs. `refine`. Read-only in pass 1.
2. **Prototype Library Browser** — DAG of prototypes with instance counts. Click to see strokes, canonical bbox, anchors, role tags, hosting chars.
3. **Rule Browser** — `rules.yaml` as a flow graph. Overlay a `rule-trace-<char>.json` to highlight the rule path that fired.
4. **Placement Debugger** — xyflow-renders a glyph's `layout_tree`. Each node annotated with input_adapter, transform, resolved constraints. Click to pop geometry in `VirtualCoordGrid`.

### Package split

- `packages/glyph-viz/` — framework-neutral SVG primitives: `StrokePath`, `VirtualCoordGrid`, `BBoxOverlay`, `AnchorMarker`, `AnchorBindingArrow`, `TreeLayout`, `GraphLayout`, `LayerStack`, `IoUBadge`, `InputAdapterChip`, `ModeIndicator`.
- `packages/glyph-loader/` — fs/URL load + zod validate.
- `packages/flow-nodes/` — xyflow `<Node>` wrappers that compose `glyph-viz` primitives inside their bodies.
- `packages/rule-viz/` — rule-graph view primitives (rule node, precedence edge, fallback-chain edge, trace-highlight overlay).
- `apps/remotion-studio/` — thin; compositions only.
- `apps/inspector/` — thin; wires `flow-nodes` + `rule-viz` + `glyph-viz` into four view routes.

### Decisions

- **D15.** Rules are data (YAML) + engine, not scattered code. Rule traces are a first-class output artifact.
- **D16.** Inspector is a separate app from Remotion Studio; both read the same JSON artifacts.
- **D17.** Both apps are read-only in pass 1. Authoring stays in Python + YAML.
- **D18.** `Storyboard` is the demo artifact; the five individual compositions are diagnostic.
- **D19.** IoU-vs-MMH is both a metric (`metadata.iou_report`) and a visual (badges in `CharacterAnim`).

## Section 5 — Dev workflow: Archon + worktrees + agent lanes

### Lane inventory (15)

Python (8) — `P1 sources/makemeahanzi`, `P2 sources/cjk_decomp`, `P3 decompose/`, `P4 prototypes/`, `P5 constraints/`, `P6 compose/`, `P7 rules/`, `P8 cli.py + integration`.

TypeScript (7) — `T1 schema/`, `T2 glyph-schema`, `T3 glyph-loader`, `T4 glyph-viz`, `T5 flow-nodes + rule-viz`, `T6 remotion-studio`, `T7 inspector`.

Dependencies: `P3 ← P1,P2`; `P4 ← P1,P3`; `P6 ← P3,P4,P5`; `P8 ← P1..P7`. `T2 ← T1`; `T3 ← T2`; `T5 ← T2,T4`; `T6 ← T3,T4, records from P8`; `T7 ← T3,T4,T5, records from P8`.

### Git worktree location

**Single convention: `.worktrees/` at the repo root, gitignored.** One location for both lane work and Archon-spawned tasks; consistent with project's existing dotted-dir style (`.agent/`, `.claude/`).

```
olik-font/                          # main checkout, main branch
├── .worktrees/                     # gitignored
│   ├── p3-decompose/               # branch: feat/p3-decompose
│   ├── p6-compose/                 # branch: feat/p6-compose
│   ├── t4-glyph-viz/
│   ├── archon-wf-compose-char-qing/   # Archon-spawned
│   └── …
└── …
```

**Branch naming**: `feat/<lane-id>-<slug>` for manual lane work; `archon/task-<slug>` for Archon-spawned tasks (Archon's own convention). Both land under `.worktrees/`.

**Archon config**: point `worktrees.root_path` (or equivalent) to `<repo>/.worktrees/` when Archon is installed. If Archon's config key differs at install time, adjust there — the convention here is the source of truth.

### Agent assignment ("one CLI, one job")

| CLI | Role | Lanes |
|---|---|---|
| **Codex** (GPT-5.4 via ChatGPT OAuth) | Primary; Python-strong; runs inside Archon AI nodes | P1, P3, P6, P7, P8 |
| **Pi** (ZAI / GLM-5.1) | Secondary; parallel Python; `bash:` nodes | P2, P4, P5 |
| **Kimi** (Moonshot) | TS / React; `bash:` nodes | T2, T3, T6, T7 |
| **Copilot** (GitHub OAuth) | Cross-cutting: git ops, issue/PR grooming, worktree setup | — |
| **Ollama / Gemma4:31b** (cloud) | Review-only, second opinion; `bash:` nodes | All lanes |

T1, T4, T5 are small; default to Kimi. Assignment is for predictability, not load balancing.

### Archon workflows

Named workflows, PostgreSQL-backed, Codex-SDK-driven. Implementation follows Archon install (handover item #3).

- **`wf/bootstrap`** — one-off. Runs P1 + P2 + T1 to land shared foundation.
- **`wf/lane/<lane-id>`** — per lane. SDLC DAG: `plan → scaffold → implement → test → self-review → commit → open-PR`. Codex nodes for P-Codex lanes; `bash:` wrappers for Pi / Kimi / Copilot.
- **`wf/compose-char/<char>`** — per character. Full py pipeline end-to-end; emits `glyph-record-<char>.json` + `rule-trace-<char>.json`.
- **`wf/integration/pass-1`** — join point after all lane PRs close. Runs `wf/compose-char` for 明/清/國/森; opens Inspector + Remotion Studio against artifacts; manual review gate.
- **`wf/review`** — takes a PR number; spawns Gemma4 reviewer; writes comments via Copilot.

### Sync points

Three, in order:

1. After P1 + P2 + T1 (foundation lands; every other lane unblocks).
2. After P6 + P8 (first real glyph record exists; T6/T7 stop using fake records).
3. After all lanes + `wf/compose-char` for 明/清/國/森 (pass 1 complete).

Between sync points, lanes are independent. PRs to `main` merge in any order.

### Safety rails

- **Worktree ownership file** `.worktree-owner` at each worktree root (lane + CLI + branch). Pre-commit hook enforces that staged paths lie within the lane's declared module paths.
- **Lockfile discipline** — `pnpm-lock.yaml` / `pyproject.toml` changes go through a dedicated `chore/deps` worktree.
- **No force-push to `main`**; no rebasing others' feature branches; merge-commits for lane PRs.
- **`ref-projects/` is read-only** (existing project convention). Hook rejects writes under that path from any worktree.
- **Secrets don't travel** — `infra/.env` stays host-local; Archon references env by key, never inline values.

### Decisions

- **D20.** `.worktrees/` at repo root is the single worktree location for both lane and Archon work. Gitignored.
- **D21.** Worktrees (not in-place branches) are the isolation unit. One worktree per lane for the life of the lane.
- **D22.** Archon is the orchestration substrate. Codex owns AI nodes; non-Codex CLIs run via `bash:` nodes.
- **D23.** Gemma4 is review-only. Keeps implementer and reviewer separate.
- **D24.** Rule traces + IoU reports are the objective review criteria for P-lane PRs.
- **D25.** Sync points are explicit (three for pass 1). No lane claims completion until its sync point closes.

## Reviewable decisions

All design calls, consolidated for easy diffing. Numbers are stable references — don't renumber on edits; add new decisions at the end.

- **D1.** `stroke_instances` is flattened + post-transform. Tree for viz, strokes for rendering.
- **D2.** Prototype extraction uses hand-authored `extraction_plan.yaml` in pass 1.
- **D3.** Roles seeded by hand for 4 chars with Dong-Chinese tags.
- **D4.** No preset/relation enum in the data model. Only `transform` + `anchor_bindings`. `input_adapter` is metadata.
- **D5.** Anchors are first-class on every prototype.
- **D6.** At least one placement per seed char authored via anchor-binding or direct mode.
- **D7.** Recursive decomposition via cjk-decomp, not IDS-only.
- **D8.** `refine` mode implemented in pass 1; `replace` schema-only.
- **D9.** Per-character depth choices authored, not inferred.
- **D10.** HanziJS reference-only; we re-read `cjk-decomp.txt` in Python.
- **D11.** Deterministic single-pass composition; no iterative solver in pass 1.
- **D12.** `avoid_overlap` is a post-condition check in pass 1.
- **D13.** IoU-vs-MMH is the acceptance test. Warn `< 0.85`; fail `< 0.80`.
- **D14.** `refine` exercised in pass 1 via 清/青.
- **D15.** Rules are data (YAML) + engine. Rule traces are first-class.
- **D16.** Inspector is a separate app from Remotion Studio.
- **D17.** Both apps read-only in pass 1.
- **D18.** `Storyboard` is the demo artifact; five individual compositions are diagnostic.
- **D19.** IoU is both metric and visual.
- **D20.** `.worktrees/` at repo root; single convention for lane + Archon work.
- **D21.** Worktrees are the isolation unit.
- **D22.** Archon orchestrates; Codex for AI nodes, others via `bash:`.
- **D23.** Gemma4 is review-only.
- **D24.** Rule traces + IoU are PR review criteria.
- **D25.** Three explicit sync points for pass 1.

## Deferred work

Every named-but-not-built item, consolidated so nothing gets lost. Organized by module for retrieval, not priority.

### Schema / composition

- Iterative constraint solver (cassowary / SAT) — unlocks circular anchor bindings.
- `replace` node mode — code path; schema slot already exists.
- Style-variant alternates per prototype.
- Learned layout adapter — IF-Font / CCFont-style placement prediction. Emits the same `InstancePlacement` trees as manual adapters.
- Per-stroke nonlinear deformation (warp fields).
- Quadtree acceleration for `avoid_overlap` scans and nearest-neighbor queries.
- Automated IDS/cjk-decomp parsing to replace the hand-authored `extraction_plan.yaml`.
- Constraint primitives reserved but not implemented in pass 1: `tangent`, `center_on_path`, `distribute_along_curve`, `radial_array`, `mirror`, `stack_by_priority`, `preserve_gap`.
- Anchor inference — extracting semantically meaningful anchors from prototype geometry (currently hand-declared).
- Font-metrics extension in `coord_space`.
- Render-layer population beyond `stroke_body` (edge, texture, damage are empty in pass 1).

### Rules / decomposition

- Richer rule sets (per-style, per-corpus).
- Learned rules as a second rule source that emits the same trace format.
- Rule diffs (two rule-sets side-by-side).
- Time-travel replay of rule firings for a given compose run.

### Presentation

- Interactive edits in Inspector that round-trip back to YAML (rule edits, placement edits, prototype edits).
- Diff mode: two glyph records or two rule sets, xyflow-diffed.
- Visual rule authoring: drag nodes to create new rules without touching YAML.
- Web playground / docs app consuming the same JSON.

### Future packages (named, not built)

- `packages/glyph-styler/` — ComfyUI bridge for the styling stage.
- `packages/glyph-export/` — Potrace / FontForge export tail (qiji-font style).
- `packages/prototype-editor/` — hand-authoring tool for prototype geometry and anchors.

### Dev workflow

- Archon install + PostgreSQL setup + `~/.archon/config.yaml` tuning (handover item #3; prerequisite, not part of pass-1 design).
- Dynamic lane rebalancing (idle CLI picks up another lane).
- Automated worktree provisioning script (Copilot-generated).
- `wf/review` gate as a GitHub PR check (auto-review on PR open).
- Per-lane test coverage thresholds enforced by workflow gates.

### Data sources (named adapters, not built)

- `sources/hanzicraft` — productive-component frequency data, phonetic sets.
- `sources/hanzivg` — stroke-order SVGs + radical/component metadata.
- `sources/dong_chinese` — authoritative role-color labels beyond our hand-seeded tags.

## See also

- [[glyph-scene-graph-spec]] — the distilled, language-neutral spec this plan implements.
- [[glyph-scene-graph-pipeline.excalidraw]] — pipeline diagram stub.
- [[discussion-0003]] — raw thread proposing component-first pipeline + scene graph.
- [[discussion-0004]] — raw thread replacing IDS enums with constraint-based backend.
- [[handover-2026-04-21]] — session handover; project conventions, CLI state, open items.
- `.agent/skills/00-meta/archon-workflows/SKILL.md` — Archon usage conventions.
- `ref-projects/animCJK/` — presentation reference (stroke-order SVG animation).
- `ref-projects/hanzi/` — HanziJS, source of the cjk-decomp dataset used in `sources/cjk_decomp`.
- `ref-projects/xyflow/` — React Flow, basis for Inspector views.
