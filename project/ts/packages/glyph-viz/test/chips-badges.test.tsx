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
  test("renders the adapter label verbatim", () => {
    const { container } = render(<svg><InputAdapterChip adapter="refine" /></svg>);
    expect(container.textContent).toContain("refine");
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
