---
title: "Plan 04 — TS foundation (T2 glyph-schema, T3 glyph-loader)"
created: 2026-04-21
tags: [type/plan, topic/scene-graph]
source: self
spec: "[[2026-04-21-glyph-scene-graph-solution-design]]"
status: draft
phase: 4
depends-on: "[[2026-04-21-01-foundation]]"
---

# Plan 04 — TS foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two shipped pnpm packages: `@olik/glyph-schema` (TS types + zod validators mirroring the JSON schemas from Plan 01) and `@olik/glyph-loader` (fs + URL loaders that validate on load). Downstream packages (Plan 05, 06, 07) depend on these.

**Architecture:** Both packages are dual-purpose ESM libraries compiled with `tsup` to both ESM + CJS + `.d.ts`. Zod is the runtime validator; TS types are inferred from zod schemas via `z.infer`. Loader is framework-agnostic (uses `fs/promises` in Node and `fetch` in browsers via a small runtime shim).

**Tech Stack:** TypeScript 5.6+, zod 3.23+, vitest 2+, tsup 8+, pnpm 9+.

---

## File Structure

```
project/ts/
├── packages/
│   ├── glyph-schema/
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── tsup.config.ts
│   │   ├── src/
│   │   │   ├── index.ts                   # public barrel
│   │   │   ├── coord-space.ts
│   │   │   ├── affine.ts
│   │   │   ├── prototype.ts
│   │   │   ├── prototype-library.ts
│   │   │   ├── constraint.ts
│   │   │   ├── layout-tree.ts
│   │   │   ├── stroke-instance.ts
│   │   │   ├── glyph-record.ts
│   │   │   └── rule-trace.ts
│   │   └── test/
│   │       ├── glyph-record.test.ts
│   │       ├── prototype-library.test.ts
│   │       └── rule-trace.test.ts
│   └── glyph-loader/
│       ├── package.json
│       ├── tsconfig.json
│       ├── tsup.config.ts
│       ├── src/
│       │   ├── index.ts
│       │   ├── load-fs.ts
│       │   ├── load-url.ts
│       │   └── bundle.ts                  # composite: load library + records together
│       └── test/
│           ├── load-fs.test.ts
│           └── bundle.test.ts
```

---

## Task 1: Scaffold `@olik/glyph-schema`

**Files:**
- Create: `project/ts/packages/glyph-schema/package.json`
- Create: `project/ts/packages/glyph-schema/tsconfig.json`
- Create: `project/ts/packages/glyph-schema/tsup.config.ts`
- Create: `project/ts/packages/glyph-schema/src/index.ts`

- [ ] **Step 1: Create `package.json`**

```json
{
  "name": "@olik/glyph-schema",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "./dist/index.cjs",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.js",
      "require": "./dist/index.cjs",
      "types": "./dist/index.d.ts"
    }
  },
  "files": ["dist"],
  "scripts": {
    "build":     "tsup",
    "dev":       "tsup --watch",
    "test":      "vitest run",
    "test:watch":"vitest",
    "typecheck": "tsc --noEmit",
    "lint":      "eslint src --max-warnings 0"
  },
  "dependencies": {
    "zod": "3.23.8"
  },
  "devDependencies": {
    "tsup":       "8.3.0",
    "typescript": "5.6.3",
    "vitest":     "2.1.2"
  }
}
```

- [ ] **Step 2: Create `tsconfig.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "rootDir": "./src",
    "outDir": "./dist"
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 3: Create `tsup.config.ts`**

```ts
import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm", "cjs"],
  dts: true,
  clean: true,
  sourcemap: true,
  target: "es2022",
});
```

- [ ] **Step 4: Create `src/index.ts` placeholder**

```ts
// project/ts/packages/glyph-schema/src/index.ts
export const SCHEMA_VERSION = "0.1";
```

- [ ] **Step 5: Install + verify**

```bash
cd project/ts && pnpm install
cd packages/glyph-schema && pnpm build && pnpm typecheck
```

Expected: `dist/` populated with ESM + CJS + `.d.ts`; `typecheck` passes.

- [ ] **Step 6: Commit**

```bash
git add project/ts/packages/glyph-schema/package.json project/ts/packages/glyph-schema/tsconfig.json project/ts/packages/glyph-schema/tsup.config.ts project/ts/packages/glyph-schema/src/index.ts project/ts/pnpm-lock.yaml
git commit -m "chore(ts): scaffold @olik/glyph-schema package"
```

---

## Task 2: Coord space + affine zod schemas

**Files:**
- Create: `project/ts/packages/glyph-schema/src/coord-space.ts`
- Create: `project/ts/packages/glyph-schema/src/affine.ts`

- [ ] **Step 1: Implement coord-space**

```ts
// project/ts/packages/glyph-schema/src/coord-space.ts
import { z } from "zod";

export const CoordSpace = z.object({
  width:  z.literal(1024),
  height: z.literal(1024),
  origin: z.literal("top-left"),
  y_axis: z.literal("down"),
}).strict();

export type CoordSpace = z.infer<typeof CoordSpace>;

export const CANONICAL_COORD_SPACE: CoordSpace = {
  width: 1024,
  height: 1024,
  origin: "top-left",
  y_axis: "down",
};

export const Point = z.tuple([z.number(), z.number()]);
export type Point = z.infer<typeof Point>;

export const BBox = z.tuple([z.number(), z.number(), z.number(), z.number()]);
export type BBox = z.infer<typeof BBox>;
```

- [ ] **Step 2: Implement affine**

```ts
// project/ts/packages/glyph-schema/src/affine.ts
import { z } from "zod";
import { Point } from "./coord-space.js";

export const Affine = z.object({
  translate: Point,
  scale:     Point,
  rotate:    z.number(),
  shear:     Point,
}).strict();

export type Affine = z.infer<typeof Affine>;

export const IDENTITY_AFFINE: Affine = {
  translate: [0, 0],
  scale:     [1, 1],
  rotate:    0,
  shear:     [0, 0],
};
```

- [ ] **Step 3: Wire into `index.ts`**

```ts
// project/ts/packages/glyph-schema/src/index.ts
export const SCHEMA_VERSION = "0.1";

export * from "./coord-space.js";
export * from "./affine.js";
```

- [ ] **Step 4: Typecheck**

```bash
cd project/ts/packages/glyph-schema && pnpm typecheck
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add project/ts/packages/glyph-schema/src/coord-space.ts project/ts/packages/glyph-schema/src/affine.ts project/ts/packages/glyph-schema/src/index.ts
git commit -m "feat(glyph-schema): coord-space + affine zod schemas"
```

---

## Task 3: Prototype + prototype-library zod schemas

**Files:**
- Create: `project/ts/packages/glyph-schema/src/prototype.ts`
- Create: `project/ts/packages/glyph-schema/src/prototype-library.ts`
- Create: `project/ts/packages/glyph-schema/test/prototype-library.test.ts`

- [ ] **Step 1: Implement prototype**

```ts
// project/ts/packages/glyph-schema/src/prototype.ts
import { z } from "zod";
import { BBox, Point } from "./coord-space.js";

export const StrokeRole = z.enum([
  "horizontal", "vertical", "dot", "hook",
  "slash", "backslash", "fold", "other",
]);
export type StrokeRole = z.infer<typeof StrokeRole>;

export const DongChineseRole = z.enum([
  "meaning", "sound", "iconic", "distinguishing", "unknown",
]);
export type DongChineseRole = z.infer<typeof DongChineseRole>;

export const RefinementMode = z.enum(["keep", "refine", "replace"]);
export type RefinementMode = z.infer<typeof RefinementMode>;

export const Stroke = z.object({
  id:     z.string(),
  path:   z.string(),
  median: z.array(Point),
  order:  z.number().int().min(0),
  role:   StrokeRole,
}).strict();
export type Stroke = z.infer<typeof Stroke>;

export const Prototype = z.object({
  id:             z.string().regex(/^proto:[A-Za-z0-9_]+$/),
  name:           z.string(),
  kind:           z.enum(["component", "stroke", "group"]),
  source:         z.record(z.unknown()).optional(),
  canonical_bbox: BBox,
  strokes:        z.array(Stroke),
  anchors:        z.record(Point),
  roles:          z.array(DongChineseRole).optional(),
  refinement: z.object({
    mode:       RefinementMode,
    alternates: z.array(z.string()).optional(),
  }),
}).strict();
export type Prototype = z.infer<typeof Prototype>;
```

- [ ] **Step 2: Implement prototype-library**

```ts
// project/ts/packages/glyph-schema/src/prototype-library.ts
import { z } from "zod";
import { CoordSpace } from "./coord-space.js";
import { Prototype } from "./prototype.js";

export const LibraryEdge = z.object({
  from: z.string(),
  kind: z.enum(["refines-to", "replaces"]),
  to:   z.string(),
}).strict();
export type LibraryEdge = z.infer<typeof LibraryEdge>;

export const PrototypeLibrary = z.object({
  schema_version: z.string().regex(/^\d+\.\d+(\.\d+)?$/),
  coord_space:    CoordSpace,
  prototypes:     z.record(z.string().regex(/^proto:[A-Za-z0-9_]+$/), Prototype),
  edges:          z.array(LibraryEdge).optional(),
}).strict();
export type PrototypeLibrary = z.infer<typeof PrototypeLibrary>;
```

- [ ] **Step 3: Wire exports**

```ts
// project/ts/packages/glyph-schema/src/index.ts
export const SCHEMA_VERSION = "0.1";

export * from "./coord-space.js";
export * from "./affine.js";
export * from "./prototype.js";
export * from "./prototype-library.js";
```

- [ ] **Step 4: Write failing test**

```ts
// project/ts/packages/glyph-schema/test/prototype-library.test.ts
import { describe, expect, test } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { PrototypeLibrary } from "../src/prototype-library.js";

const exampleHello = resolve(
  __dirname, "../../../../schema/examples/hello-library.json",
);

describe("PrototypeLibrary", () => {
  test("hello example validates", () => {
    const raw = JSON.parse(readFileSync(exampleHello, "utf-8"));
    const parsed = PrototypeLibrary.parse(raw);
    expect(parsed.prototypes["proto:hello"].name).toBe("hello");
  });

  test("rejects library missing coord_space", () => {
    const raw: Record<string, unknown> = JSON.parse(readFileSync(exampleHello, "utf-8"));
    delete raw.coord_space;
    expect(() => PrototypeLibrary.parse(raw)).toThrow();
  });

  test("rejects prototype whose id doesn't match proto: pattern", () => {
    const raw = JSON.parse(readFileSync(exampleHello, "utf-8"));
    raw.prototypes["bogus"] = raw.prototypes["proto:hello"];
    expect(() => PrototypeLibrary.parse(raw)).toThrow();
  });

  test("infers Prototype type with TS", () => {
    const raw = JSON.parse(readFileSync(exampleHello, "utf-8"));
    const parsed = PrototypeLibrary.parse(raw);
    const proto = parsed.prototypes["proto:hello"];
    // Compile-time shape assertion; this block fails typecheck if Prototype changes.
    const _canonical: [number, number, number, number] = proto.canonical_bbox;
    expect(_canonical).toHaveLength(4);
  });
});
```

- [ ] **Step 5: Run test**

```bash
cd project/ts/packages/glyph-schema && pnpm test
```

Expected: `4 passed`.

- [ ] **Step 6: Commit**

```bash
git add project/ts/packages/glyph-schema/src/prototype.ts project/ts/packages/glyph-schema/src/prototype-library.ts project/ts/packages/glyph-schema/src/index.ts project/ts/packages/glyph-schema/test/prototype-library.test.ts
git commit -m "feat(glyph-schema): Prototype + PrototypeLibrary zod schemas"
```

---

## Task 4: Constraint + layout-tree + stroke-instance + glyph-record schemas

**Files:**
- Create: `project/ts/packages/glyph-schema/src/constraint.ts`
- Create: `project/ts/packages/glyph-schema/src/layout-tree.ts`
- Create: `project/ts/packages/glyph-schema/src/stroke-instance.ts`
- Create: `project/ts/packages/glyph-schema/src/glyph-record.ts`
- Create: `project/ts/packages/glyph-schema/test/glyph-record.test.ts`

- [ ] **Step 1: Constraint discriminated union**

```ts
// project/ts/packages/glyph-schema/src/constraint.ts
import { z } from "zod";

export const AlignX = z.object({
  kind: z.literal("align_x"),
  targets: z.array(z.string()),
}).strict();

export const AlignY = z.object({
  kind: z.literal("align_y"),
  targets: z.array(z.string()),
}).strict();

export const OrderX = z.object({
  kind: z.literal("order_x"),
  before: z.string(),
  after:  z.string(),
}).strict();

export const OrderY = z.object({
  kind: z.literal("order_y"),
  above: z.string(),
  below: z.string(),
}).strict();

export const AnchorDistance = z.object({
  kind: z.literal("anchor_distance"),
  from: z.string(),
  to:   z.string(),
  value: z.number(),
}).strict();

export const Inside = z.object({
  kind: z.literal("inside"),
  target:  z.string(),
  frame:   z.string(),
  padding: z.number(),
}).strict();

export const AvoidOverlap = z.object({
  kind: z.literal("avoid_overlap"),
  a: z.string(),
  b: z.string(),
  padding: z.number(),
}).strict();

export const Repeat = z.object({
  kind: z.literal("repeat"),
  prototype_ref: z.string(),
  count:         z.number().int(),
  layout_hint:   z.string(),
}).strict();

export const Constraint = z.discriminatedUnion("kind", [
  AlignX, AlignY, OrderX, OrderY, AnchorDistance, Inside, AvoidOverlap, Repeat,
]);
export type Constraint = z.infer<typeof Constraint>;
```

- [ ] **Step 2: Layout-tree (recursive)**

```ts
// project/ts/packages/glyph-schema/src/layout-tree.ts
import { z } from "zod";
import { Affine } from "./affine.js";
import { BBox } from "./coord-space.js";
import { RefinementMode } from "./prototype.js";

export const AnchorBinding = z.object({
  from:     z.string(),
  to:       z.string(),
  distance: z.number().optional(),
}).strict();
export type AnchorBinding = z.infer<typeof AnchorBinding>;

const baseNode = z.object({
  id:              z.string(),
  prototype_ref:   z.string().regex(/^proto:[A-Za-z0-9_]+$/).optional(),
  bbox:            BBox,
  mode:            RefinementMode.optional(),
  depth:           z.number().int().min(0).optional(),
  transform:       Affine.optional(),
  anchor_bindings: z.array(AnchorBinding).optional(),
  decomp_source:   z.record(z.unknown()).optional(),
  input_adapter:   z.string().optional(),
}).strict();

export type LayoutNode = z.infer<typeof baseNode> & { children?: LayoutNode[] };

export const LayoutNode: z.ZodType<LayoutNode> = baseNode.extend({
  children: z.lazy(() => z.array(LayoutNode).optional()),
});
```

- [ ] **Step 3: Stroke instance**

```ts
// project/ts/packages/glyph-schema/src/stroke-instance.ts
import { z } from "zod";
import { BBox, Point } from "./coord-space.js";

export const StrokeInstance = z.object({
  id:          z.string(),
  instance_id: z.string(),
  order:       z.number().int().min(0),
  path:        z.string(),
  median:      z.array(Point),
  bbox:        BBox,
  z:           z.number().int().min(0).max(99),
  role:        z.string(),
}).strict();
export type StrokeInstance = z.infer<typeof StrokeInstance>;
```

- [ ] **Step 4: Glyph record**

```ts
// project/ts/packages/glyph-schema/src/glyph-record.ts
import { z } from "zod";
import { Affine } from "./affine.js";
import { Constraint } from "./constraint.js";
import { CoordSpace } from "./coord-space.js";
import { LayoutNode } from "./layout-tree.js";
import { DongChineseRole } from "./prototype.js";
import { StrokeInstance } from "./stroke-instance.js";

export const ComponentInstance = z.object({
  id:            z.string(),
  prototype_ref: z.string().regex(/^proto:[A-Za-z0-9_]+$/),
  transform:     Affine,
  placed_bbox:   z.tuple([z.number(), z.number(), z.number(), z.number()]).optional(),
  style_slots:   z.record(z.unknown()).optional(),
}).strict();
export type ComponentInstance = z.infer<typeof ComponentInstance>;

export const RenderLayer = z.object({
  name:  z.string(),
  z_min: z.number().int().min(0).max(99),
  z_max: z.number().int().min(0).max(99),
}).strict();
export type RenderLayer = z.infer<typeof RenderLayer>;

export const IouReport = z.object({
  mean: z.number(),
  min:  z.number(),
  per_stroke: z.record(z.number()).optional(),
  note: z.string().optional(),
}).passthrough();
export type IouReport = z.infer<typeof IouReport>;

export const GlyphRecord = z.object({
  schema_version: z.string().regex(/^\d+\.\d+(\.\d+)?$/),
  glyph_id:       z.string().min(1),
  unicode:        z.string().regex(/^U\+[0-9A-F]{4,6}$/).optional(),
  coord_space:    CoordSpace,
  source:         z.record(z.unknown()).optional(),
  layout_tree:    LayoutNode,
  component_instances: z.array(ComponentInstance),
  stroke_instances:    z.array(StrokeInstance),
  constraints:    z.array(Constraint),
  render_layers:  z.array(RenderLayer),
  roles: z.record(z.object({
    dong_chinese: DongChineseRole.optional(),
  }).passthrough()),
  metadata: z.object({
    generated_at: z.string().optional(),
    generator:    z.string().optional(),
    iou_report:   IouReport.optional(),
  }).passthrough(),
}).strict();
export type GlyphRecord = z.infer<typeof GlyphRecord>;
```

- [ ] **Step 5: Wire exports**

Append to `src/index.ts`:

```ts
export * from "./constraint.js";
export * from "./layout-tree.js";
export * from "./stroke-instance.js";
export * from "./glyph-record.js";
```

- [ ] **Step 6: Write failing glyph-record test**

```ts
// project/ts/packages/glyph-schema/test/glyph-record.test.ts
import { describe, expect, test } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { GlyphRecord } from "../src/glyph-record.js";

const helloPath = resolve(__dirname, "../../../../schema/examples/hello-record.json");

describe("GlyphRecord", () => {
  test("hello example validates", () => {
    const raw = JSON.parse(readFileSync(helloPath, "utf-8"));
    const parsed = GlyphRecord.parse(raw);
    expect(parsed.glyph_id).toBe("hello");
  });

  test("rejects record missing render_layers", () => {
    const raw = JSON.parse(readFileSync(helloPath, "utf-8"));
    delete raw.render_layers;
    expect(() => GlyphRecord.parse(raw)).toThrow();
  });

  test("discriminated union accepts a left_right-style constraint list", () => {
    const raw = JSON.parse(readFileSync(helloPath, "utf-8"));
    raw.constraints = [
      { kind: "align_y", targets: ["inst:a.center", "inst:b.center"] },
      { kind: "order_x", before: "inst:a", after: "inst:b" },
      { kind: "anchor_distance", from: "inst:a.right_edge", to: "inst:b.left_edge", value: 20 },
    ];
    const parsed = GlyphRecord.parse(raw);
    expect(parsed.constraints).toHaveLength(3);
  });

  test("rejects unknown constraint kind", () => {
    const raw = JSON.parse(readFileSync(helloPath, "utf-8"));
    raw.constraints = [{ kind: "not_a_constraint" }];
    expect(() => GlyphRecord.parse(raw)).toThrow();
  });
});
```

- [ ] **Step 7: Run test**

```bash
cd project/ts/packages/glyph-schema && pnpm test
```

Expected: `8 passed` (4 library + 4 record).

- [ ] **Step 8: Commit**

```bash
git add project/ts/packages/glyph-schema/src/constraint.ts project/ts/packages/glyph-schema/src/layout-tree.ts project/ts/packages/glyph-schema/src/stroke-instance.ts project/ts/packages/glyph-schema/src/glyph-record.ts project/ts/packages/glyph-schema/src/index.ts project/ts/packages/glyph-schema/test/glyph-record.test.ts
git commit -m "feat(glyph-schema): constraint union + layout-tree + stroke-instance + glyph-record"
```

---

## Task 5: Rule-trace zod schema

**Files:**
- Create: `project/ts/packages/glyph-schema/src/rule-trace.ts`
- Create: `project/ts/packages/glyph-schema/test/rule-trace.test.ts`

- [ ] **Step 1: Implement rule-trace**

```ts
// project/ts/packages/glyph-schema/src/rule-trace.ts
import { z } from "zod";

export const RuleTraceAlternative = z.object({
  rule_id:      z.string(),
  would_output: z.record(z.unknown()),
}).strict();

export const RuleTraceEntry = z.object({
  decision_id:  z.string(),
  rule_id:      z.string(),
  inputs:       z.record(z.unknown()),
  output:       z.record(z.unknown()),
  alternatives: z.array(RuleTraceAlternative),
  applied_at:   z.string(),
}).strict();
export type RuleTraceEntry = z.infer<typeof RuleTraceEntry>;

export const RuleTrace = z.object({
  decisions: z.array(RuleTraceEntry),
}).strict();
export type RuleTrace = z.infer<typeof RuleTrace>;
```

- [ ] **Step 2: Wire export**

Append to `src/index.ts`:

```ts
export * from "./rule-trace.js";
```

- [ ] **Step 3: Write failing test**

```ts
// project/ts/packages/glyph-schema/test/rule-trace.test.ts
import { describe, expect, test } from "vitest";
import { RuleTrace } from "../src/rule-trace.js";

describe("RuleTrace", () => {
  test("parses a minimal trace", () => {
    const raw = {
      decisions: [
        {
          decision_id: "d:明:composition",
          rule_id: "compose.preset_from_plan",
          inputs: { has_preset_in_plan: true, preset: "left_right" },
          output: { adapter: "preset" },
          alternatives: [],
          applied_at: "2026-04-21T00:00:00Z",
        },
      ],
    };
    const parsed = RuleTrace.parse(raw);
    expect(parsed.decisions).toHaveLength(1);
    expect(parsed.decisions[0].rule_id).toBe("compose.preset_from_plan");
  });

  test("rejects missing applied_at", () => {
    const raw = {
      decisions: [
        {
          decision_id: "d:test",
          rule_id: "x",
          inputs: {},
          output: {},
          alternatives: [],
        },
      ],
    };
    expect(() => RuleTrace.parse(raw)).toThrow();
  });
});
```

- [ ] **Step 4: Run test**

```bash
cd project/ts/packages/glyph-schema && pnpm test
```

Expected: `10 passed`.

- [ ] **Step 5: Build package**

```bash
cd project/ts/packages/glyph-schema && pnpm build
```

Expected: `dist/index.js`, `dist/index.cjs`, `dist/index.d.ts` produced.

- [ ] **Step 6: Commit**

```bash
git add project/ts/packages/glyph-schema/src/rule-trace.ts project/ts/packages/glyph-schema/src/index.ts project/ts/packages/glyph-schema/test/rule-trace.test.ts
git commit -m "feat(glyph-schema): RuleTrace zod schema"
```

---

## Task 6: Validate against Plan 03's real outputs

**Files:**
- Create: `project/ts/packages/glyph-schema/test/real-records.test.ts`

This task only runs meaningfully after Plan 03's `olik build` has produced real records. If they're absent, tests are skipped.

- [ ] **Step 1: Write the test**

```ts
// project/ts/packages/glyph-schema/test/real-records.test.ts
import { describe, expect, test } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { GlyphRecord } from "../src/glyph-record.js";
import { PrototypeLibrary } from "../src/prototype-library.js";
import { RuleTrace } from "../src/rule-trace.js";

const EXAMPLES = resolve(__dirname, "../../../../schema/examples");
const SEED = ["明", "清", "國", "森"] as const;

describe.runIf(existsSync(resolve(EXAMPLES, "prototype-library.json")))(
  "validates real CLI outputs",
  () => {
    test("prototype-library.json validates", () => {
      const raw = JSON.parse(readFileSync(resolve(EXAMPLES, "prototype-library.json"), "utf-8"));
      const parsed = PrototypeLibrary.parse(raw);
      // pass-1 produces 7 prototypes (per extraction_plan.yaml in Plan 02)
      expect(Object.keys(parsed.prototypes).length).toBeGreaterThanOrEqual(7);
    });

    for (const ch of SEED) {
      test(`glyph-record-${ch}.json validates`, () => {
        const path = resolve(EXAMPLES, `glyph-record-${ch}.json`);
        if (!existsSync(path)) return;
        const raw = JSON.parse(readFileSync(path, "utf-8"));
        const parsed = GlyphRecord.parse(raw);
        expect(parsed.glyph_id).toBe(ch);
        expect(parsed.stroke_instances.length).toBeGreaterThan(0);
      });

      test(`rule-trace-${ch}.json validates`, () => {
        const path = resolve(EXAMPLES, `rule-trace-${ch}.json`);
        if (!existsSync(path)) return;
        const raw = JSON.parse(readFileSync(path, "utf-8"));
        const parsed = RuleTrace.parse(raw);
        expect(parsed.decisions.length).toBeGreaterThan(0);
      });
    }
  },
);
```

- [ ] **Step 2: Run**

```bash
cd project/ts/packages/glyph-schema && pnpm test
```

Expected: real-records tests pass if Plan 03 has been executed; skipped otherwise.

- [ ] **Step 3: Commit**

```bash
git add project/ts/packages/glyph-schema/test/real-records.test.ts
git commit -m "test(glyph-schema): validate real records from Plan 03 output"
```

---

## Task 7: Scaffold `@olik/glyph-loader`

**Files:**
- Create: `project/ts/packages/glyph-loader/package.json`
- Create: `project/ts/packages/glyph-loader/tsconfig.json`
- Create: `project/ts/packages/glyph-loader/tsup.config.ts`
- Create: `project/ts/packages/glyph-loader/src/index.ts`

- [ ] **Step 1: `package.json`**

```json
{
  "name": "@olik/glyph-loader",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "./dist/index.cjs",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.js",
      "require": "./dist/index.cjs",
      "types": "./dist/index.d.ts"
    }
  },
  "files": ["dist"],
  "scripts": {
    "build":     "tsup",
    "dev":       "tsup --watch",
    "test":      "vitest run",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@olik/glyph-schema": "workspace:*",
    "zod": "3.23.8"
  },
  "devDependencies": {
    "tsup":       "8.3.0",
    "typescript": "5.6.3",
    "vitest":     "2.1.2"
  }
}
```

- [ ] **Step 2: `tsconfig.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "rootDir": "./src",
    "outDir": "./dist",
    "types": ["node"]
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 3: `tsup.config.ts`**

```ts
import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm", "cjs"],
  dts: true,
  clean: true,
  sourcemap: true,
  target: "es2022",
});
```

- [ ] **Step 4: Placeholder `src/index.ts`**

```ts
// project/ts/packages/glyph-loader/src/index.ts
export const GLYPH_LOADER_VERSION = "0.1.0";
```

- [ ] **Step 5: Install + verify**

```bash
cd project/ts && pnpm install
cd packages/glyph-loader && pnpm typecheck
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add project/ts/packages/glyph-loader/package.json project/ts/packages/glyph-loader/tsconfig.json project/ts/packages/glyph-loader/tsup.config.ts project/ts/packages/glyph-loader/src/index.ts project/ts/pnpm-lock.yaml
git commit -m "chore(ts): scaffold @olik/glyph-loader package"
```

---

## Task 8: fs loader

**Files:**
- Create: `project/ts/packages/glyph-loader/src/load-fs.ts`
- Create: `project/ts/packages/glyph-loader/test/load-fs.test.ts`

- [ ] **Step 1: Write failing test**

```ts
// project/ts/packages/glyph-loader/test/load-fs.test.ts
import { describe, expect, test } from "vitest";
import { resolve } from "node:path";
import { existsSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { loadGlyphRecord, loadPrototypeLibrary, loadRuleTrace } from "../src/load-fs.js";

const EXAMPLES = resolve(__dirname, "../../../../schema/examples");

describe("load-fs", () => {
  test("loads hello-library.json", async () => {
    const path = resolve(EXAMPLES, "hello-library.json");
    const lib = await loadPrototypeLibrary(path);
    expect(lib.prototypes["proto:hello"]).toBeDefined();
  });

  test("loads hello-record.json", async () => {
    const path = resolve(EXAMPLES, "hello-record.json");
    const rec = await loadGlyphRecord(path);
    expect(rec.glyph_id).toBe("hello");
  });

  test("throws on validation failure", async () => {
    const dir = mkdtempSync(resolve(tmpdir(), "olik-test-"));
    const bad = resolve(dir, "bad.json");
    writeFileSync(bad, JSON.stringify({ glyph_id: "x" }));  // missing required fields
    await expect(loadGlyphRecord(bad)).rejects.toThrow();
  });

  test("throws when file doesn't exist", async () => {
    await expect(loadGlyphRecord("/nonexistent")).rejects.toThrow();
  });

  test("loads a real rule trace if CLI has been run", async () => {
    const path = resolve(EXAMPLES, "rule-trace-明.json");
    if (!existsSync(path)) return;
    const trace = await loadRuleTrace(path);
    expect(trace.decisions.length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: Implement `load-fs.ts`**

```ts
// project/ts/packages/glyph-loader/src/load-fs.ts
import { readFile } from "node:fs/promises";
import {
  GlyphRecord, PrototypeLibrary, RuleTrace,
  type GlyphRecord as GlyphRecordT,
  type PrototypeLibrary as PrototypeLibraryT,
  type RuleTrace as RuleTraceT,
} from "@olik/glyph-schema";

export async function loadGlyphRecord(path: string): Promise<GlyphRecordT> {
  const raw = await readFile(path, "utf-8");
  const parsed = JSON.parse(raw);
  return GlyphRecord.parse(parsed);
}

export async function loadPrototypeLibrary(path: string): Promise<PrototypeLibraryT> {
  const raw = await readFile(path, "utf-8");
  const parsed = JSON.parse(raw);
  return PrototypeLibrary.parse(parsed);
}

export async function loadRuleTrace(path: string): Promise<RuleTraceT> {
  const raw = await readFile(path, "utf-8");
  const parsed = JSON.parse(raw);
  return RuleTrace.parse(parsed);
}
```

- [ ] **Step 3: Wire exports**

```ts
// project/ts/packages/glyph-loader/src/index.ts
export const GLYPH_LOADER_VERSION = "0.1.0";
export * from "./load-fs.js";
```

- [ ] **Step 4: Run test**

```bash
cd project/ts/packages/glyph-loader && pnpm test
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add project/ts/packages/glyph-loader/src/load-fs.ts project/ts/packages/glyph-loader/src/index.ts project/ts/packages/glyph-loader/test/load-fs.test.ts
git commit -m "feat(glyph-loader): fs loaders for record/library/trace"
```

---

## Task 9: URL loader + bundle helper

**Files:**
- Create: `project/ts/packages/glyph-loader/src/load-url.ts`
- Create: `project/ts/packages/glyph-loader/src/bundle.ts`
- Create: `project/ts/packages/glyph-loader/test/bundle.test.ts`

- [ ] **Step 1: Implement URL loader**

```ts
// project/ts/packages/glyph-loader/src/load-url.ts
import {
  GlyphRecord, PrototypeLibrary, RuleTrace,
  type GlyphRecord as GlyphRecordT,
  type PrototypeLibrary as PrototypeLibraryT,
  type RuleTrace as RuleTraceT,
} from "@olik/glyph-schema";

async function fetchJson(url: string | URL): Promise<unknown> {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`fetch ${url}: ${resp.status} ${resp.statusText}`);
  }
  return await resp.json();
}

export async function loadGlyphRecordUrl(url: string | URL): Promise<GlyphRecordT> {
  return GlyphRecord.parse(await fetchJson(url));
}

export async function loadPrototypeLibraryUrl(url: string | URL): Promise<PrototypeLibraryT> {
  return PrototypeLibrary.parse(await fetchJson(url));
}

export async function loadRuleTraceUrl(url: string | URL): Promise<RuleTraceT> {
  return RuleTrace.parse(await fetchJson(url));
}
```

- [ ] **Step 2: Implement bundle composite**

```ts
// project/ts/packages/glyph-loader/src/bundle.ts
import { resolve } from "node:path";
import type { GlyphRecord, PrototypeLibrary, RuleTrace } from "@olik/glyph-schema";
import { loadGlyphRecord, loadPrototypeLibrary, loadRuleTrace } from "./load-fs.js";

export interface GlyphBundle {
  library: PrototypeLibrary;
  records: Record<string, GlyphRecord>;
  traces:  Record<string, RuleTrace>;
}

export async function loadBundleFs(
  examplesDir: string,
  chars: readonly string[],
): Promise<GlyphBundle> {
  const library = await loadPrototypeLibrary(resolve(examplesDir, "prototype-library.json"));
  const records: Record<string, GlyphRecord> = {};
  const traces:  Record<string, RuleTrace> = {};
  for (const ch of chars) {
    const rec = resolve(examplesDir, `glyph-record-${ch}.json`);
    const trc = resolve(examplesDir, `rule-trace-${ch}.json`);
    records[ch] = await loadGlyphRecord(rec);
    traces[ch]  = await loadRuleTrace(trc);
  }
  return { library, records, traces };
}
```

- [ ] **Step 3: Wire exports**

Append to `src/index.ts`:

```ts
export * from "./load-url.js";
export * from "./bundle.js";
export type { GlyphBundle } from "./bundle.js";
```

- [ ] **Step 4: Write test**

```ts
// project/ts/packages/glyph-loader/test/bundle.test.ts
import { describe, expect, test } from "vitest";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { loadBundleFs } from "../src/bundle.js";

const EXAMPLES = resolve(__dirname, "../../../../schema/examples");

describe.runIf(existsSync(resolve(EXAMPLES, "prototype-library.json")))(
  "loadBundleFs",
  () => {
    test("loads all 4 seed records + library + traces", async () => {
      const chars = ["明", "清", "國", "森"] as const;
      const bundle = await loadBundleFs(EXAMPLES, chars);
      expect(Object.keys(bundle.library.prototypes).length).toBeGreaterThanOrEqual(7);
      for (const ch of chars) {
        expect(bundle.records[ch].glyph_id).toBe(ch);
        expect(bundle.traces[ch].decisions.length).toBeGreaterThan(0);
      }
    });

    test("missing file throws", async () => {
      await expect(loadBundleFs(EXAMPLES, ["not-a-char"])).rejects.toThrow();
    });
  },
);
```

- [ ] **Step 5: Run**

```bash
cd project/ts/packages/glyph-loader && pnpm test
```

Expected: `7 passed` (5 load-fs + 2 bundle, or bundle skipped if Plan 03 not run).

- [ ] **Step 6: Build both packages**

```bash
cd project/ts && pnpm -r --filter "@olik/glyph-schema" --filter "@olik/glyph-loader" build
```

Expected: `dist/` populated in both packages.

- [ ] **Step 7: Commit**

```bash
git add project/ts/packages/glyph-loader/src/load-url.ts project/ts/packages/glyph-loader/src/bundle.ts project/ts/packages/glyph-loader/src/index.ts project/ts/packages/glyph-loader/test/bundle.test.ts
git commit -m "feat(glyph-loader): URL loader + bundle composite"
```

---

## Task 10: Final verification + tag

- [ ] **Step 1: Workspace-wide test run**

```bash
cd project/ts && pnpm -r test
```

Expected: all tests pass; count ≥ 12 across both packages (real-records + bundle tests may skip if Plan 03 hasn't run).

- [ ] **Step 2: Workspace-wide build**

```bash
cd project/ts && pnpm -r build
```

Expected: both packages build cleanly.

- [ ] **Step 3: Tag**

```bash
git tag -a plan-04-ts-foundation -m "Plan 04 complete — @olik/glyph-schema + glyph-loader"
```

---

## Self-review

Coverage against spec §§ T2, T3:

- [x] `@olik/glyph-schema` package with zod schemas for coord_space, affine, prototype, prototype-library, constraint, layout-tree, stroke-instance, glyph-record, rule-trace (Tasks 1–5) — T2 ✓
- [x] Validation against hand-crafted examples + real CLI outputs (Tasks 3, 4, 5, 6) — T2 ✓
- [x] `@olik/glyph-loader` fs + URL + bundle loaders (Tasks 7–9) — T3 ✓

## Follow-ups for later plans

- Plan 05 (viz primitives) imports types from `@olik/glyph-schema` for its component props.
- Plan 06 (Remotion) uses `@olik/glyph-loader`'s `loadBundleFs` during `delayRender`.
- Plan 07 (Inspector) uses both packages.

## Adjustments after execution

_Record any schema tweaks that surfaced while consuming real Plan 03 outputs._
