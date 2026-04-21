import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { AnchorBindingArrow, AnchorMarker, BBoxOverlay } from "../src/index.js";

describe("BBoxOverlay", () => {
  test("renders rect with correct dims + optional label", () => {
    const { container } = render(
      <svg>
        <BBoxOverlay bbox={[10, 20, 40, 60]} label="inst:x" />
      </svg>,
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
      <svg>
        <AnchorMarker name="center" point={[100, 200]} />
      </svg>,
    );
    expect(container.querySelector("circle")!.getAttribute("cx")).toBe("100");
    expect(container.textContent).toContain("center");
  });
});

describe("AnchorBindingArrow", () => {
  test("renders line with marker-end", () => {
    const { container } = render(
      <svg>
        <AnchorBindingArrow from={[0, 0]} to={[100, 0]} />
      </svg>,
    );
    const line = container.querySelector("line")!;
    expect(line.getAttribute("marker-end")).toMatch(/^url\(#arrowhead-/);
  });
});
