import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { GraphLayout, type GraphLink, type GraphNode } from "../src/graph-layout.js";

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
      <svg>
        <GraphLayout nodes={nodes} links={links} renderNode={(n) => <circle r={10} />} />
      </svg>,
    );
    expect(container.querySelectorAll("g.olik-graph-node").length).toBe(3);
  });

  test("renders one <line> per link", () => {
    const { container } = render(
      <svg>
        <GraphLayout nodes={nodes} links={links} renderNode={() => null} />
      </svg>,
    );
    expect(container.querySelectorAll("line.olik-graph-link").length).toBe(2);
  });

  test("skips links with unknown endpoints", () => {
    const bad: GraphLink[] = [{ source: "proto:a", target: "proto:nope" }];
    const { container } = render(
      <svg>
        <GraphLayout nodes={nodes} links={bad} renderNode={() => null} />
      </svg>,
    );
    expect(container.querySelectorAll("line.olik-graph-link").length).toBe(0);
  });
});
