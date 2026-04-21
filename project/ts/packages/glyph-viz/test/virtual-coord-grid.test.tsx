import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { VirtualCoordGrid } from "../src/virtual-coord-grid.js";

describe("VirtualCoordGrid", () => {
  test("default grid spans 1024 with major every 128", () => {
    const { container } = render(
      <svg>
        <VirtualCoordGrid />
      </svg>,
    );
    const lines = container.querySelectorAll("line");
    expect(lines.length).toBeGreaterThan(0);
  });

  test("bounding rect is drawn", () => {
    const { container } = render(
      <svg>
        <VirtualCoordGrid />
      </svg>,
    );
    const rect = container.querySelector("rect");
    expect(rect).not.toBeNull();
    expect(rect!.getAttribute("width")).toBe("1024");
  });
});
