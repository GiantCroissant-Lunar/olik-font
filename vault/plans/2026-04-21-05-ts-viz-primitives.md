---
title: "Plan 05 — TS viz primitives (T4 glyph-viz)"
created: 2026-04-21
tags: [type/plan, topic/scene-graph]
source: self
spec: "[[2026-04-21-glyph-scene-graph-solution-design]]"
status: draft
phase: 5
depends-on: "[[2026-04-21-04-ts-foundation]]"
---

# Plan 05 — TS viz primitives Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `@olik/glyph-viz` — a framework-neutral React/SVG primitive package consumed by Remotion (Plan 06) and Inspector (Plan 07). All components accept validated types from `@olik/glyph-schema`; none depend on Remotion or xyflow.

**Architecture:** Small, focused React components, each in its own file. SVG-first; components render into the caller's `<svg>` root. Animation props accept a progress value (0..1) so Remotion and Inspector can drive the timeline differently. Tree layout uses `d3-hierarchy`; graph layout accepts pre-computed node positions (force-directed layout is the caller's job — keeps the primitive stateless).

**Tech Stack:** TypeScript 5.6+, React 18+, zod 3.23, d3-hierarchy 3+, vitest + @testing-library/react for tests.

---

## File Structure

```
project/ts/packages/glyph-viz/
├── package.json
├── tsconfig.json
├── tsup.config.ts
├── vitest.config.ts
├── src/
│   ├── index.ts
│   ├── theme.ts                       # colors, sizes, z-depth palette
│   ├── stroke-path.tsx                # animCJK-style stroke rendering
│   ├── virtual-coord-grid.tsx         # 1024×1024 grid overlay
│   ├── bbox-overlay.tsx               # placed_bbox rectangles
│   ├── anchor-marker.tsx              # anchor points
│   ├── anchor-binding-arrow.tsx       # resolved anchor bindings
│   ├── tree-layout.tsx                # tidy tree over LayoutNode
│   ├── graph-layout.tsx               # stateless DAG renderer
│   ├── layer-stack.tsx                # exploded z-layer view
│   ├── iou-badge.tsx                  # IoU colored badge
│   ├── input-adapter-chip.tsx         # chip per authoring strategy
│   └── mode-indicator.tsx             # keep / refine / replace icon
└── test/
    ├── stroke-path.test.tsx
    ├── virtual-coord-grid.test.tsx
    ├── bbox-overlay.test.tsx
    ├── tree-layout.test.tsx
    ├── graph-layout.test.tsx
    ├── layer-stack.test.tsx
    └── chips-badges.test.tsx
```

---

## Task 1: Scaffold package + theme

**Files:**
- Create: `project/ts/packages/glyph-viz/package.json`
- Create: `project/ts/packages/glyph-viz/tsconfig.json`
- Create: `project/ts/packages/glyph-viz/tsup.config.ts`
- Create: `project/ts/packages/glyph-viz/vitest.config.ts`
- Create: `project/ts/packages/glyph-viz/src/theme.ts`
- Create: `project/ts/packages/glyph-viz/src/index.ts`

- [ ] **Step 1: `package.json`**

```json
{
  "name": "@olik/glyph-viz",
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
    "typecheck": "tsc --noEmit"
  },
  "peerDependencies": {
    "react":     ">=18",
    "react-dom": ">=18"
  },
  "dependencies": {
    "@olik/glyph-schema": "workspace:*",
    "d3-hierarchy": "3.1.2"
  },
  "devDependencies": {
    "@testing-library/react": "16.0.1",
    "@types/d3-hierarchy":    "3.1.7",
    "@types/react":           "18.3.11",
    "@types/react-dom":       "18.3.0",
    "jsdom":                  "25.0.1",
    "react":                  "18.3.1",
    "react-dom":              "18.3.1",
    "tsup":                   "8.3.0",
    "typescript":             "5.6.3",
    "vitest":                 "2.1.2"
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
    "jsx": "react-jsx",
    "types": ["vitest/globals"]
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
  external: ["react", "react-dom"],
});
```

- [ ] **Step 4: `vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: [],
  },
  esbuild: { jsx: "automatic" },
});
```

- [ ] **Step 5: `src/theme.ts`**

```ts
// project/ts/packages/glyph-viz/src/theme.ts
export const GLYPH_CANVAS_SIZE = 1024;

export const STROKE_COLOR = {
  outline:   "#1f2937",
  median:    "#f97316",
  highlight: "#10b981",
} as const;

export const LAYER_COLOR: Record<string, string> = {
  skeleton:        "#9ca3af",
  stroke_body:     "#111827",
  stroke_edge:     "#6366f1",
  texture_overlay: "#ec4899",
  damage:          "#dc2626",
};

export const INPUT_ADAPTER_COLOR: Record<string, string> = {
  direct:                   "#6366f1",
  "preset:left_right":      "#0ea5e9",
  "preset:top_bottom":      "#14b8a6",
  "preset:enclose":         "#d97706",
  "direct:repeat_triangle": "#a855f7",
  "anchor-binding":         "#ec4899",
  leaf:                     "#64748b",
};

export const IOU_THRESHOLD = {
  warn: 0.85,
  fail: 0.80,
} as const;

export function iouColor(v: number): string {
  if (v >= IOU_THRESHOLD.warn) return "#10b981";
  if (v >= IOU_THRESHOLD.fail) return "#eab308";
  return "#dc2626";
}
```

- [ ] **Step 6: `src/index.ts`**

```ts
// project/ts/packages/glyph-viz/src/index.ts
export const GLYPH_VIZ_VERSION = "0.1.0";
export * from "./theme.js";
```

- [ ] **Step 7: Install**

```bash
cd project/ts && pnpm install
cd packages/glyph-viz && pnpm typecheck
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add project/ts/packages/glyph-viz/package.json project/ts/packages/glyph-viz/tsconfig.json project/ts/packages/glyph-viz/tsup.config.ts project/ts/packages/glyph-viz/vitest.config.ts project/ts/packages/glyph-viz/src/theme.ts project/ts/packages/glyph-viz/src/index.ts project/ts/pnpm-lock.yaml
git commit -m "chore(glyph-viz): scaffold package + theme constants"
```

---

## Task 2: `StrokePath` — animCJK-style stroke rendering

**Files:**
- Create: `project/ts/packages/glyph-viz/src/stroke-path.tsx`
- Create: `project/ts/packages/glyph-viz/test/stroke-path.test.tsx`

Renders one stroke: a grey outline fill behind a black median brush sweep. Animation is progress-driven: `progress` 0..1 controls how much of the median is drawn (dash-offset idiom from animCJK).

- [ ] **Step 1: Write failing test**

```tsx
// project/ts/packages/glyph-viz/test/stroke-path.test.tsx
import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { StrokePath } from "../src/stroke-path.js";

describe("StrokePath", () => {
  test("renders outline and median paths", () => {
    const { container } = render(
      <svg>
        <StrokePath
          outlinePath="M 0 0 L 10 0 L 10 10 L 0 10 Z"
          median={[[5, 0], [5, 10]]}
          progress={1}
        />
      </svg>,
    );
    const paths = container.querySelectorAll("path");
    // outline + median
    expect(paths.length).toBe(2);
  });

  test("progress=0 hides the median stroke via dash offset", () => {
    const { container } = render(
      <svg>
        <StrokePath outlinePath="M 0 0 L 1 0" median={[[0, 0], [1, 0]]} progress={0} />
      </svg>,
    );
    const medianPath = container.querySelectorAll("path")[1];
    const dashOffset = Number(medianPath.getAttribute("stroke-dashoffset"));
    expect(dashOffset).toBeGreaterThan(0);
  });

  test("progress=1 fully draws the median", () => {
    const { container } = render(
      <svg>
        <StrokePath outlinePath="M 0 0 L 1 0" median={[[0, 0], [1, 0]]} progress={1} />
      </svg>,
    );
    const medianPath = container.querySelectorAll("path")[1];
    expect(Number(medianPath.getAttribute("stroke-dashoffset"))).toBe(0);
  });

  test("single-point median treated as zero-length dash", () => {
    const { container } = render(
      <svg>
        <StrokePath outlinePath="M 0 0 Z" median={[[0, 0]]} progress={1} />
      </svg>,
    );
    expect(container.querySelectorAll("path").length).toBe(2);
  });
});
```

- [ ] **Step 2: Implement `stroke-path.tsx`**

```tsx
// project/ts/packages/glyph-viz/src/stroke-path.tsx
import * as React from "react";
import { STROKE_COLOR } from "./theme.js";

export interface StrokePathProps {
  outlinePath: string;
  median:      ReadonlyArray<readonly [number, number]>;
  progress:    number;  // 0..1
  strokeWidth?: number;
  className?:  string;
}

export function StrokePath({
  outlinePath,
  median,
  progress,
  strokeWidth = 48,
  className,
}: StrokePathProps): React.ReactElement {
  const medianD = medianToPath(median);
  const totalLen = medianLength(median);
  const drawn = Math.max(0, Math.min(1, progress)) * totalLen;
  const dashArray = totalLen > 0 ? `${totalLen} ${totalLen}` : "0 0";
  const dashOffset = totalLen - drawn;

  return (
    <g className={className}>
      <path d={outlinePath} fill={STROKE_COLOR.outline} fillOpacity={0.25} />
      <path
        d={medianD}
        fill="none"
        stroke={STROKE_COLOR.median}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={dashArray}
        strokeDashoffset={dashOffset}
      />
    </g>
  );
}

function medianToPath(median: ReadonlyArray<readonly [number, number]>): string {
  if (median.length === 0) return "M 0 0 Z";
  const [[x0, y0], ...rest] = median;
  return `M ${x0} ${y0} ${rest.map(([x, y]) => `L ${x} ${y}`).join(" ")}`;
}

function medianLength(median: ReadonlyArray<readonly [number, number]>): number {
  let total = 0;
  for (let i = 1; i < median.length; i++) {
    const [x0, y0] = median[i - 1]!;
    const [x1, y1] = median[i]!;
    total += Math.hypot(x1 - x0, y1 - y0);
  }
  return total;
}
```

- [ ] **Step 3: Export from index**

Append to `src/index.ts`:

```ts
export * from "./stroke-path.js";
```

- [ ] **Step 4: Run tests**

```bash
cd project/ts/packages/glyph-viz && pnpm test
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add project/ts/packages/glyph-viz/src/stroke-path.tsx project/ts/packages/glyph-viz/src/index.ts project/ts/packages/glyph-viz/test/stroke-path.test.tsx
git commit -m "feat(glyph-viz): StrokePath component with progress-driven dash animation"
```

---

## Task 3: `VirtualCoordGrid` + `BBoxOverlay` + `AnchorMarker`

**Files:**
- Create: `project/ts/packages/glyph-viz/src/virtual-coord-grid.tsx`
- Create: `project/ts/packages/glyph-viz/src/bbox-overlay.tsx`
- Create: `project/ts/packages/glyph-viz/src/anchor-marker.tsx`
- Create: `project/ts/packages/glyph-viz/src/anchor-binding-arrow.tsx`
- Create: `project/ts/packages/glyph-viz/test/virtual-coord-grid.test.tsx`
- Create: `project/ts/packages/glyph-viz/test/bbox-overlay.test.tsx`

- [ ] **Step 1: `VirtualCoordGrid`**

```tsx
// project/ts/packages/glyph-viz/src/virtual-coord-grid.tsx
import * as React from "react";

export interface VirtualCoordGridProps {
  size?:      number;   // default 1024
  majorStep?: number;   // default 128
  minorStep?: number;   // default 32
  majorColor?: string;
  minorColor?: string;
}

export function VirtualCoordGrid({
  size = 1024,
  majorStep = 128,
  minorStep = 32,
  majorColor = "#cbd5e1",
  minorColor = "#eef2ff",
}: VirtualCoordGridProps): React.ReactElement {
  const minorLines: React.ReactElement[] = [];
  for (let x = minorStep; x < size; x += minorStep) {
    if (x % majorStep === 0) continue;
    minorLines.push(<line key={`mv${x}`} x1={x} y1={0} x2={x} y2={size} stroke={minorColor} strokeWidth={1} />);
    minorLines.push(<line key={`mh${x}`} x1={0} y1={x} x2={size} y2={x} stroke={minorColor} strokeWidth={1} />);
  }
  const majorLines: React.ReactElement[] = [];
  for (let x = 0; x <= size; x += majorStep) {
    majorLines.push(<line key={`Mv${x}`} x1={x} y1={0} x2={x} y2={size} stroke={majorColor} strokeWidth={1} />);
    majorLines.push(<line key={`Mh${x}`} x1={0} y1={x} x2={size} y2={x} stroke={majorColor} strokeWidth={1} />);
  }
  return (
    <g className="olik-virtual-coord-grid">
      {minorLines}
      {majorLines}
      <rect x={0} y={0} width={size} height={size} fill="none" stroke={majorColor} strokeWidth={2} />
    </g>
  );
}
```

- [ ] **Step 2: `BBoxOverlay`**

```tsx
// project/ts/packages/glyph-viz/src/bbox-overlay.tsx
import * as React from "react";
import type { BBox } from "@olik/glyph-schema";

export interface BBoxOverlayProps {
  bbox:    BBox;
  label?:  string;
  color?:  string;
  dashed?: boolean;
}

export function BBoxOverlay({
  bbox, label, color = "#0ea5e9", dashed = false,
}: BBoxOverlayProps): React.ReactElement {
  const [x0, y0, x1, y1] = bbox;
  const width  = x1 - x0;
  const height = y1 - y0;
  return (
    <g className="olik-bbox">
      <rect
        x={x0}
        y={y0}
        width={width}
        height={height}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeDasharray={dashed ? "8 4" : undefined}
      />
      {label ? (
        <text x={x0 + 6} y={y0 + 18} fill={color} fontSize={14} fontFamily="monospace">
          {label}
        </text>
      ) : null}
    </g>
  );
}
```

- [ ] **Step 3: `AnchorMarker`**

```tsx
// project/ts/packages/glyph-viz/src/anchor-marker.tsx
import * as React from "react";
import type { Point } from "@olik/glyph-schema";

export interface AnchorMarkerProps {
  name:  string;
  point: Point;
  color?: string;
  radius?: number;
}

export function AnchorMarker({
  name, point, color = "#ec4899", radius = 6,
}: AnchorMarkerProps): React.ReactElement {
  const [x, y] = point;
  return (
    <g className="olik-anchor">
      <circle cx={x} cy={y} r={radius} fill={color} />
      <text x={x + radius + 4} y={y + 4} fontSize={11} fontFamily="monospace" fill={color}>
        {name}
      </text>
    </g>
  );
}
```

- [ ] **Step 4: `AnchorBindingArrow`**

```tsx
// project/ts/packages/glyph-viz/src/anchor-binding-arrow.tsx
import * as React from "react";
import type { Point } from "@olik/glyph-schema";

export interface AnchorBindingArrowProps {
  from:  Point;
  to:    Point;
  color?: string;
  label?: string;
}

export function AnchorBindingArrow({
  from, to, color = "#f59e0b", label,
}: AnchorBindingArrowProps): React.ReactElement {
  const [x0, y0] = from;
  const [x1, y1] = to;
  const id = `arrowhead-${Math.floor((x0 + y0 + x1 + y1) * 1000)}`;
  const midX = (x0 + x1) / 2;
  const midY = (y0 + y1) / 2;
  return (
    <g className="olik-anchor-binding">
      <defs>
        <marker id={id} viewBox="0 0 10 10" refX="8" refY="5"
                markerWidth="8" markerHeight="8" orient="auto">
          <path d="M 0 0 L 10 5 L 0 10 z" fill={color} />
        </marker>
      </defs>
      <line
        x1={x0} y1={y0} x2={x1} y2={y1}
        stroke={color} strokeWidth={2}
        markerEnd={`url(#${id})`}
      />
      {label ? (
        <text x={midX} y={midY - 6} fontSize={11} fontFamily="monospace" fill={color}>
          {label}
        </text>
      ) : null}
    </g>
  );
}
```

- [ ] **Step 5: Export from index**

Append to `src/index.ts`:

```ts
export * from "./virtual-coord-grid.js";
export * from "./bbox-overlay.js";
export * from "./anchor-marker.js";
export * from "./anchor-binding-arrow.js";
```

- [ ] **Step 6: Write tests**

```tsx
// project/ts/packages/glyph-viz/test/virtual-coord-grid.test.tsx
import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { VirtualCoordGrid } from "../src/virtual-coord-grid.js";

describe("VirtualCoordGrid", () => {
  test("default grid spans 1024 with major every 128", () => {
    const { container } = render(<svg><VirtualCoordGrid /></svg>);
    // 8 major lines on each axis (0..1024 by 128 = 9 lines, minus edges counted elsewhere)
    const lines = container.querySelectorAll("line");
    expect(lines.length).toBeGreaterThan(0);
  });

  test("bounding rect is drawn", () => {
    const { container } = render(<svg><VirtualCoordGrid /></svg>);
    const rect = container.querySelector("rect");
    expect(rect).not.toBeNull();
    expect(rect!.getAttribute("width")).toBe("1024");
  });
});
```

```tsx
// project/ts/packages/glyph-viz/test/bbox-overlay.test.tsx
import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { AnchorBindingArrow, AnchorMarker, BBoxOverlay } from "../src/index.js";

describe("BBoxOverlay", () => {
  test("renders rect with correct dims + optional label", () => {
    const { container } = render(
      <svg><BBoxOverlay bbox={[10, 20, 40, 60]} label="inst:x" /></svg>,
    );
    const rect = container.querySelector("rect")!;
    expect(rect.getAttribute("x")).toBe("10");
    expect(rect.getAttribute("width")).toBe("30");
    expect(rect.getAttribute("height")).toBe("40");
    expect(container.textContent).toContain("inst:x");
  });
});

describe("AnchorMarker", () => {
  test("renders circle + name label", () => {
    const { container } = render(
      <svg><AnchorMarker name="center" point={[100, 200]} /></svg>,
    );
    expect(container.querySelector("circle")!.getAttribute("cx")).toBe("100");
    expect(container.textContent).toContain("center");
  });
});

describe("AnchorBindingArrow", () => {
  test("renders line with marker-end", () => {
    const { container } = render(
      <svg><AnchorBindingArrow from={[0, 0]} to={[100, 0]} /></svg>,
    );
    const line = container.querySelector("line")!;
    expect(line.getAttribute("marker-end")).toMatch(/^url\(#arrowhead-/);
  });
});
```

- [ ] **Step 7: Run**

```bash
cd project/ts/packages/glyph-viz && pnpm test
```

Expected: `8 passed` (4 stroke + 4 overlays).

- [ ] **Step 8: Commit**

```bash
git add project/ts/packages/glyph-viz/src/virtual-coord-grid.tsx project/ts/packages/glyph-viz/src/bbox-overlay.tsx project/ts/packages/glyph-viz/src/anchor-marker.tsx project/ts/packages/glyph-viz/src/anchor-binding-arrow.tsx project/ts/packages/glyph-viz/src/index.ts project/ts/packages/glyph-viz/test/virtual-coord-grid.test.tsx project/ts/packages/glyph-viz/test/bbox-overlay.test.tsx
git commit -m "feat(glyph-viz): VirtualCoordGrid + BBoxOverlay + AnchorMarker + AnchorBindingArrow"
```

---

## Task 4: `TreeLayout` — tidy tree over `LayoutNode`

**Files:**
- Create: `project/ts/packages/glyph-viz/src/tree-layout.tsx`
- Create: `project/ts/packages/glyph-viz/test/tree-layout.test.tsx`

Uses `d3-hierarchy`'s tidy tree algorithm. Renders nodes as `<g>` at computed (x, y); caller supplies a render function for node contents so the same primitive works for a decomposition tree or a layout-tree overview.

- [ ] **Step 1: Write failing test**

```tsx
// project/ts/packages/glyph-viz/test/tree-layout.test.tsx
import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { LayoutNode } from "@olik/glyph-schema";
import { TreeLayout } from "../src/tree-layout.js";

const fakeTree: LayoutNode = {
  id: "root",
  bbox: [0, 0, 1024, 1024],
  children: [
    { id: "L", bbox: [0, 0, 400, 1024] },
    { id: "R", bbox: [420, 0, 1024, 1024] },
  ],
};

describe("TreeLayout", () => {
  test("renders one <g> per node", () => {
    const { container } = render(
      <svg width={1024} height={800}>
        <TreeLayout root={fakeTree} width={800} height={400} renderNode={(n) => <text>{n.id}</text>} />
      </svg>,
    );
    const groups = container.querySelectorAll("g.olik-tree-node");
    expect(groups.length).toBe(3);
  });

  test("renders one <path> per parent-child link", () => {
    const { container } = render(
      <svg width={1024} height={800}>
        <TreeLayout root={fakeTree} width={800} height={400} renderNode={(n) => <text>{n.id}</text>} />
      </svg>,
    );
    const paths = container.querySelectorAll("path.olik-tree-link");
    expect(paths.length).toBe(2);  // root→L, root→R
  });

  test("calls renderNode with each LayoutNode", () => {
    const seen: string[] = [];
    render(
      <svg>
        <TreeLayout root={fakeTree} width={400} height={400} renderNode={(n) => {
          seen.push(n.id);
          return <text>{n.id}</text>;
        }} />
      </svg>,
    );
    expect(seen.sort()).toEqual(["L", "R", "root"]);
  });
});
```

- [ ] **Step 2: Implement `tree-layout.tsx`**

```tsx
// project/ts/packages/glyph-viz/src/tree-layout.tsx
import * as React from "react";
import { hierarchy, tree as d3tree, type HierarchyPointNode } from "d3-hierarchy";
import type { LayoutNode } from "@olik/glyph-schema";

export interface TreeLayoutProps {
  root:   LayoutNode;
  width:  number;
  height: number;
  nodeRadius?: number;
  linkColor?:  string;
  renderNode:  (node: LayoutNode) => React.ReactNode;
}

export function TreeLayout({
  root, width, height, linkColor = "#94a3b8", renderNode,
}: TreeLayoutProps): React.ReactElement {
  const layout = React.useMemo(() => {
    const h = hierarchy<LayoutNode>(root, (n) => n.children ?? []);
    return d3tree<LayoutNode>().size([width, height])(h);
  }, [root, width, height]);

  const nodes = layout.descendants();
  const links = layout.links();

  return (
    <g className="olik-tree">
      {links.map((l, i) => (
        <path
          key={`l${i}`}
          className="olik-tree-link"
          d={curveD(l.source, l.target)}
          fill="none"
          stroke={linkColor}
          strokeWidth={1.5}
        />
      ))}
      {nodes.map((n) => (
        <g key={n.data.id} className="olik-tree-node" transform={`translate(${n.x}, ${n.y})`}>
          {renderNode(n.data)}
        </g>
      ))}
    </g>
  );
}

function curveD(
  a: HierarchyPointNode<LayoutNode>,
  b: HierarchyPointNode<LayoutNode>,
): string {
  const mx = (a.y + b.y) / 2;
  return `M ${a.x} ${a.y} C ${a.x} ${mx}, ${b.x} ${mx}, ${b.x} ${b.y}`;
}
```

- [ ] **Step 3: Export**

Append to `src/index.ts`:

```ts
export * from "./tree-layout.js";
```

- [ ] **Step 4: Run**

```bash
cd project/ts/packages/glyph-viz && pnpm test
```

Expected: `11 passed`.

- [ ] **Step 5: Commit**

```bash
git add project/ts/packages/glyph-viz/src/tree-layout.tsx project/ts/packages/glyph-viz/src/index.ts project/ts/packages/glyph-viz/test/tree-layout.test.tsx
git commit -m "feat(glyph-viz): TreeLayout using d3-hierarchy tidy tree"
```

---

## Task 5: `GraphLayout` — stateless DAG renderer

**Files:**
- Create: `project/ts/packages/glyph-viz/src/graph-layout.tsx`
- Create: `project/ts/packages/glyph-viz/test/graph-layout.test.tsx`

Callers pre-compute node positions. The primitive just renders `<g>` + links. Force-layout is the caller's job (keeps this primitive pure).

- [ ] **Step 1: Write failing test**

```tsx
// project/ts/packages/glyph-viz/test/graph-layout.test.tsx
import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { GraphLayout, type GraphNode, type GraphLink } from "../src/graph-layout.js";

const nodes: GraphNode[] = [
  { id: "proto:a", x: 100, y: 100 },
  { id: "proto:b", x: 300, y: 100 },
  { id: "proto:c", x: 200, y: 300 },
];
const links: GraphLink[] = [
  { source: "proto:a", target: "proto:b" },
  { source: "proto:a", target: "proto:c" },
];

describe("GraphLayout", () => {
  test("renders one <g> per node", () => {
    const { container } = render(
      <svg><GraphLayout nodes={nodes} links={links} renderNode={(n) => <circle r={10} />} /></svg>,
    );
    expect(container.querySelectorAll("g.olik-graph-node").length).toBe(3);
  });

  test("renders one <line> per link", () => {
    const { container } = render(
      <svg><GraphLayout nodes={nodes} links={links} renderNode={() => null} /></svg>,
    );
    expect(container.querySelectorAll("line.olik-graph-link").length).toBe(2);
  });

  test("skips links with unknown endpoints", () => {
    const bad: GraphLink[] = [{ source: "proto:a", target: "proto:nope" }];
    const { container } = render(
      <svg><GraphLayout nodes={nodes} links={bad} renderNode={() => null} /></svg>,
    );
    expect(container.querySelectorAll("line.olik-graph-link").length).toBe(0);
  });
});
```

- [ ] **Step 2: Implement `graph-layout.tsx`**

```tsx
// project/ts/packages/glyph-viz/src/graph-layout.tsx
import * as React from "react";

export interface GraphNode {
  id: string;
  x:  number;
  y:  number;
  data?: unknown;
}

export interface GraphLink {
  source: string;
  target: string;
  kind?:  string;
}

export interface GraphLayoutProps {
  nodes: ReadonlyArray<GraphNode>;
  links: ReadonlyArray<GraphLink>;
  linkColor?: string;
  renderNode: (node: GraphNode) => React.ReactNode;
}

export function GraphLayout({
  nodes, links, linkColor = "#94a3b8", renderNode,
}: GraphLayoutProps): React.ReactElement {
  const byId = new Map(nodes.map((n) => [n.id, n] as const));
  return (
    <g className="olik-graph">
      {links.map((l, i) => {
        const s = byId.get(l.source);
        const t = byId.get(l.target);
        if (!s || !t) return null;
        return (
          <line
            key={`l${i}`}
            className="olik-graph-link"
            x1={s.x} y1={s.y} x2={t.x} y2={t.y}
            stroke={linkColor} strokeWidth={1.5}
          />
        );
      })}
      {nodes.map((n) => (
        <g key={n.id} className="olik-graph-node" transform={`translate(${n.x}, ${n.y})`}>
          {renderNode(n)}
        </g>
      ))}
    </g>
  );
}
```

- [ ] **Step 3: Export**

Append to `src/index.ts`:

```ts
export * from "./graph-layout.js";
```

- [ ] **Step 4: Run**

```bash
cd project/ts/packages/glyph-viz && pnpm test
```

Expected: `14 passed`.

- [ ] **Step 5: Commit**

```bash
git add project/ts/packages/glyph-viz/src/graph-layout.tsx project/ts/packages/glyph-viz/src/index.ts project/ts/packages/glyph-viz/test/graph-layout.test.tsx
git commit -m "feat(glyph-viz): GraphLayout (stateless DAG renderer)"
```

---

## Task 6: `LayerStack` — exploded z-layer view

**Files:**
- Create: `project/ts/packages/glyph-viz/src/layer-stack.tsx`
- Create: `project/ts/packages/glyph-viz/test/layer-stack.test.tsx`

Buckets `stroke_instances[]` by `render_layers[]` via their `z`, stacks them vertically. Each layer is a mini viewport of the glyph showing only strokes in that layer's z range.

- [ ] **Step 1: Write failing test**

```tsx
// project/ts/packages/glyph-viz/test/layer-stack.test.tsx
import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { RenderLayer, StrokeInstance } from "@olik/glyph-schema";
import { LayerStack } from "../src/layer-stack.js";

const layers: RenderLayer[] = [
  { name: "skeleton",    z_min: 0,  z_max: 9 },
  { name: "stroke_body", z_min: 10, z_max: 49 },
  { name: "stroke_edge", z_min: 50, z_max: 69 },
];

const strokes: StrokeInstance[] = [
  { id: "s1", instance_id: "inst:a", order: 0, path: "M 0 0 L 10 0", median: [[0,0],[10,0]],
    bbox: [0, 0, 10, 0], z: 20, role: "horizontal" },
  { id: "s2", instance_id: "inst:a", order: 1, path: "M 0 5 L 10 5", median: [[0,5],[10,5]],
    bbox: [0, 5, 10, 5], z: 22, role: "horizontal" },
  { id: "s3", instance_id: "inst:b", order: 0, path: "M 5 0 L 5 10", median: [[5,0],[5,10]],
    bbox: [5, 0, 5, 10], z: 55, role: "vertical" },
];

describe("LayerStack", () => {
  test("renders one panel per layer", () => {
    const { container } = render(
      <svg>
        <LayerStack layers={layers} strokes={strokes} panelHeight={100} />
      </svg>,
    );
    const panels = container.querySelectorAll("g.olik-layer-panel");
    expect(panels.length).toBe(3);
  });

  test("assigns strokes to correct layers by z", () => {
    const { container } = render(
      <svg>
        <LayerStack layers={layers} strokes={strokes} panelHeight={100} />
      </svg>,
    );
    const panels = container.querySelectorAll("g.olik-layer-panel");
    // panel 0 (skeleton, z 0..9) — 0 strokes
    expect(panels[0].querySelectorAll("path").length).toBe(0);
    // panel 1 (stroke_body, z 10..49) — 2 strokes
    expect(panels[1].querySelectorAll("path").length).toBe(2);
    // panel 2 (stroke_edge, z 50..69) — 1 stroke
    expect(panels[2].querySelectorAll("path").length).toBe(1);
  });

  test("panel labels show layer name + stroke count", () => {
    const { container } = render(
      <svg>
        <LayerStack layers={layers} strokes={strokes} panelHeight={100} />
      </svg>,
    );
    expect(container.textContent).toContain("stroke_body");
    expect(container.textContent).toContain("(2)");
  });
});
```

- [ ] **Step 2: Implement `layer-stack.tsx`**

```tsx
// project/ts/packages/glyph-viz/src/layer-stack.tsx
import * as React from "react";
import type { RenderLayer, StrokeInstance } from "@olik/glyph-schema";
import { LAYER_COLOR } from "./theme.js";

export interface LayerStackProps {
  layers:       ReadonlyArray<RenderLayer>;
  strokes:      ReadonlyArray<StrokeInstance>;
  panelHeight:  number;
  panelWidth?:  number;
  gap?:         number;
  glyphSize?:   number;
}

export function LayerStack({
  layers, strokes, panelHeight,
  panelWidth = 120,
  gap = 12,
  glyphSize = 1024,
}: LayerStackProps): React.ReactElement {
  const scale = panelWidth / glyphSize;
  const panelInnerH = panelHeight - 24; // reserve space for label
  return (
    <g className="olik-layer-stack">
      {layers.map((layer, i) => {
        const inLayer = strokes.filter((s) => s.z >= layer.z_min && s.z <= layer.z_max);
        const yOffset = i * (panelHeight + gap);
        const color = LAYER_COLOR[layer.name] ?? "#0f172a";
        return (
          <g
            key={layer.name}
            className="olik-layer-panel"
            transform={`translate(0, ${yOffset})`}
          >
            <rect
              x={0} y={0} width={panelWidth} height={panelHeight}
              fill="#f8fafc" stroke={color} strokeWidth={1}
            />
            <text x={8} y={16} fontSize={11} fontFamily="monospace" fill={color}>
              {layer.name} ({inLayer.length})
            </text>
            <g transform={`translate(0, 24) scale(${scale} ${panelInnerH / glyphSize})`}>
              {inLayer.map((s) => (
                <path key={s.id} d={s.path} fill="none" stroke={color} strokeWidth={48} strokeLinecap="round" />
              ))}
            </g>
          </g>
        );
      })}
    </g>
  );
}
```

- [ ] **Step 3: Export**

Append to `src/index.ts`:

```ts
export * from "./layer-stack.js";
```

- [ ] **Step 4: Run**

```bash
cd project/ts/packages/glyph-viz && pnpm test
```

Expected: `17 passed`.

- [ ] **Step 5: Commit**

```bash
git add project/ts/packages/glyph-viz/src/layer-stack.tsx project/ts/packages/glyph-viz/src/index.ts project/ts/packages/glyph-viz/test/layer-stack.test.tsx
git commit -m "feat(glyph-viz): LayerStack (exploded z-layer view)"
```

---

## Task 7: `IoUBadge` + `InputAdapterChip` + `ModeIndicator`

**Files:**
- Create: `project/ts/packages/glyph-viz/src/iou-badge.tsx`
- Create: `project/ts/packages/glyph-viz/src/input-adapter-chip.tsx`
- Create: `project/ts/packages/glyph-viz/src/mode-indicator.tsx`
- Create: `project/ts/packages/glyph-viz/test/chips-badges.test.tsx`

- [ ] **Step 1: Implement the three**

```tsx
// project/ts/packages/glyph-viz/src/iou-badge.tsx
import * as React from "react";
import { iouColor } from "./theme.js";

export interface IoUBadgeProps {
  value: number;
  label?: string;
  x?:    number;
  y?:    number;
}

export function IoUBadge({
  value, label, x = 0, y = 0,
}: IoUBadgeProps): React.ReactElement {
  const text = label ?? `IoU ${value.toFixed(2)}`;
  const color = iouColor(value);
  return (
    <g className="olik-iou-badge" transform={`translate(${x}, ${y})`}>
      <rect x={0} y={0} width={72} height={20} rx={4} fill={color} />
      <text x={36} y={14} fontSize={11} fontFamily="monospace" fill="#fff" textAnchor="middle">
        {text}
      </text>
    </g>
  );
}
```

```tsx
// project/ts/packages/glyph-viz/src/input-adapter-chip.tsx
import * as React from "react";
import { INPUT_ADAPTER_COLOR } from "./theme.js";

export interface InputAdapterChipProps {
  adapter: string;
  x?:      number;
  y?:      number;
}

export function InputAdapterChip({
  adapter, x = 0, y = 0,
}: InputAdapterChipProps): React.ReactElement {
  const color = INPUT_ADAPTER_COLOR[adapter] ?? "#64748b";
  const text = adapter.replace("preset:", "").replace("direct:", "");
  return (
    <g className="olik-input-adapter-chip" transform={`translate(${x}, ${y})`}>
      <rect x={0} y={0} width={110} height={18} rx={3} fill={color} fillOpacity={0.15} stroke={color} strokeWidth={1} />
      <text x={6} y={13} fontSize={11} fontFamily="monospace" fill={color}>
        {text}
      </text>
    </g>
  );
}
```

```tsx
// project/ts/packages/glyph-viz/src/mode-indicator.tsx
import * as React from "react";

const SYMBOL: Record<string, string> = {
  keep:    "○",
  refine:  "◐",
  replace: "●",
};

export interface ModeIndicatorProps {
  mode: "keep" | "refine" | "replace";
  x?:   number;
  y?:   number;
}

export function ModeIndicator({
  mode, x = 0, y = 0,
}: ModeIndicatorProps): React.ReactElement {
  return (
    <g className="olik-mode-indicator" transform={`translate(${x}, ${y})`}>
      <text x={0} y={12} fontSize={14} fontFamily="monospace">
        {SYMBOL[mode]} {mode}
      </text>
    </g>
  );
}
```

- [ ] **Step 2: Export all**

Append to `src/index.ts`:

```ts
export * from "./iou-badge.js";
export * from "./input-adapter-chip.js";
export * from "./mode-indicator.js";
```

- [ ] **Step 3: Tests**

```tsx
// project/ts/packages/glyph-viz/test/chips-badges.test.tsx
import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { IoUBadge, InputAdapterChip, ModeIndicator } from "../src/index.js";

describe("IoUBadge", () => {
  test("formats value to two decimals", () => {
    const { container } = render(<svg><IoUBadge value={0.918} /></svg>);
    expect(container.textContent).toContain("0.92");
  });

  test("uses green fill when IoU >= 0.85", () => {
    const { container } = render(<svg><IoUBadge value={0.9} /></svg>);
    expect(container.querySelector("rect")!.getAttribute("fill")).toBe("#10b981");
  });

  test("uses red fill when IoU < 0.80", () => {
    const { container } = render(<svg><IoUBadge value={0.5} /></svg>);
    expect(container.querySelector("rect")!.getAttribute("fill")).toBe("#dc2626");
  });
});

describe("InputAdapterChip", () => {
  test("renders label sans the preset: prefix", () => {
    const { container } = render(<svg><InputAdapterChip adapter="preset:left_right" /></svg>);
    expect(container.textContent).toContain("left_right");
    expect(container.textContent).not.toContain("preset:");
  });

  test("falls back to grey color for unknown adapter", () => {
    const { container } = render(<svg><InputAdapterChip adapter="mystery" /></svg>);
    const rect = container.querySelector("rect")!;
    expect(rect.getAttribute("stroke")).toBe("#64748b");
  });
});

describe("ModeIndicator", () => {
  test.each(["keep", "refine", "replace"] as const)("renders %s label", (mode) => {
    const { container } = render(<svg><ModeIndicator mode={mode} /></svg>);
    expect(container.textContent).toContain(mode);
  });
});
```

- [ ] **Step 4: Run**

```bash
cd project/ts/packages/glyph-viz && pnpm test
```

Expected: `24 passed`.

- [ ] **Step 5: Commit**

```bash
git add project/ts/packages/glyph-viz/src/iou-badge.tsx project/ts/packages/glyph-viz/src/input-adapter-chip.tsx project/ts/packages/glyph-viz/src/mode-indicator.tsx project/ts/packages/glyph-viz/src/index.ts project/ts/packages/glyph-viz/test/chips-badges.test.tsx
git commit -m "feat(glyph-viz): IoUBadge + InputAdapterChip + ModeIndicator"
```

---

## Task 8: Final build + tag

- [ ] **Step 1: Build package**

```bash
cd project/ts/packages/glyph-viz && pnpm build
```

Expected: `dist/index.js`, `dist/index.cjs`, `dist/index.d.ts` produced.

- [ ] **Step 2: Workspace-wide test**

```bash
cd project/ts && pnpm -r test
```

Expected: all tests pass across glyph-schema + glyph-loader + glyph-viz.

- [ ] **Step 3: Tag**

```bash
git tag -a plan-05-ts-viz -m "Plan 05 complete — @olik/glyph-viz primitives"
```

---

## Self-review

Coverage against spec § T4 (glyph-viz primitives):

- [x] StrokePath (animCJK-style animation) — Task 2
- [x] VirtualCoordGrid — Task 3
- [x] BBoxOverlay — Task 3
- [x] AnchorMarker — Task 3
- [x] AnchorBindingArrow — Task 3
- [x] TreeLayout — Task 4
- [x] GraphLayout — Task 5
- [x] LayerStack — Task 6
- [x] IoUBadge, InputAdapterChip, ModeIndicator — Task 7

All nine primitives named in the spec's "Package split" list are present.

## Follow-ups for later plans

- Plan 06 (Remotion) composes StrokePath with timeline-driven progress.
- Plan 07 (Inspector) wraps Tree/GraphLayout inside xyflow custom nodes.
- Graph layout is stateless; Plan 07 or a future package owns force-directed positioning.

## Adjustments after execution

_Notes on prop-shape changes, accessibility tweaks, or component splits that emerged during Remotion/Inspector integration._
