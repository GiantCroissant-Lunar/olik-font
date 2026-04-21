---
title: "Plan 07 — xyflow Inspector (T5 flow-nodes + rule-viz, T7 inspector)"
created: 2026-04-21
tags: [type/plan, topic/scene-graph]
source: self
spec: "[[2026-04-21-glyph-scene-graph-solution-design]]"
status: draft
phase: 7
depends-on:
  - "[[2026-04-21-03-python-compose-cli]]"
  - "[[2026-04-21-05-ts-viz-primitives]]"
---

# Plan 07 — xyflow Inspector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship two packages (`@olik/flow-nodes`, `@olik/rule-viz`) and one app (`@olik/inspector`) — a Vite + React SPA with four xyflow-powered views: Decomposition Explorer, Prototype Library Browser, Rule Browser, Placement Debugger. Read-only in pass 1.

**Architecture:** xyflow `<ReactFlow>` hosts all four views. Custom node types (`flow-nodes`) wrap `@olik/glyph-viz` primitives inside xyflow `<Node>` bodies. Rule-specific node/edge types live in `rule-viz`. The inspector app is a thin shell: loads the bundle + rule-set once, routes between views via a top-nav tab switcher.

**Tech Stack:** @xyflow/react 12+, Vite 5+, React 18, TypeScript 5.6, vitest + @testing-library/react.

---

## File Structure

```
project/ts/
├── packages/
│   ├── flow-nodes/
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── tsup.config.ts
│   │   ├── vitest.config.ts
│   │   ├── src/
│   │   │   ├── index.ts
│   │   │   ├── prototype-node.tsx
│   │   │   ├── decomp-node.tsx
│   │   │   ├── placement-node.tsx
│   │   │   └── types.ts
│   │   └── test/
│   │       ├── prototype-node.test.tsx
│   │       └── decomp-node.test.tsx
│   └── rule-viz/
│       ├── package.json
│       ├── tsconfig.json
│       ├── tsup.config.ts
│       ├── vitest.config.ts
│       ├── src/
│       │   ├── index.ts
│       │   ├── rule-node.tsx
│       │   ├── precedence-edge.tsx
│       │   ├── trace-highlight.tsx
│       │   └── types.ts
│       └── test/
│           ├── rule-node.test.tsx
│           └── trace-highlight.test.ts
└── apps/
    └── inspector/
        ├── package.json
        ├── index.html
        ├── vite.config.ts
        ├── tsconfig.json
        ├── src/
        │   ├── main.tsx
        │   ├── App.tsx
        │   ├── state.tsx                 # bundle + rules + selection state (React context)
        │   ├── views/
        │   │   ├── DecompositionExplorer.tsx
        │   │   ├── PrototypeLibraryBrowser.tsx
        │   │   ├── RuleBrowser.tsx
        │   │   └── PlacementDebugger.tsx
        │   └── ui/
        │       ├── TopNav.tsx
        │       └── CharPicker.tsx
        └── test/
            ├── App.test.tsx
            └── views.test.tsx
```

---

## Task 1: Scaffold `@olik/flow-nodes`

**Files:**
- Create: `project/ts/packages/flow-nodes/package.json`
- Create: `project/ts/packages/flow-nodes/tsconfig.json`
- Create: `project/ts/packages/flow-nodes/tsup.config.ts`
- Create: `project/ts/packages/flow-nodes/vitest.config.ts`
- Create: `project/ts/packages/flow-nodes/src/index.ts`
- Create: `project/ts/packages/flow-nodes/src/types.ts`

- [ ] **Step 1: `package.json`**

```json
{
  "name": "@olik/flow-nodes",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "./dist/index.cjs",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": { "import": "./dist/index.js", "require": "./dist/index.cjs", "types": "./dist/index.d.ts" }
  },
  "files": ["dist"],
  "scripts": {
    "build":     "tsup",
    "test":      "vitest run",
    "typecheck": "tsc --noEmit"
  },
  "peerDependencies": {
    "@xyflow/react": ">=12",
    "react":         ">=18",
    "react-dom":     ">=18"
  },
  "dependencies": {
    "@olik/glyph-schema": "workspace:*",
    "@olik/glyph-viz":    "workspace:*"
  },
  "devDependencies": {
    "@testing-library/react": "16.0.1",
    "@types/react":           "18.3.11",
    "@types/react-dom":       "18.3.0",
    "@xyflow/react":          "12.3.5",
    "jsdom":                  "25.0.1",
    "react":                  "18.3.1",
    "react-dom":              "18.3.1",
    "tsup":                   "8.3.0",
    "typescript":             "5.6.3",
    "vitest":                 "2.1.2"
  }
}
```

- [ ] **Step 2: tsconfig / tsup / vitest configs** (same shape as Plan 05 Task 1)

```json
// tsconfig.json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "rootDir": "./src",
    "outDir": "./dist",
    "jsx": "react-jsx"
  },
  "include": ["src/**/*"]
}
```

```ts
// tsup.config.ts
import { defineConfig } from "tsup";
export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm", "cjs"],
  dts: true,
  clean: true,
  sourcemap: true,
  target: "es2022",
  external: ["react", "react-dom", "@xyflow/react"],
});
```

```ts
// vitest.config.ts
import { defineConfig } from "vitest/config";
export default defineConfig({
  test: { environment: "jsdom", globals: true },
  esbuild: { jsx: "automatic" },
});
```

- [ ] **Step 3: `src/types.ts`**

```ts
// project/ts/packages/flow-nodes/src/types.ts
import type { LayoutNode, Prototype } from "@olik/glyph-schema";

export interface PrototypeNodeData {
  prototype:      Prototype;
  instanceCount:  number;
  hostingChars:   readonly string[];
}

export interface DecompNodeData {
  char:        string;
  operator:    string | null;  // cjk-decomp operator letter
  components:  readonly string[];
  wouldMode?:  "keep" | "refine" | "replace";
  ruleId?:     string;
}

export interface PlacementNodeData {
  node: LayoutNode;
}

export const NODE_TYPE_KEYS = {
  prototype: "olik-prototype",
  decomp:    "olik-decomp",
  placement: "olik-placement",
} as const;
```

- [ ] **Step 4: `src/index.ts`**

```ts
// project/ts/packages/flow-nodes/src/index.ts
export * from "./types.js";
```

- [ ] **Step 5: Install + typecheck**

```bash
cd project/ts && pnpm install
cd packages/flow-nodes && pnpm typecheck
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add project/ts/packages/flow-nodes project/ts/pnpm-lock.yaml
git commit -m "chore(flow-nodes): scaffold package + shared data types"
```

---

## Task 2: `PrototypeNode` + `DecompNode` + `PlacementNode` components

**Files:**
- Create: `project/ts/packages/flow-nodes/src/prototype-node.tsx`
- Create: `project/ts/packages/flow-nodes/src/decomp-node.tsx`
- Create: `project/ts/packages/flow-nodes/src/placement-node.tsx`
- Create: `project/ts/packages/flow-nodes/test/prototype-node.test.tsx`
- Create: `project/ts/packages/flow-nodes/test/decomp-node.test.tsx`

- [ ] **Step 1: `prototype-node.tsx`**

```tsx
// project/ts/packages/flow-nodes/src/prototype-node.tsx
import * as React from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { StrokePath } from "@olik/glyph-viz";
import type { PrototypeNodeData } from "./types.js";

export const PrototypeNode: React.FC<NodeProps<{ data: PrototypeNodeData }>> = ({ data }) => {
  const { prototype, instanceCount, hostingChars } = data;
  return (
    <div
      style={{
        border: "1px solid #475569", background: "#ffffff", padding: 8,
        borderRadius: 6, width: 180, fontFamily: "system-ui, sans-serif",
      }}
    >
      <Handle type="target" position={Position.Left} />
      <div style={{ fontSize: 22, fontFamily: "serif" }}>{prototype.name}</div>
      <div style={{ fontSize: 10, color: "#64748b", fontFamily: "monospace" }}>{prototype.id}</div>
      <svg width={120} height={120} viewBox="0 0 1024 1024" style={{ display: "block", margin: "8px 0" }}>
        {prototype.strokes.map((s) => (
          <StrokePath
            key={s.id}
            outlinePath={s.path}
            median={s.median as Array<[number, number]>}
            progress={1}
            strokeWidth={48}
          />
        ))}
      </svg>
      <div style={{ fontSize: 11 }}>
        <div>uses: {instanceCount}</div>
        <div>chars: {hostingChars.join(" ")}</div>
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
};
```

- [ ] **Step 2: `decomp-node.tsx`**

```tsx
// project/ts/packages/flow-nodes/src/decomp-node.tsx
import * as React from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { ModeIndicator } from "@olik/glyph-viz";
import type { DecompNodeData } from "./types.js";

export const DecompNode: React.FC<NodeProps<{ data: DecompNodeData }>> = ({ data }) => {
  return (
    <div
      style={{
        border: "1px solid #0ea5e9", background: "#f0f9ff", padding: 8,
        borderRadius: 6, width: 140, fontFamily: "system-ui, sans-serif",
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div style={{ fontSize: 28, fontFamily: "serif", textAlign: "center" }}>{data.char}</div>
      <div style={{ fontSize: 11, color: "#64748b" }}>
        op: {data.operator ?? "atomic"}
      </div>
      {data.components.length > 0 ? (
        <div style={{ fontSize: 11 }}>→ {data.components.join(", ")}</div>
      ) : null}
      {data.wouldMode ? (
        <svg width={100} height={18}>
          <ModeIndicator mode={data.wouldMode} />
        </svg>
      ) : null}
      {data.ruleId ? (
        <div style={{ fontSize: 10, color: "#0ea5e9", fontFamily: "monospace" }}>{data.ruleId}</div>
      ) : null}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};
```

- [ ] **Step 3: `placement-node.tsx`**

```tsx
// project/ts/packages/flow-nodes/src/placement-node.tsx
import * as React from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { InputAdapterChip, ModeIndicator } from "@olik/glyph-viz";
import type { PlacementNodeData } from "./types.js";

export const PlacementNode: React.FC<NodeProps<{ data: PlacementNodeData }>> = ({ data }) => {
  const n = data.node;
  return (
    <div
      style={{
        border: "1px solid #a855f7", background: "#faf5ff", padding: 8,
        borderRadius: 6, width: 220, fontFamily: "system-ui, sans-serif",
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div style={{ fontSize: 12, fontFamily: "monospace", fontWeight: 600 }}>{n.id}</div>
      {n.prototype_ref ? (
        <div style={{ fontSize: 11, color: "#64748b" }}>{n.prototype_ref}</div>
      ) : null}
      {n.mode ? <svg width={120} height={18}><ModeIndicator mode={n.mode} /></svg> : null}
      {n.input_adapter ? <svg width={120} height={20}><InputAdapterChip adapter={n.input_adapter} /></svg> : null}
      <div style={{ fontSize: 10, fontFamily: "monospace", color: "#334155" }}>
        bbox: [{n.bbox.map((v) => Math.round(v)).join(", ")}]
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};
```

- [ ] **Step 4: Export from `index.ts`**

```ts
// project/ts/packages/flow-nodes/src/index.ts
export * from "./types.js";
export * from "./prototype-node.js";
export * from "./decomp-node.js";
export * from "./placement-node.js";
```

- [ ] **Step 5: Write tests**

```tsx
// project/ts/packages/flow-nodes/test/prototype-node.test.tsx
import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { ReactFlowProvider } from "@xyflow/react";
import { PrototypeNode } from "../src/prototype-node.js";
import type { Prototype } from "@olik/glyph-schema";

const proto: Prototype = {
  id: "proto:sun",
  name: "日",
  kind: "component",
  canonical_bbox: [0, 0, 1024, 1024],
  strokes: [{
    id: "s0", path: "M 0 0 L 1 0", median: [[0, 0], [1, 0]],
    order: 0, role: "horizontal",
  }],
  anchors: { center: [512, 512] },
  roles: ["meaning"],
  refinement: { mode: "keep", alternates: [] },
};

describe("PrototypeNode", () => {
  test("renders name + ID + host chars", () => {
    const { container } = render(
      <ReactFlowProvider>
        <PrototypeNode
          id="n1"
          data={{ prototype: proto, instanceCount: 2, hostingChars: ["明", "清"] }}
          type="olik-prototype"
          selected={false}
          zIndex={0}
          isConnectable
          xPos={0}
          yPos={0}
          dragging={false}
        />
      </ReactFlowProvider>,
    );
    expect(container.textContent).toContain("日");
    expect(container.textContent).toContain("proto:sun");
    expect(container.textContent).toContain("明");
    expect(container.textContent).toContain("清");
  });
});
```

```tsx
// project/ts/packages/flow-nodes/test/decomp-node.test.tsx
import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { ReactFlowProvider } from "@xyflow/react";
import { DecompNode } from "../src/decomp-node.js";

describe("DecompNode", () => {
  test("renders char + operator + components + rule id", () => {
    const { container } = render(
      <ReactFlowProvider>
        <DecompNode
          id="n1"
          data={{ char: "清", operator: "c", components: ["氵", "青"], wouldMode: "keep", ruleId: "decomp.use_extraction_plan" }}
          type="olik-decomp"
          selected={false}
          zIndex={0}
          isConnectable
          xPos={0}
          yPos={0}
          dragging={false}
        />
      </ReactFlowProvider>,
    );
    expect(container.textContent).toContain("清");
    expect(container.textContent).toContain("op: c");
    expect(container.textContent).toContain("氵");
    expect(container.textContent).toContain("青");
    expect(container.textContent).toContain("decomp.use_extraction_plan");
  });

  test("shows 'atomic' when operator is null", () => {
    const { container } = render(
      <ReactFlowProvider>
        <DecompNode
          id="n1"
          data={{ char: "日", operator: null, components: [] }}
          type="olik-decomp"
          selected={false}
          zIndex={0}
          isConnectable
          xPos={0}
          yPos={0}
          dragging={false}
        />
      </ReactFlowProvider>,
    );
    expect(container.textContent).toContain("op: atomic");
  });
});
```

- [ ] **Step 6: Run tests**

```bash
cd project/ts/packages/flow-nodes && pnpm test
```

Expected: `3 passed`.

- [ ] **Step 7: Commit**

```bash
git add project/ts/packages/flow-nodes/src project/ts/packages/flow-nodes/test
git commit -m "feat(flow-nodes): PrototypeNode + DecompNode + PlacementNode xyflow types"
```

---

## Task 3: Scaffold `@olik/rule-viz` + `RuleNode`

**Files:**
- Create: `project/ts/packages/rule-viz/package.json`
- Create: `project/ts/packages/rule-viz/tsconfig.json`
- Create: `project/ts/packages/rule-viz/tsup.config.ts`
- Create: `project/ts/packages/rule-viz/vitest.config.ts`
- Create: `project/ts/packages/rule-viz/src/types.ts`
- Create: `project/ts/packages/rule-viz/src/rule-node.tsx`
- Create: `project/ts/packages/rule-viz/src/trace-highlight.tsx`
- Create: `project/ts/packages/rule-viz/src/index.ts`
- Create: `project/ts/packages/rule-viz/test/rule-node.test.tsx`
- Create: `project/ts/packages/rule-viz/test/trace-highlight.test.ts`

- [ ] **Step 1: `package.json`** (same shape as flow-nodes, with these deps)

```json
{
  "name": "@olik/rule-viz",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "./dist/index.cjs",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": { ".": { "import": "./dist/index.js", "require": "./dist/index.cjs", "types": "./dist/index.d.ts" } },
  "files": ["dist"],
  "scripts": { "build": "tsup", "test": "vitest run", "typecheck": "tsc --noEmit" },
  "peerDependencies": { "@xyflow/react": ">=12", "react": ">=18", "react-dom": ">=18" },
  "dependencies": { "@olik/glyph-schema": "workspace:*" },
  "devDependencies": {
    "@testing-library/react": "16.0.1",
    "@types/react":           "18.3.11",
    "@types/react-dom":       "18.3.0",
    "@xyflow/react":          "12.3.5",
    "jsdom":                  "25.0.1",
    "react":                  "18.3.1",
    "react-dom":              "18.3.1",
    "tsup":                   "8.3.0",
    "typescript":             "5.6.3",
    "vitest":                 "2.1.2"
  }
}
```

tsconfig / tsup / vitest configs mirror the flow-nodes ones.

- [ ] **Step 2: `src/types.ts`**

```ts
// project/ts/packages/rule-viz/src/types.ts
import type { RuleTrace } from "@olik/glyph-schema";

export interface RuleNodeData {
  ruleId:    string;
  bucket:    "decomposition" | "composition" | "prototype_extraction";
  when:      Record<string, unknown>;
  action:    Record<string, unknown>;
  firedBy?:  readonly string[];  // decision_ids where this rule won
}

export type TraceHighlight = {
  firedRuleIds: Set<string>;
  alternativeRuleIds: Set<string>;
};

export function traceToHighlight(trace: RuleTrace): TraceHighlight {
  const fired = new Set<string>();
  const alts  = new Set<string>();
  for (const d of trace.decisions) {
    fired.add(d.rule_id);
    for (const a of d.alternatives) alts.add(a.rule_id);
  }
  return { firedRuleIds: fired, alternativeRuleIds: alts };
}
```

- [ ] **Step 3: `rule-node.tsx`**

```tsx
// project/ts/packages/rule-viz/src/rule-node.tsx
import * as React from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { RuleNodeData } from "./types.js";

const BUCKET_COLOR: Record<RuleNodeData["bucket"], string> = {
  decomposition:        "#0ea5e9",
  composition:          "#a855f7",
  prototype_extraction: "#d97706",
};

export const RuleNode: React.FC<NodeProps<{ data: RuleNodeData & { firedInView?: boolean; isAlternativeInView?: boolean } }>> = ({ data }) => {
  const color = BUCKET_COLOR[data.bucket];
  const bg = data.firedInView ? "#dcfce7" : data.isAlternativeInView ? "#fef3c7" : "#ffffff";
  const border = data.firedInView ? "#16a34a" : data.isAlternativeInView ? "#ca8a04" : color;
  return (
    <div style={{
      border: `2px solid ${border}`, background: bg, padding: 8,
      borderRadius: 6, width: 260, fontFamily: "system-ui, sans-serif",
    }}>
      <Handle type="target" position={Position.Top} />
      <div style={{ fontSize: 11, color, fontFamily: "monospace" }}>{data.bucket}</div>
      <div style={{ fontSize: 13, fontFamily: "monospace", fontWeight: 600 }}>{data.ruleId}</div>
      <div style={{ fontSize: 10, color: "#64748b", fontFamily: "monospace", marginTop: 4 }}>
        when: {JSON.stringify(data.when)}
      </div>
      <div style={{ fontSize: 10, color: "#64748b", fontFamily: "monospace" }}>
        → {JSON.stringify(data.action)}
      </div>
      {data.firedBy && data.firedBy.length > 0 ? (
        <div style={{ fontSize: 10, color: "#16a34a", marginTop: 4 }}>
          fired by: {data.firedBy.join(", ")}
        </div>
      ) : null}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};
```

- [ ] **Step 4: `trace-highlight.tsx`** (helper component for overlay)

```tsx
// project/ts/packages/rule-viz/src/trace-highlight.tsx
import * as React from "react";
import type { RuleTrace } from "@olik/glyph-schema";
import { traceToHighlight } from "./types.js";

export interface TraceHighlightSummaryProps {
  trace: RuleTrace;
}

export const TraceHighlightSummary: React.FC<TraceHighlightSummaryProps> = ({ trace }) => {
  const hi = traceToHighlight(trace);
  return (
    <div style={{ fontSize: 12, fontFamily: "monospace", padding: 8 }}>
      <div>decisions: {trace.decisions.length}</div>
      <div>fired: {[...hi.firedRuleIds].join(", ")}</div>
      <div>considered (not fired): {[...hi.alternativeRuleIds].join(", ") || "—"}</div>
    </div>
  );
};
```

- [ ] **Step 5: `index.ts`**

```ts
// project/ts/packages/rule-viz/src/index.ts
export * from "./types.js";
export * from "./rule-node.js";
export * from "./trace-highlight.js";
```

- [ ] **Step 6: Tests**

```ts
// project/ts/packages/rule-viz/test/trace-highlight.test.ts
import { describe, expect, test } from "vitest";
import { traceToHighlight } from "../src/types.js";

describe("traceToHighlight", () => {
  test("flattens fired + alternatives", () => {
    const hi = traceToHighlight({
      decisions: [
        { decision_id: "d:1", rule_id: "r1", inputs: {}, output: {},
          alternatives: [{ rule_id: "r2", would_output: {} }], applied_at: "t" },
        { decision_id: "d:2", rule_id: "r3", inputs: {}, output: {}, alternatives: [], applied_at: "t" },
      ],
    });
    expect([...hi.firedRuleIds].sort()).toEqual(["r1", "r3"]);
    expect([...hi.alternativeRuleIds]).toEqual(["r2"]);
  });
});
```

```tsx
// project/ts/packages/rule-viz/test/rule-node.test.tsx
import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { ReactFlowProvider } from "@xyflow/react";
import { RuleNode } from "../src/rule-node.js";

describe("RuleNode", () => {
  test("highlights when fired", () => {
    const { container } = render(
      <ReactFlowProvider>
        <RuleNode
          id="n"
          data={{
            ruleId: "compose.preset_from_plan",
            bucket: "composition",
            when: { has_preset_in_plan: true },
            action: { adapter: "preset" },
            firedInView: true,
          }}
          type="olik-rule"
          selected={false} zIndex={0} isConnectable
          xPos={0} yPos={0} dragging={false}
        />
      </ReactFlowProvider>,
    );
    const box = container.querySelector("div")!;
    expect(box.style.background).toBe("rgb(220, 252, 231)");
  });

  test("renders rule id + bucket + when/action", () => {
    const { container } = render(
      <ReactFlowProvider>
        <RuleNode
          id="n"
          data={{
            ruleId: "decomp.default_keep",
            bucket: "decomposition",
            when: {},
            action: { mode: "keep" },
          }}
          type="olik-rule"
          selected={false} zIndex={0} isConnectable
          xPos={0} yPos={0} dragging={false}
        />
      </ReactFlowProvider>,
    );
    expect(container.textContent).toContain("decomp.default_keep");
    expect(container.textContent).toContain("decomposition");
  });
});
```

- [ ] **Step 7: Install + run**

```bash
cd project/ts && pnpm install
cd packages/rule-viz && pnpm test
```

Expected: `3 passed`.

- [ ] **Step 8: Commit**

```bash
git add project/ts/packages/rule-viz project/ts/pnpm-lock.yaml
git commit -m "feat(rule-viz): RuleNode + trace highlight helpers"
```

---

## Task 4: Scaffold `@olik/inspector` (Vite + React)

**Files:**
- Create: `project/ts/apps/inspector/package.json`
- Create: `project/ts/apps/inspector/index.html`
- Create: `project/ts/apps/inspector/vite.config.ts`
- Create: `project/ts/apps/inspector/tsconfig.json`
- Create: `project/ts/apps/inspector/src/main.tsx`
- Create: `project/ts/apps/inspector/src/App.tsx`

- [ ] **Step 1: `package.json`**

```json
{
  "name": "@olik/inspector",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev":       "vite",
    "build":     "vite build",
    "preview":   "vite preview",
    "test":      "vitest run",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@olik/flow-nodes":   "workspace:*",
    "@olik/glyph-loader": "workspace:*",
    "@olik/glyph-schema": "workspace:*",
    "@olik/glyph-viz":    "workspace:*",
    "@olik/rule-viz":     "workspace:*",
    "@xyflow/react":      "12.3.5",
    "react":              "18.3.1",
    "react-dom":          "18.3.1"
  },
  "devDependencies": {
    "@testing-library/react": "16.0.1",
    "@types/react":           "18.3.11",
    "@types/react-dom":       "18.3.0",
    "@vitejs/plugin-react":   "4.3.2",
    "jsdom":                  "25.0.1",
    "typescript":             "5.6.3",
    "vite":                   "5.4.9",
    "vitest":                 "2.1.2"
  }
}
```

- [ ] **Step 2: `index.html`**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>olik Inspector</title>
  </head>
  <body style="margin:0">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 3: `vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  test: { environment: "jsdom", globals: true },
});
```

- [ ] **Step 4: `tsconfig.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "rootDir": "./src",
    "noEmit": true,
    "jsx": "react-jsx",
    "types": ["vitest/globals"]
  },
  "include": ["src/**/*", "test/**/*"]
}
```

- [ ] **Step 5: `src/main.tsx`**

```tsx
// project/ts/apps/inspector/src/main.tsx
import * as React from "react";
import { createRoot } from "react-dom/client";
import "@xyflow/react/dist/style.css";
import { App } from "./App.js";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 6: Minimal `App.tsx`**

```tsx
// project/ts/apps/inspector/src/App.tsx
import * as React from "react";

export const App: React.FC = () => {
  return (
    <div style={{ padding: 24, fontFamily: "system-ui, sans-serif" }}>
      <h1>olik Inspector</h1>
      <p>Views will load here once state + routing land.</p>
    </div>
  );
};
```

- [ ] **Step 7: Install + typecheck**

```bash
cd project/ts && pnpm install
cd apps/inspector && pnpm typecheck
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add project/ts/apps/inspector project/ts/pnpm-lock.yaml
git commit -m "chore(inspector): scaffold Vite+React SPA"
```

---

## Task 5: State + TopNav + CharPicker

**Files:**
- Create: `project/ts/apps/inspector/src/state.tsx`
- Create: `project/ts/apps/inspector/src/ui/TopNav.tsx`
- Create: `project/ts/apps/inspector/src/ui/CharPicker.tsx`

Inspector loads the bundle + rules.yaml once at startup via a React context. Data comes from `@olik/glyph-loader`'s `loadBundleFs` (Node) in a tiny dev server — but for the browser, we switch to URL-based loading of JSON served by Vite's `public/` dir. Pass 1 approach: **copy JSON records into `public/data/` at startup** via a small npm script, then fetch over HTTP.

- [ ] **Step 1: Add a prepare-data script**

Append to `project/ts/apps/inspector/package.json`'s `scripts`:

```json
"prepare-data": "mkdir -p public/data && cp ../../../schema/examples/*.json public/data/"
```

Full `scripts` block becomes:

```json
"scripts": {
  "prepare-data": "mkdir -p public/data && cp ../../../schema/examples/*.json public/data/",
  "dev":          "npm run prepare-data && vite",
  "build":        "npm run prepare-data && vite build",
  "preview":      "vite preview",
  "test":         "vitest run",
  "typecheck":    "tsc --noEmit"
}
```

- [ ] **Step 2: `state.tsx`**

```tsx
// project/ts/apps/inspector/src/state.tsx
import * as React from "react";
import {
  loadGlyphRecordUrl, loadPrototypeLibraryUrl, loadRuleTraceUrl,
} from "@olik/glyph-loader";
import type { GlyphRecord, PrototypeLibrary, RuleTrace } from "@olik/glyph-schema";

export type ViewKey = "decomposition" | "library" | "rules" | "placement";

export interface AppState {
  library:   PrototypeLibrary | null;
  records:   Record<string, GlyphRecord>;
  traces:    Record<string, RuleTrace>;
  char:      string;
  view:      ViewKey;
  loading:   boolean;
  error:     string | null;
}

export type AppAction =
  | { type: "loaded"; library: PrototypeLibrary; records: AppState["records"]; traces: AppState["traces"]; }
  | { type: "error"; message: string }
  | { type: "setChar"; char: string }
  | { type: "setView"; view: ViewKey };

export const SEED_CHARS = ["明", "清", "國", "森"] as const;

const initial: AppState = {
  library: null, records: {}, traces: {},
  char: "明", view: "decomposition", loading: true, error: null,
};

function reducer(s: AppState, a: AppAction): AppState {
  switch (a.type) {
    case "loaded":  return { ...s, library: a.library, records: a.records, traces: a.traces, loading: false };
    case "error":   return { ...s, loading: false, error: a.message };
    case "setChar": return { ...s, char: a.char };
    case "setView": return { ...s, view: a.view };
  }
}

const Ctx = React.createContext<[AppState, React.Dispatch<AppAction>] | null>(null);

export const AppStateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = React.useReducer(reducer, initial);

  React.useEffect(() => {
    (async () => {
      try {
        const library = await loadPrototypeLibraryUrl("/data/prototype-library.json");
        const records: AppState["records"] = {};
        const traces:  AppState["traces"]  = {};
        for (const ch of SEED_CHARS) {
          records[ch] = await loadGlyphRecordUrl(`/data/glyph-record-${ch}.json`);
          traces[ch]  = await loadRuleTraceUrl(`/data/rule-trace-${ch}.json`);
        }
        dispatch({ type: "loaded", library, records, traces });
      } catch (e) {
        dispatch({ type: "error", message: (e as Error).message });
      }
    })();
  }, []);

  return <Ctx.Provider value={[state, dispatch]}>{children}</Ctx.Provider>;
};

export function useAppState(): [AppState, React.Dispatch<AppAction>] {
  const ctx = React.useContext(Ctx);
  if (!ctx) throw new Error("useAppState outside AppStateProvider");
  return ctx;
}
```

- [ ] **Step 3: `ui/TopNav.tsx`**

```tsx
// project/ts/apps/inspector/src/ui/TopNav.tsx
import * as React from "react";
import { useAppState, type ViewKey } from "../state.js";

const VIEWS: Array<{ key: ViewKey; label: string }> = [
  { key: "decomposition", label: "Decomposition Explorer" },
  { key: "library",       label: "Prototype Library" },
  { key: "rules",         label: "Rule Browser" },
  { key: "placement",     label: "Placement Debugger" },
];

export const TopNav: React.FC = () => {
  const [state, dispatch] = useAppState();
  return (
    <nav style={{ display: "flex", gap: 8, padding: 12, borderBottom: "1px solid #cbd5e1" }}>
      {VIEWS.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => dispatch({ type: "setView", view: key })}
          style={{
            padding: "6px 12px",
            background: state.view === key ? "#0ea5e9" : "transparent",
            color:      state.view === key ? "#fff" : "#0f172a",
            border: "1px solid #0ea5e9", borderRadius: 4, cursor: "pointer",
          }}
        >
          {label}
        </button>
      ))}
    </nav>
  );
};
```

- [ ] **Step 4: `ui/CharPicker.tsx`**

```tsx
// project/ts/apps/inspector/src/ui/CharPicker.tsx
import * as React from "react";
import { SEED_CHARS, useAppState } from "../state.js";

export const CharPicker: React.FC = () => {
  const [state, dispatch] = useAppState();
  return (
    <div style={{ display: "flex", gap: 8, padding: 8 }}>
      {SEED_CHARS.map((ch) => (
        <button
          key={ch}
          onClick={() => dispatch({ type: "setChar", char: ch })}
          style={{
            fontSize: 24, fontFamily: "serif",
            padding: "4px 12px",
            background: state.char === ch ? "#fef3c7" : "#fff",
            border: "1px solid #cbd5e1", borderRadius: 4, cursor: "pointer",
          }}
        >
          {ch}
        </button>
      ))}
    </div>
  );
};
```

- [ ] **Step 5: Rewire `App.tsx`**

```tsx
// project/ts/apps/inspector/src/App.tsx
import * as React from "react";
import { AppStateProvider, useAppState } from "./state.js";
import { TopNav } from "./ui/TopNav.js";
import { CharPicker } from "./ui/CharPicker.js";

const Body: React.FC = () => {
  const [state] = useAppState();
  if (state.loading) return <div style={{ padding: 24 }}>loading…</div>;
  if (state.error)   return <div style={{ padding: 24, color: "#dc2626" }}>error: {state.error}</div>;
  return (
    <div>
      <CharPicker />
      <div style={{ padding: 24 }}>
        view <code>{state.view}</code>, char <code>{state.char}</code> (views land in Task 6)
      </div>
    </div>
  );
};

export const App: React.FC = () => (
  <AppStateProvider>
    <div style={{ fontFamily: "system-ui, sans-serif" }}>
      <TopNav />
      <Body />
    </div>
  </AppStateProvider>
);
```

- [ ] **Step 6: Run dev**

```bash
cd project/ts/apps/inspector && pnpm dev
```

Expected: browser opens to `http://localhost:5173`, tabs switch, char picker highlights. If Plan 03 records exist in `public/data/`, "loading…" clears; otherwise an error message shows (acceptable in pass 1).

Stop dev server (Ctrl-C).

- [ ] **Step 7: Commit**

```bash
git add project/ts/apps/inspector
git commit -m "feat(inspector): AppState + TopNav + CharPicker shell"
```

---

## Task 6: Four views

**Files:**
- Create: `project/ts/apps/inspector/src/views/DecompositionExplorer.tsx`
- Create: `project/ts/apps/inspector/src/views/PrototypeLibraryBrowser.tsx`
- Create: `project/ts/apps/inspector/src/views/RuleBrowser.tsx`
- Create: `project/ts/apps/inspector/src/views/PlacementDebugger.tsx`

Each view is a `<ReactFlow>` instance configured with the appropriate node types. Layouts are simple (dagre-style precomputation or hand-laid); force-directed layout is a deferred enhancement.

- [ ] **Step 1: `DecompositionExplorer.tsx`**

```tsx
// project/ts/apps/inspector/src/views/DecompositionExplorer.tsx
import * as React from "react";
import { ReactFlow, type Edge, type Node } from "@xyflow/react";
import { DecompNode, NODE_TYPE_KEYS } from "@olik/flow-nodes";
import type { LayoutNode } from "@olik/glyph-schema";
import { useAppState } from "../state.js";

const nodeTypes = { [NODE_TYPE_KEYS.decomp]: DecompNode };

export const DecompositionExplorer: React.FC = () => {
  const [state] = useAppState();
  const record = state.records[state.char];
  if (!record) return <div style={{ padding: 24 }}>no record for {state.char}</div>;

  const { nodes, edges } = layoutTreeToFlow(record.layout_tree, record.glyph_id);

  return (
    <div style={{ height: "calc(100vh - 160px)" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
      />
    </div>
  );
};

function layoutTreeToFlow(root: LayoutNode, rootChar: string): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // BFS-level layout: depth as y, sibling index as x
  const levels = new Map<number, LayoutNode[]>();
  (function index(n: LayoutNode, depth: number) {
    const arr = levels.get(depth) ?? [];
    arr.push(n);
    levels.set(depth, arr);
    (n.children ?? []).forEach((c) => index(c, depth + 1));
  })(root, 0);

  const dx = 220;
  const dy = 140;
  const positions = new Map<string, { x: number; y: number }>();
  for (const [depth, arr] of levels.entries()) {
    const start = -((arr.length - 1) * dx) / 2;
    arr.forEach((n, i) => positions.set(n.id, { x: 640 + start + i * dx, y: 60 + depth * dy }));
  }

  (function build(n: LayoutNode, parentId: string | null) {
    const pos = positions.get(n.id)!;
    const isRoot = parentId === null;
    const label = isRoot ? rootChar : n.prototype_ref?.replace("proto:", "") ?? n.id;
    nodes.push({
      id: n.id,
      position: pos,
      type: NODE_TYPE_KEYS.decomp,
      data: {
        char: label,
        operator: (n.decomp_source as { operator?: string } | undefined)?.operator ?? null,
        components: (n.children ?? []).map((c) =>
          (c.prototype_ref?.replace("proto:", "") ?? c.id),
        ),
        wouldMode: n.mode,
        ruleId: n.input_adapter,
      },
    });
    if (parentId) {
      edges.push({ id: `${parentId}->${n.id}`, source: parentId, target: n.id });
    }
    (n.children ?? []).forEach((c) => build(c, n.id));
  })(root, null);

  return { nodes, edges };
}
```

- [ ] **Step 2: `PrototypeLibraryBrowser.tsx`**

```tsx
// project/ts/apps/inspector/src/views/PrototypeLibraryBrowser.tsx
import * as React from "react";
import { ReactFlow, type Edge, type Node } from "@xyflow/react";
import { NODE_TYPE_KEYS, PrototypeNode } from "@olik/flow-nodes";
import { useAppState } from "../state.js";

const nodeTypes = { [NODE_TYPE_KEYS.prototype]: PrototypeNode };

export const PrototypeLibraryBrowser: React.FC = () => {
  const [state] = useAppState();
  if (!state.library) return <div style={{ padding: 24 }}>no library</div>;

  const protoIds = Object.keys(state.library.prototypes);
  const usageCount = new Map<string, number>();
  const hostingChars = new Map<string, Set<string>>();
  for (const [ch, rec] of Object.entries(state.records)) {
    for (const inst of rec.component_instances) {
      usageCount.set(inst.prototype_ref, (usageCount.get(inst.prototype_ref) ?? 0) + 1);
      const set = hostingChars.get(inst.prototype_ref) ?? new Set<string>();
      set.add(ch);
      hostingChars.set(inst.prototype_ref, set);
    }
  }

  const cols = 4;
  const dx = 220, dy = 280;
  const nodes: Node[] = protoIds.map((id, i) => ({
    id,
    position: { x: 60 + (i % cols) * dx, y: 60 + Math.floor(i / cols) * dy },
    type: NODE_TYPE_KEYS.prototype,
    data: {
      prototype: state.library!.prototypes[id]!,
      instanceCount: usageCount.get(id) ?? 0,
      hostingChars: [...(hostingChars.get(id) ?? [])],
    },
  }));

  const edges: Edge[] = [];  // pass 1 library has no refines-to edges

  return (
    <div style={{ height: "calc(100vh - 160px)" }}>
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView />
    </div>
  );
};
```

- [ ] **Step 3: `RuleBrowser.tsx`**

For pass 1, the Rule Browser reads `rules.yaml` via HTTP (we copy it into `public/data/` alongside records). Since YAML parsing in the browser would pull `js-yaml` just for this, we instead ship a **rules.json** alongside rules.yaml; the CLI emits it.

Update Plan 03's CLI to ALSO emit `rules.json` as a side output:
- _(deferred to this plan's adjustments unless Plan 03 already does so; otherwise: inspector falls back to a hand-maintained `public/data/rules.json` mirroring `rules.yaml`)_

For cleanliness, add the CLI step here as a tiny Plan-03 amendment:

_Append to `project/py/src/olik_font/cli.py`'s `build` handler, right after writing `prototype-library.json`:_

```python
import yaml
rules_yaml_path = args.rules
rules_obj = yaml.safe_load(rules_yaml_path.read_text(encoding="utf-8"))
(out / "rules.json").write_text(
    json.dumps(rules_obj, ensure_ascii=False, indent=2), encoding="utf-8",
)
```

Re-run `olik build 明 清 國 森 -o project/schema/examples` after the edit.

Then the inspector view:

```tsx
// project/ts/apps/inspector/src/views/RuleBrowser.tsx
import * as React from "react";
import { ReactFlow, type Edge, type Node } from "@xyflow/react";
import { RuleNode, traceToHighlight } from "@olik/rule-viz";
import { useAppState } from "../state.js";

interface RulesJson {
  decomposition:        Array<{ id: string; when: Record<string, unknown>; action: Record<string, unknown> }>;
  composition:          Array<{ id: string; when: Record<string, unknown>; action: Record<string, unknown> }>;
  prototype_extraction: Array<{ id: string; when: Record<string, unknown>; action: Record<string, unknown> }>;
}

const nodeTypes = { "olik-rule": RuleNode };

export const RuleBrowser: React.FC = () => {
  const [state] = useAppState();
  const [rules, setRules] = React.useState<RulesJson | null>(null);

  React.useEffect(() => {
    fetch("/data/rules.json").then((r) => r.json()).then(setRules).catch(() => setRules(null));
  }, []);

  if (!rules) return <div style={{ padding: 24 }}>load rules.json (re-run <code>olik build</code>)</div>;

  const trace = state.traces[state.char];
  const highlight = trace ? traceToHighlight(trace) : { firedRuleIds: new Set<string>(), alternativeRuleIds: new Set<string>() };

  const buckets: Array<[keyof RulesJson, number]> = [
    ["decomposition",        60],
    ["composition",          60 + 320],
    ["prototype_extraction", 60 + 640],
  ];
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  for (const [bucket, x] of buckets) {
    rules[bucket].forEach((r, i) => {
      const id = `${bucket}:${r.id}`;
      nodes.push({
        id,
        position: { x, y: 60 + i * 160 },
        type: "olik-rule",
        data: {
          ruleId: r.id,
          bucket,
          when: r.when,
          action: r.action,
          firedInView: highlight.firedRuleIds.has(r.id),
          isAlternativeInView: highlight.alternativeRuleIds.has(r.id),
        },
      });
      if (i > 0) {
        edges.push({ id: `${bucket}-fallback-${i}`, source: `${bucket}:${rules[bucket][i - 1]!.id}`, target: id });
      }
    });
  }

  return (
    <div style={{ height: "calc(100vh - 160px)" }}>
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView />
    </div>
  );
};
```

- [ ] **Step 4: `PlacementDebugger.tsx`**

```tsx
// project/ts/apps/inspector/src/views/PlacementDebugger.tsx
import * as React from "react";
import { ReactFlow, type Edge, type Node } from "@xyflow/react";
import { NODE_TYPE_KEYS, PlacementNode } from "@olik/flow-nodes";
import type { LayoutNode } from "@olik/glyph-schema";
import { useAppState } from "../state.js";

const nodeTypes = { [NODE_TYPE_KEYS.placement]: PlacementNode };

export const PlacementDebugger: React.FC = () => {
  const [state] = useAppState();
  const record = state.records[state.char];
  if (!record) return <div style={{ padding: 24 }}>no record for {state.char}</div>;

  const { nodes, edges } = toFlow(record.layout_tree);

  return (
    <div style={{ height: "calc(100vh - 160px)" }}>
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView />
    </div>
  );
};

function toFlow(root: LayoutNode): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const levels = new Map<number, LayoutNode[]>();
  (function index(n: LayoutNode, depth: number) {
    const arr = levels.get(depth) ?? [];
    arr.push(n);
    levels.set(depth, arr);
    (n.children ?? []).forEach((c) => index(c, depth + 1));
  })(root, 0);

  const dx = 260, dy = 180;
  const positions = new Map<string, { x: number; y: number }>();
  for (const [depth, arr] of levels.entries()) {
    const start = -((arr.length - 1) * dx) / 2;
    arr.forEach((n, i) => positions.set(n.id, { x: 640 + start + i * dx, y: 60 + depth * dy }));
  }

  (function build(n: LayoutNode, parentId: string | null) {
    nodes.push({
      id: n.id,
      position: positions.get(n.id)!,
      type: NODE_TYPE_KEYS.placement,
      data: { node: n },
    });
    if (parentId) edges.push({ id: `${parentId}->${n.id}`, source: parentId, target: n.id });
    (n.children ?? []).forEach((c) => build(c, n.id));
  })(root, null);

  return { nodes, edges };
}
```

- [ ] **Step 5: Wire views into `App.tsx`'s Body**

Replace the placeholder Body in `App.tsx`:

```tsx
const Body: React.FC = () => {
  const [state] = useAppState();
  if (state.loading) return <div style={{ padding: 24 }}>loading…</div>;
  if (state.error)   return <div style={{ padding: 24, color: "#dc2626" }}>error: {state.error}</div>;
  return (
    <div>
      <CharPicker />
      {state.view === "decomposition" ? <DecompositionExplorer /> : null}
      {state.view === "library"       ? <PrototypeLibraryBrowser /> : null}
      {state.view === "rules"         ? <RuleBrowser /> : null}
      {state.view === "placement"     ? <PlacementDebugger /> : null}
    </div>
  );
};
```

Plus the imports at the top of `App.tsx`:

```tsx
import { DecompositionExplorer }   from "./views/DecompositionExplorer.js";
import { PrototypeLibraryBrowser } from "./views/PrototypeLibraryBrowser.js";
import { RuleBrowser }             from "./views/RuleBrowser.js";
import { PlacementDebugger }       from "./views/PlacementDebugger.js";
```

- [ ] **Step 6: Run dev, verify each tab**

```bash
cd project/ts/apps/inspector && pnpm dev
```

Expected: each of the four tabs renders an xyflow canvas with relevant nodes + edges for each selected char. If `rules.json` isn't in `public/data/`, the Rule Browser shows a hint; re-run the Plan 03 CLI after adding the emitter (Task 6 Step 3).

Stop (Ctrl-C).

- [ ] **Step 7: Commit**

```bash
git add project/ts/apps/inspector/src/views project/ts/apps/inspector/src/App.tsx
git commit -m "feat(inspector): four views — decomposition/library/rules/placement"
```

---

## Task 7: Integration smoke test

**Files:**
- Create: `project/ts/apps/inspector/test/App.test.tsx`

- [ ] **Step 1: Write a shallow render test**

```tsx
// project/ts/apps/inspector/test/App.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { App } from "../src/App.js";

// mock loader module so tests don't need HTTP
vi.mock("@olik/glyph-loader", () => ({
  loadGlyphRecordUrl:      vi.fn(async () => ({ glyph_id: "明" })),
  loadPrototypeLibraryUrl: vi.fn(async () => ({ prototypes: {} })),
  loadRuleTraceUrl:        vi.fn(async () => ({ decisions: [] })),
}));

describe("App", () => {
  test("renders top nav", async () => {
    render(<App />);
    expect(await screen.findByText("Decomposition Explorer")).toBeTruthy();
    expect(screen.getByText("Prototype Library")).toBeTruthy();
    expect(screen.getByText("Rule Browser")).toBeTruthy();
    expect(screen.getByText("Placement Debugger")).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run**

```bash
cd project/ts/apps/inspector && pnpm test
```

Expected: `1 passed`.

- [ ] **Step 3: Commit**

```bash
git add project/ts/apps/inspector/test/App.test.tsx
git commit -m "test(inspector): App renders TopNav with all four view tabs"
```

---

## Task 8: Final verification + tag

- [ ] **Step 1: Workspace build + test**

```bash
cd project/ts && pnpm -r build && pnpm -r test
```

Expected: all plans' packages + apps build and test cleanly.

- [ ] **Step 2: Tag**

```bash
git tag -a plan-07-inspector -m "Plan 07 complete — xyflow Inspector with 4 views"
```

- [ ] **Step 3: Pass-1 complete tag**

```bash
git tag -a pass-1-complete -m "Pass 1 complete — all 7 plans executed; 4 seed chars reconstructed + rendered + inspected"
```

---

## Self-review

Coverage against spec § T5 + § T7 + § Section 4B (Inspector views 1–4):

- [x] `@olik/flow-nodes` with PrototypeNode, DecompNode, PlacementNode (Tasks 1, 2) — T5 ✓
- [x] `@olik/rule-viz` with RuleNode + trace highlight helpers (Task 3) — T5 ✓
- [x] `@olik/inspector` Vite + React SPA (Tasks 4, 5) — T7 ✓
- [x] Decomposition Explorer view (Task 6.1) — § 4B.1
- [x] Prototype Library Browser (Task 6.2) — § 4B.2
- [x] Rule Browser with trace overlay (Task 6.3) — § 4B.3
- [x] Placement Debugger (Task 6.4) — § 4B.4
- [x] `rules.json` emission tacked onto Plan 03 CLI (Task 6.3) — D15 addendum

All 4 inspector views ship read-only per D17.

## Follow-ups for later phases

- Inspector edits that round-trip to `extraction_plan.yaml` / `rules.yaml` (deferred; per D17).
- Force-directed or dagre layout for views 2 and 3 (currently grid-layout).
- Click-through from PrototypeLibraryBrowser → PlacementDebugger filtered by prototype.
- Diff mode for two rule sets.
- Time-travel replay of rule firings.

## Adjustments after execution

_Record Vite config tweaks, xyflow version upgrades, or view interaction changes discovered during implementation._
