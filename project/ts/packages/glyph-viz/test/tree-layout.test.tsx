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
    expect(paths.length).toBe(2);
  });

  test("calls renderNode with each LayoutNode", () => {
    const seen: string[] = [];
    render(
      <svg>
        <TreeLayout
          root={fakeTree}
          width={400}
          height={400}
          renderNode={(n) => {
            seen.push(n.id);
            return <text>{n.id}</text>;
          }}
        />
      </svg>,
    );
    expect(seen.sort()).toEqual(["L", "R", "root"]);
  });
});
