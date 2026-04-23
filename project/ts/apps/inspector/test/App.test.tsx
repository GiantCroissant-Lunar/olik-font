import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { App } from "../src/App.js";

// mock loader module so tests don't need HTTP
vi.mock("@olik/glyph-loader", () => ({
  loadGlyphRecordUrl: vi.fn(async () => ({ glyph_id: "明" })),
  loadPrototypeBrowserDataUrl: vi.fn(async () => ({
    focus: { id: "u6708", label: "月", kind: "focus", role: "meaning", etymology: "pictographic", productive_count: 37 },
    nodes: [],
    edges: [],
    appearsIn: [],
  })),
  loadPrototypeLibraryUrl: vi.fn(async () => ({ prototypes: {} })),
  loadRuleTraceUrl: vi.fn(async () => ({ decisions: [] })),
}));

describe("App", () => {
  test("renders top nav", async () => {
    render(<App />);
    expect(await screen.findByText("Decomposition Explorer")).toBeTruthy();
    expect(screen.getByText("Prototype Browser")).toBeTruthy();
    expect(screen.getByText("Rule Browser")).toBeTruthy();
    expect(screen.getByText("Placement Debugger")).toBeTruthy();
  });
});
