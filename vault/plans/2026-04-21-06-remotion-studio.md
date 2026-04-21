---
title: "Plan 06 — Remotion Studio (T6)"
created: 2026-04-21
tags: [type/plan, topic/scene-graph]
source: self
spec: "[[2026-04-21-glyph-scene-graph-solution-design]]"
status: draft
phase: 6
depends-on:
  - "[[2026-04-21-03-python-compose-cli]]"
  - "[[2026-04-21-05-ts-viz-primitives]]"
---

# Plan 06 — Remotion Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `apps/remotion-studio` — a Remotion 4 app with five compositions + one storyboard, rendering validated JSON records from Plan 03 into animated video using primitives from Plan 05.

**Architecture:** Thin app. All reusable rendering logic is in `@olik/glyph-viz`; the app contributes only timeline mapping (frame → progress), scene orchestration, and composition registration. Data loads once at module init via `@olik/glyph-loader`'s `loadBundleFs` wrapped in `delayRender/continueRender`. Each composition is a pure component taking a pre-loaded `GlyphBundle` + props.

**Tech Stack:** Remotion 4.x, React 18, TypeScript 5.6, pnpm 9.

---

## File Structure

```
project/ts/apps/remotion-studio/
├── package.json
├── tsconfig.json
├── remotion.config.ts
├── src/
│   ├── Root.tsx                        # Composition registry
│   ├── load-records.ts                 # bundle loader (delayRender-compatible)
│   ├── timing.ts                       # shared frame/progress helpers
│   ├── compositions/
│   │   ├── CharacterAnim.tsx
│   │   ├── DecompositionTree.tsx
│   │   ├── PrototypeGraph.tsx
│   │   ├── LayerZDepth.tsx
│   │   ├── VirtualCoord.tsx
│   │   └── Storyboard.tsx
│   └── index.ts                        # Remotion entry point
└── test/
    ├── timing.test.ts
    └── load-records.test.ts
```

Composition conventions:
- Canvas: 1280×720, 30fps.
- Per-char scene: 3s (90 frames). Storyboard: 4 chars × (5 scenes × 3s) = 60s per char → 4 min total. Or override via props at registration.
- Glyph is drawn at 800×800 centered in the 1280×720 frame; side panels (trees, badges) occupy the remaining ~400px column.

---

## Task 1: Scaffold Remotion app

**Files:**
- Create: `project/ts/apps/remotion-studio/package.json`
- Create: `project/ts/apps/remotion-studio/tsconfig.json`
- Create: `project/ts/apps/remotion-studio/remotion.config.ts`
- Create: `project/ts/apps/remotion-studio/src/index.ts`
- Create: `project/ts/apps/remotion-studio/src/Root.tsx`

- [ ] **Step 1: `package.json`**

```json
{
  "name": "@olik/remotion-studio",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "studio": "remotion studio",
    "build":  "remotion render Storyboard out/storyboard.mp4",
    "test":   "vitest run",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@olik/glyph-loader": "workspace:*",
    "@olik/glyph-schema": "workspace:*",
    "@olik/glyph-viz":    "workspace:*",
    "react":              "18.3.1",
    "react-dom":          "18.3.1",
    "remotion":           "4.0.228",
    "@remotion/cli":      "4.0.228",
    "@remotion/bundler":  "4.0.228"
  },
  "devDependencies": {
    "@types/react":     "18.3.11",
    "@types/react-dom": "18.3.0",
    "typescript":       "5.6.3",
    "vitest":           "2.1.2"
  }
}
```

- [ ] **Step 2: `tsconfig.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "rootDir": "./src",
    "outDir":  "./dist",
    "jsx":     "react-jsx",
    "noEmit":  true
  },
  "include": ["src/**/*", "test/**/*"]
}
```

- [ ] **Step 3: `remotion.config.ts`**

```ts
import { Config } from "@remotion/cli/config";

Config.setEntryPoint("./src/index.ts");
Config.setVideoImageFormat("png");
Config.setPixelFormat("yuv420p");
```

- [ ] **Step 4: `src/index.ts`**

```ts
// project/ts/apps/remotion-studio/src/index.ts
import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root.js";

registerRoot(RemotionRoot);
```

- [ ] **Step 5: Placeholder `Root.tsx`**

```tsx
// project/ts/apps/remotion-studio/src/Root.tsx
import * as React from "react";
import { Composition } from "remotion";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Placeholder"
      component={() => <div style={{background: "#000", width: 1280, height: 720}} />}
      durationInFrames={30}
      fps={30}
      width={1280}
      height={720}
    />
  );
};
```

- [ ] **Step 6: Install + verify typecheck**

```bash
cd project/ts && pnpm install
cd apps/remotion-studio && pnpm typecheck
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add project/ts/apps/remotion-studio project/ts/pnpm-lock.yaml
git commit -m "chore(remotion): scaffold @olik/remotion-studio app"
```

---

## Task 2: Bundle loader (`delayRender`-compatible)

**Files:**
- Create: `project/ts/apps/remotion-studio/src/load-records.ts`
- Create: `project/ts/apps/remotion-studio/test/load-records.test.ts`

- [ ] **Step 1: Write failing test**

```ts
// project/ts/apps/remotion-studio/test/load-records.test.ts
import { describe, expect, test } from "vitest";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { exampleDirPath, loadSeedBundle } from "../src/load-records.js";

const EXAMPLES = resolve(__dirname, "../../../../schema/examples");

describe("loadSeedBundle", () => {
  test("resolves path relative to ts/schema/examples", () => {
    expect(exampleDirPath()).toContain("schema/examples");
  });

  test.runIf(existsSync(resolve(EXAMPLES, "prototype-library.json")))(
    "loads all four seed chars + library",
    async () => {
      const bundle = await loadSeedBundle();
      expect(Object.keys(bundle.records).sort()).toEqual(["國", "明", "清", "森"].sort());
      expect(Object.keys(bundle.library.prototypes).length).toBeGreaterThanOrEqual(7);
    },
  );
});
```

- [ ] **Step 2: Implement `load-records.ts`**

```ts
// project/ts/apps/remotion-studio/src/load-records.ts
import { loadBundleFs, type GlyphBundle } from "@olik/glyph-loader";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const SEED_CHARS = ["明", "清", "國", "森"] as const;

export function exampleDirPath(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  // remotion-studio/src/load-records.ts → ../../../../schema/examples
  return resolve(here, "../../../../schema/examples");
}

export async function loadSeedBundle(): Promise<GlyphBundle> {
  return await loadBundleFs(exampleDirPath(), SEED_CHARS);
}
```

- [ ] **Step 3: Run test**

```bash
cd project/ts/apps/remotion-studio && pnpm test
```

Expected: `2 passed` (or 1 + 1 skipped if Plan 03 hasn't run).

- [ ] **Step 4: Commit**

```bash
git add project/ts/apps/remotion-studio/src/load-records.ts project/ts/apps/remotion-studio/test/load-records.test.ts
git commit -m "feat(remotion): load-records bundle loader"
```

---

## Task 3: Timing helpers

**Files:**
- Create: `project/ts/apps/remotion-studio/src/timing.ts`
- Create: `project/ts/apps/remotion-studio/test/timing.test.ts`

- [ ] **Step 1: Write failing test**

```ts
// project/ts/apps/remotion-studio/test/timing.test.ts
import { describe, expect, test } from "vitest";
import { strokeProgress, strokeStartFrame, totalStrokeFrames } from "../src/timing.js";

describe("stroke timing", () => {
  test("sequential: stroke N starts after stroke N-1 completes", () => {
    expect(strokeStartFrame({ strokeIndex: 0, framesPerStroke: 10 })).toBe(0);
    expect(strokeStartFrame({ strokeIndex: 1, framesPerStroke: 10 })).toBe(10);
    expect(strokeStartFrame({ strokeIndex: 3, framesPerStroke: 10 })).toBe(30);
  });

  test("progress: 0 before start, 1 after completion", () => {
    expect(strokeProgress({ frame: 0, strokeIndex: 1, framesPerStroke: 10 })).toBe(0);
    expect(strokeProgress({ frame: 15, strokeIndex: 1, framesPerStroke: 10 })).toBeCloseTo(0.5, 2);
    expect(strokeProgress({ frame: 25, strokeIndex: 1, framesPerStroke: 10 })).toBe(1);
  });

  test("totalStrokeFrames covers all strokes", () => {
    expect(totalStrokeFrames({ strokeCount: 8, framesPerStroke: 10 })).toBe(80);
  });
});
```

- [ ] **Step 2: Implement `timing.ts`**

```ts
// project/ts/apps/remotion-studio/src/timing.ts
export function strokeStartFrame(params: {
  strokeIndex:     number;
  framesPerStroke: number;
}): number {
  return params.strokeIndex * params.framesPerStroke;
}

export function strokeProgress(params: {
  frame:           number;
  strokeIndex:     number;
  framesPerStroke: number;
}): number {
  const start = strokeStartFrame(params);
  const end   = start + params.framesPerStroke;
  if (params.frame <= start) return 0;
  if (params.frame >= end)   return 1;
  return (params.frame - start) / params.framesPerStroke;
}

export function totalStrokeFrames(params: {
  strokeCount:     number;
  framesPerStroke: number;
}): number {
  return params.strokeCount * params.framesPerStroke;
}
```

- [ ] **Step 3: Run**

```bash
cd project/ts/apps/remotion-studio && pnpm test
```

Expected: `5 passed`.

- [ ] **Step 4: Commit**

```bash
git add project/ts/apps/remotion-studio/src/timing.ts project/ts/apps/remotion-studio/test/timing.test.ts
git commit -m "feat(remotion): frame→progress timing helpers"
```

---

## Task 4: `CharacterAnim` composition

**Files:**
- Create: `project/ts/apps/remotion-studio/src/compositions/CharacterAnim.tsx`

- [ ] **Step 1: Implement**

```tsx
// project/ts/apps/remotion-studio/src/compositions/CharacterAnim.tsx
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { IoUBadge, StrokePath, VirtualCoordGrid } from "@olik/glyph-viz";
import type { GlyphBundle } from "@olik/glyph-loader";
import { strokeProgress } from "../timing.js";

export interface CharacterAnimProps {
  bundle:          GlyphBundle;
  char:            string;
  framesPerStroke: number;
  showGrid?:       boolean;
}

export const CharacterAnim: React.FC<CharacterAnimProps> = ({
  bundle, char, framesPerStroke, showGrid = false,
}) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const record = bundle.records[char];
  if (!record) return null;

  const glyphSize = 800;
  const gx = (width - glyphSize) / 2;
  const gy = (height - glyphSize) / 2;
  const iou = record.metadata?.iou_report?.mean ?? 1;

  return (
    <AbsoluteFill style={{ background: "#ffffff" }}>
      <svg width={width} height={height}>
        <g transform={`translate(${gx}, ${gy}) scale(${glyphSize / 1024})`}>
          {showGrid ? <VirtualCoordGrid /> : null}
          {record.stroke_instances.map((s, i) => (
            <StrokePath
              key={s.id}
              outlinePath={s.path}
              median={s.median as Array<[number, number]>}
              progress={strokeProgress({ frame, strokeIndex: i, framesPerStroke })}
            />
          ))}
        </g>
        <g transform={`translate(40, 40)`}>
          <text fontSize={56} fontFamily="serif">{char}</text>
        </g>
        <g transform={`translate(${width - 120}, ${height - 40})`}>
          <IoUBadge value={iou} />
        </g>
      </svg>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Register composition in `Root.tsx`**

Replace placeholder Root with:

```tsx
// project/ts/apps/remotion-studio/src/Root.tsx
import * as React from "react";
import { Composition, delayRender, continueRender } from "remotion";
import type { GlyphBundle } from "@olik/glyph-loader";
import { CharacterAnim } from "./compositions/CharacterAnim.js";
import { loadSeedBundle, SEED_CHARS } from "./load-records.js";
import { totalStrokeFrames } from "./timing.js";

const FRAMES_PER_STROKE = 12;

export const RemotionRoot: React.FC = () => {
  const [bundle, setBundle] = React.useState<GlyphBundle | null>(null);
  const [handle] = React.useState(() => delayRender("load-bundle"));

  React.useEffect(() => {
    loadSeedBundle()
      .then((b) => {
        setBundle(b);
        continueRender(handle);
      })
      .catch((err) => {
        console.error("load bundle failed:", err);
        continueRender(handle);
      });
  }, [handle]);

  if (!bundle) return null;

  return (
    <>
      {SEED_CHARS.map((ch) => {
        const strokes = bundle.records[ch]?.stroke_instances.length ?? 8;
        const duration = totalStrokeFrames({
          strokeCount:     strokes,
          framesPerStroke: FRAMES_PER_STROKE,
        }) + 30;  // trailing hold
        return (
          <Composition
            key={`char-${ch}`}
            id={`CharacterAnim-${ch}`}
            component={CharacterAnim}
            durationInFrames={duration}
            fps={30}
            width={1280}
            height={720}
            defaultProps={{ bundle, char: ch, framesPerStroke: FRAMES_PER_STROKE, showGrid: false }}
          />
        );
      })}
    </>
  );
};
```

- [ ] **Step 3: Start Remotion Studio and verify**

```bash
cd project/ts/apps/remotion-studio && pnpm studio
```

Expected: browser opens to `http://localhost:3000`; four compositions named `CharacterAnim-明` / -清 / -國 / -森 appear; scrubbing each shows stroke-by-stroke drawing.

If the Plan 03 artifacts aren't present, the compositions render blank but don't crash — acceptable.

Stop the studio (Ctrl-C) before continuing.

- [ ] **Step 4: Commit**

```bash
git add project/ts/apps/remotion-studio/src/compositions/CharacterAnim.tsx project/ts/apps/remotion-studio/src/Root.tsx
git commit -m "feat(remotion): CharacterAnim composition + bundle-driven Root"
```

---

## Task 5: `DecompositionTree` composition (synced with CharacterAnim)

**Files:**
- Create: `project/ts/apps/remotion-studio/src/compositions/DecompositionTree.tsx`

- [ ] **Step 1: Implement**

```tsx
// project/ts/apps/remotion-studio/src/compositions/DecompositionTree.tsx
import * as React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import {
  InputAdapterChip, ModeIndicator, TreeLayout,
} from "@olik/glyph-viz";
import type { GlyphBundle } from "@olik/glyph-loader";
import type { LayoutNode } from "@olik/glyph-schema";
import { strokeProgress } from "../timing.js";

export interface DecompositionTreeProps {
  bundle:          GlyphBundle;
  char:            string;
  framesPerStroke: number;
}

export const DecompositionTree: React.FC<DecompositionTreeProps> = ({
  bundle, char, framesPerStroke,
}) => {
  const frame = useCurrentFrame();
  const record = bundle.records[char];
  if (!record) return null;

  // Each stroke "belongs" to an instance_id. We map instance_id → tree node id
  // and mark a node as "lit" when all its descendant strokes have drawn.
  const lit = litNodes(record.layout_tree, record.stroke_instances, frame, framesPerStroke);

  return (
    <AbsoluteFill style={{ background: "#ffffff" }}>
      <svg width={1280} height={720}>
        <g transform={`translate(40, 40)`}>
          <TreeLayout
            root={record.layout_tree}
            width={1200}
            height={640}
            renderNode={(n: LayoutNode) => (
              <g>
                <circle
                  r={10}
                  fill={lit.has(n.id) ? "#10b981" : "#cbd5e1"}
                  stroke="#475569"
                  strokeWidth={1}
                />
                <text x={14} y={4} fontSize={13} fontFamily="monospace">
                  {n.prototype_ref ?? n.id}
                </text>
                {n.mode ? <ModeIndicator mode={n.mode} x={14} y={14} /> : null}
                {n.input_adapter ? <InputAdapterChip adapter={n.input_adapter} x={14} y={34} /> : null}
              </g>
            )}
          />
        </g>
      </svg>
    </AbsoluteFill>
  );
};

function litNodes(
  root: LayoutNode,
  strokes: ReadonlyArray<{ instance_id: string }>,
  frame: number,
  framesPerStroke: number,
): Set<string> {
  // collect drawn instance_ids
  const drawn = new Set<string>();
  strokes.forEach((s, i) => {
    if (strokeProgress({ frame, strokeIndex: i, framesPerStroke }) >= 1) {
      drawn.add(s.instance_id);
    }
  });

  // walk layout tree bottom-up; a node is lit iff all descendant leaves are drawn
  const lit = new Set<string>();
  function dfs(n: LayoutNode): boolean {
    const kids = n.children ?? [];
    if (kids.length === 0) {
      if (drawn.has(n.id)) {
        lit.add(n.id);
        return true;
      }
      return false;
    }
    const allDrawn = kids.every(dfs);
    if (allDrawn) lit.add(n.id);
    return allDrawn;
  }
  dfs(root);
  return lit;
}
```

- [ ] **Step 2: Register composition**

In `Root.tsx`, add inside the `<>`:

```tsx
import { DecompositionTree } from "./compositions/DecompositionTree.js";
// ...
{SEED_CHARS.map((ch) => {
  const strokes = bundle.records[ch]?.stroke_instances.length ?? 8;
  const duration = totalStrokeFrames({ strokeCount: strokes, framesPerStroke: FRAMES_PER_STROKE }) + 30;
  return (
    <Composition
      key={`tree-${ch}`}
      id={`DecompositionTree-${ch}`}
      component={DecompositionTree}
      durationInFrames={duration}
      fps={30}
      width={1280}
      height={720}
      defaultProps={{ bundle, char: ch, framesPerStroke: FRAMES_PER_STROKE }}
    />
  );
})}
```

- [ ] **Step 3: Verify**

```bash
cd project/ts/apps/remotion-studio && pnpm typecheck
```

Expected: pass.

```bash
pnpm studio
```

Scrub `DecompositionTree-清` — nodes should light up bottom-up as strokes complete.

- [ ] **Step 4: Commit**

```bash
git add project/ts/apps/remotion-studio/src/compositions/DecompositionTree.tsx project/ts/apps/remotion-studio/src/Root.tsx
git commit -m "feat(remotion): DecompositionTree composition synced with stroke progress"
```

---

## Task 6: `PrototypeGraph` composition

**Files:**
- Create: `project/ts/apps/remotion-studio/src/compositions/PrototypeGraph.tsx`

- [ ] **Step 1: Implement (precomputed layout)**

```tsx
// project/ts/apps/remotion-studio/src/compositions/PrototypeGraph.tsx
import * as React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { GraphLayout, type GraphLink, type GraphNode } from "@olik/glyph-viz";
import type { GlyphBundle } from "@olik/glyph-loader";

export interface PrototypeGraphProps {
  bundle:     GlyphBundle;
  highlightChar?: string;
}

export const PrototypeGraph: React.FC<PrototypeGraphProps> = ({
  bundle, highlightChar,
}) => {
  const frame = useCurrentFrame();

  const protoIds = Object.keys(bundle.library.prototypes);
  // simple deterministic radial layout
  const cx = 640;
  const cy = 360;
  const r  = 220;
  const nodes: GraphNode[] = protoIds.map((id, i) => {
    const a = (i / protoIds.length) * Math.PI * 2;
    return { id, x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
  });

  // char ring around the outside
  const chars = Object.keys(bundle.records);
  const R = 340;
  const charNodes: GraphNode[] = chars.map((ch, i) => {
    const a = (i / chars.length) * Math.PI * 2 + Math.PI / chars.length;
    return { id: `char:${ch}`, x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) };
  });

  const links: GraphLink[] = [];
  for (const ch of chars) {
    const rec = bundle.records[ch];
    if (!rec) continue;
    const used = new Set<string>();
    for (const inst of rec.component_instances) used.add(inst.prototype_ref);
    for (const p of used) {
      links.push({ source: `char:${ch}`, target: p, kind: ch === highlightChar ? "highlight" : "used-by" });
    }
  }

  return (
    <AbsoluteFill style={{ background: "#ffffff" }}>
      <svg width={1280} height={720}>
        <GraphLayout
          nodes={[...nodes, ...charNodes]}
          links={links}
          linkColor="#cbd5e1"
          renderNode={(n) => {
            const isChar = n.id.startsWith("char:");
            if (isChar) {
              return (
                <text textAnchor="middle" dy={6} fontSize={28} fontFamily="serif"
                      fill={highlightChar && n.id === `char:${highlightChar}` ? "#10b981" : "#0f172a"}>
                  {n.id.slice(5)}
                </text>
              );
            }
            return (
              <>
                <circle r={14} fill="#f8fafc" stroke="#475569" />
                <text textAnchor="middle" dy={4} fontSize={11} fontFamily="monospace">
                  {bundle.library.prototypes[n.id]?.name ?? ""}
                </text>
              </>
            );
          }}
        />
      </svg>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Register**

Append in `Root.tsx`:

```tsx
import { PrototypeGraph } from "./compositions/PrototypeGraph.js";
// ...
<Composition
  id="PrototypeGraph"
  component={PrototypeGraph}
  durationInFrames={120}
  fps={30}
  width={1280}
  height={720}
  defaultProps={{ bundle, highlightChar: undefined }}
/>
```

- [ ] **Step 3: Verify in studio**

Open `PrototypeGraph` — should show a ring of prototypes with the 4 seed chars around them and edges marking usage.

- [ ] **Step 4: Commit**

```bash
git add project/ts/apps/remotion-studio/src/compositions/PrototypeGraph.tsx project/ts/apps/remotion-studio/src/Root.tsx
git commit -m "feat(remotion): PrototypeGraph composition (radial + char ring)"
```

---

## Task 7: `LayerZDepth` + `VirtualCoord` compositions

**Files:**
- Create: `project/ts/apps/remotion-studio/src/compositions/LayerZDepth.tsx`
- Create: `project/ts/apps/remotion-studio/src/compositions/VirtualCoord.tsx`

- [ ] **Step 1: `LayerZDepth`**

```tsx
// project/ts/apps/remotion-studio/src/compositions/LayerZDepth.tsx
import * as React from "react";
import { AbsoluteFill } from "remotion";
import { LayerStack } from "@olik/glyph-viz";
import type { GlyphBundle } from "@olik/glyph-loader";

export interface LayerZDepthProps {
  bundle: GlyphBundle;
  char:   string;
}

export const LayerZDepth: React.FC<LayerZDepthProps> = ({ bundle, char }) => {
  const record = bundle.records[char];
  if (!record) return null;
  return (
    <AbsoluteFill style={{ background: "#ffffff" }}>
      <svg width={1280} height={720}>
        <g transform={`translate(40, 40)`}>
          <LayerStack
            layers={record.render_layers}
            strokes={record.stroke_instances}
            panelHeight={120}
            panelWidth={180}
          />
        </g>
        <g transform={`translate(260, 40)`}>
          <text fontSize={32} fontFamily="serif">{char}</text>
          <text y={30} fontSize={13} fontFamily="monospace" fill="#64748b">
            render_layers × stroke_instances
          </text>
        </g>
      </svg>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: `VirtualCoord`**

```tsx
// project/ts/apps/remotion-studio/src/compositions/VirtualCoord.tsx
import * as React from "react";
import { AbsoluteFill } from "remotion";
import {
  AnchorBindingArrow, AnchorMarker, BBoxOverlay, StrokePath, VirtualCoordGrid,
} from "@olik/glyph-viz";
import type { GlyphBundle } from "@olik/glyph-loader";

export interface VirtualCoordProps {
  bundle: GlyphBundle;
  char:   string;
}

export const VirtualCoord: React.FC<VirtualCoordProps> = ({ bundle, char }) => {
  const record = bundle.records[char];
  if (!record) return null;

  const glyphSize = 640;
  return (
    <AbsoluteFill style={{ background: "#ffffff" }}>
      <svg width={1280} height={720}>
        <g transform={`translate(${(1280 - glyphSize) / 2}, 40) scale(${glyphSize / 1024})`}>
          <VirtualCoordGrid />
          {record.stroke_instances.map((s) => (
            <StrokePath
              key={s.id}
              outlinePath={s.path}
              median={s.median as Array<[number, number]>}
              progress={1}
            />
          ))}
          {record.component_instances.map((inst) => (
            inst.placed_bbox ? (
              <BBoxOverlay
                key={inst.id}
                bbox={inst.placed_bbox}
                label={inst.id}
                color="#0ea5e9"
                dashed
              />
            ) : null
          ))}
          {record.layout_tree.anchor_bindings?.map((ab, i) => {
            // best-effort: resolve anchor endpoints where possible, else skip
            // pass 1 layout-tree typically has none at root
            return null;
          })}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 3: Register both**

Append in `Root.tsx`:

```tsx
import { LayerZDepth } from "./compositions/LayerZDepth.js";
import { VirtualCoord } from "./compositions/VirtualCoord.js";
// ...
{SEED_CHARS.map((ch) => (
  <React.Fragment key={`extra-${ch}`}>
    <Composition
      id={`LayerZDepth-${ch}`}
      component={LayerZDepth}
      durationInFrames={90}
      fps={30}
      width={1280}
      height={720}
      defaultProps={{ bundle, char: ch }}
    />
    <Composition
      id={`VirtualCoord-${ch}`}
      component={VirtualCoord}
      durationInFrames={90}
      fps={30}
      width={1280}
      height={720}
      defaultProps={{ bundle, char: ch }}
    />
  </React.Fragment>
))}
```

- [ ] **Step 4: Commit**

```bash
git add project/ts/apps/remotion-studio/src/compositions/LayerZDepth.tsx project/ts/apps/remotion-studio/src/compositions/VirtualCoord.tsx project/ts/apps/remotion-studio/src/Root.tsx
git commit -m "feat(remotion): LayerZDepth + VirtualCoord compositions"
```

---

## Task 8: `Storyboard` meta-composition

**Files:**
- Create: `project/ts/apps/remotion-studio/src/compositions/Storyboard.tsx`

- [ ] **Step 1: Implement**

```tsx
// project/ts/apps/remotion-studio/src/compositions/Storyboard.tsx
import * as React from "react";
import { Sequence } from "remotion";
import type { GlyphBundle } from "@olik/glyph-loader";
import { CharacterAnim } from "./CharacterAnim.js";
import { DecompositionTree } from "./DecompositionTree.js";
import { LayerZDepth } from "./LayerZDepth.js";
import { PrototypeGraph } from "./PrototypeGraph.js";
import { VirtualCoord } from "./VirtualCoord.js";

export interface StoryboardProps {
  bundle:          GlyphBundle;
  chars:           readonly string[];
  framesPerStroke: number;
  sceneFrames:     number;  // frames per sub-composition scene
}

export const Storyboard: React.FC<StoryboardProps> = ({
  bundle, chars, framesPerStroke, sceneFrames,
}) => {
  let cursor = 0;
  const scenes: React.ReactNode[] = [];
  for (const ch of chars) {
    scenes.push(
      <Sequence key={`anim-${ch}`} from={cursor} durationInFrames={sceneFrames}>
        <CharacterAnim bundle={bundle} char={ch} framesPerStroke={framesPerStroke} />
      </Sequence>,
    );
    cursor += sceneFrames;
    scenes.push(
      <Sequence key={`tree-${ch}`} from={cursor} durationInFrames={sceneFrames}>
        <DecompositionTree bundle={bundle} char={ch} framesPerStroke={framesPerStroke} />
      </Sequence>,
    );
    cursor += sceneFrames;
    scenes.push(
      <Sequence key={`layer-${ch}`} from={cursor} durationInFrames={sceneFrames}>
        <LayerZDepth bundle={bundle} char={ch} />
      </Sequence>,
    );
    cursor += sceneFrames;
    scenes.push(
      <Sequence key={`coord-${ch}`} from={cursor} durationInFrames={sceneFrames}>
        <VirtualCoord bundle={bundle} char={ch} />
      </Sequence>,
    );
    cursor += sceneFrames;
  }
  scenes.push(
    <Sequence key="graph-final" from={cursor} durationInFrames={sceneFrames}>
      <PrototypeGraph bundle={bundle} />
    </Sequence>,
  );
  return <>{scenes}</>;
};
```

- [ ] **Step 2: Register**

Append in `Root.tsx`:

```tsx
import { Storyboard } from "./compositions/Storyboard.js";
// ...
<Composition
  id="Storyboard"
  component={Storyboard}
  durationInFrames={(SEED_CHARS.length * 4 + 1) * 90}  // 4 scenes per char @ 90 frames + final graph
  fps={30}
  width={1280}
  height={720}
  defaultProps={{
    bundle,
    chars: SEED_CHARS,
    framesPerStroke: FRAMES_PER_STROKE,
    sceneFrames: 90,
  }}
/>
```

- [ ] **Step 3: Verify**

```bash
cd project/ts/apps/remotion-studio && pnpm typecheck && pnpm studio
```

Expected: `Storyboard` composition visible; scrubbing shows scene transitions per char + final graph.

- [ ] **Step 4: Commit**

```bash
git add project/ts/apps/remotion-studio/src/compositions/Storyboard.tsx project/ts/apps/remotion-studio/src/Root.tsx
git commit -m "feat(remotion): Storyboard meta-composition stitching 4 chars"
```

---

## Task 9: Final verification + optional render

- [ ] **Step 1: Workspace test + typecheck**

```bash
cd project/ts && pnpm -r typecheck && pnpm -r test
```

Expected: pass across all packages + apps.

- [ ] **Step 2: Optional — render Storyboard to MP4**

Requires Plan 03 artifacts present.

```bash
cd project/ts/apps/remotion-studio && mkdir -p out && pnpm build
```

Expected: `out/storyboard.mp4` produced (a few minutes on first render). If any composition errors, the render aborts with a component stack; fix and retry.

- [ ] **Step 3: Tag**

```bash
git tag -a plan-06-remotion-studio -m "Plan 06 complete — Remotion Studio with 5 compositions + storyboard"
```

---

## Self-review

Coverage against spec § T6 + § Section 4.1–4.6:

- [x] CharacterAnim with animCJK idiom (Task 4) — § 4.1
- [x] DecompositionTree synced with strokes (Task 5) — § 4.2
- [x] PrototypeGraph with char ring (Task 6) — § 4.3
- [x] LayerZDepth exploded view (Task 7) — § 4.4
- [x] VirtualCoord overlay (Task 7) — § 4.5
- [x] Storyboard meta (Task 8) — § 4.6

## Follow-ups for later plans

- PrototypeGraph uses a deterministic radial layout; replace with force-directed in a future iteration for large libraries.
- Storyboard scene transitions are hard cuts; cross-fades belong to a polish pass.
- Rendering Storyboard on CI requires an OS with ffmpeg + chromium, tracked separately.
- Inspector (Plan 07) reuses many of these compositions' structures; keep props shapes aligned.

## Adjustments after execution

_Notes on FPS/duration tuning, prop-shape drift, or Remotion version upgrades found during implementation._
