import { render } from "@testing-library/react";
import { ReactFlowProvider } from "@xyflow/react";
import { describe, expect, test } from "vitest";
import { DecompNode } from "../src/decomp-node.js";

describe("DecompNode", () => {
  test("renders char + operator + components + rule id", () => {
    const { container } = render(
      <ReactFlowProvider>
        <DecompNode
          id="n1"
          data={{
            char: "清",
            operator: "c",
            components: ["氵", "青"],
            wouldMode: "keep",
            ruleId: "decomp.use_extraction_plan",
          }}
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
