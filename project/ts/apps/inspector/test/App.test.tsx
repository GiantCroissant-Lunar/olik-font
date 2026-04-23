import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { App } from "../src/App.js";

const mocks = vi.hoisted(() => ({
  loadGlyphRecordUrl: vi.fn(async (url: string) => ({
    glyph_id: decodeURIComponent(url.replace("/data/glyph-record-", "").replace(".json", "")),
  })),
}));

// mock loader module so tests don't need HTTP
vi.mock("@olik/glyph-loader", () => ({
  loadGlyphRecordUrl: mocks.loadGlyphRecordUrl,
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

  test("loads the route char even when it is outside the seed set", async () => {
    window.history.replaceState({}, "", "/glyph/%E4%B8%81");

    render(<App />);

    expect(await screen.findByText("no layout tree for 丁")).toBeTruthy();
    expect(mocks.loadGlyphRecordUrl).toHaveBeenCalledWith("/data/glyph-record-丁.json");
  });
});
