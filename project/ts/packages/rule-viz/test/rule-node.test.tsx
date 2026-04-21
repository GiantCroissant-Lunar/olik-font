import { render } from "@testing-library/react";
import { ReactFlowProvider } from "@xyflow/react";
import { describe, expect, test } from "vitest";
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
          selected={false}
          zIndex={0}
          isConnectable
          xPos={0}
          yPos={0}
          dragging={false}
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
          selected={false}
          zIndex={0}
          isConnectable
          xPos={0}
          yPos={0}
          dragging={false}
        />
      </ReactFlowProvider>,
    );
    expect(container.textContent).toContain("decomp.default_keep");
    expect(container.textContent).toContain("decomposition");
  });
});
