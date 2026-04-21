import { render } from "@testing-library/react";
import { ReactFlowProvider } from "@xyflow/react";
import { describe, expect, test } from "vitest";
import type { Prototype } from "@olik/glyph-schema";
import { PrototypeNode } from "../src/prototype-node.js";

const proto: Prototype = {
  id: "proto:sun",
  name: "日",
  kind: "component",
  canonical_bbox: [0, 0, 1024, 1024],
  strokes: [
    {
      id: "s0",
      path: "M 0 0 L 1 0",
      median: [
        [0, 0],
        [1, 0],
      ],
      order: 0,
      role: "horizontal",
    },
  ],
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
