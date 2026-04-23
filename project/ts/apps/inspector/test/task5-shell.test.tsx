import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { App } from "../src/App.js";

class ResizeObserverMock {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

vi.stubGlobal("ResizeObserver", ResizeObserverMock);

vi.mock("@olik/glyph-loader", () => ({
  loadPrototypeBrowserDataUrl: vi.fn(async () => ({
    focus: { id: "u6708", label: "月", kind: "focus", role: "meaning", etymology: "pictographic", productive_count: 37 },
    nodes: [],
    edges: [],
    appearsIn: [],
  })),
  loadPrototypeLibraryUrl: vi.fn(async () => ({
    prototypes: {},
    prototypes_by_name: {},
    usage_index: {},
  })),
  loadGlyphRecordUrl: vi.fn(async (url: string) => ({
    glyph_id: url,
    decomposition: null,
    prototype_placements: [],
    layout_tree: {
      id: "root",
      kind: "leaf",
      bbox: [0, 0, 1024, 1024],
      children: [],
    },
  })),
  loadRuleTraceUrl: vi.fn(async () => ({
    glyph_id: "明",
    decisions: [],
  })),
}));

describe("Task 5 shell", () => {
  test("loads app state and renders decomposition explorer content", async () => {
    render(<App />);

    expect(screen.getByText("loading…")).toBeTruthy();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Decomposition Explorer" })).toBeTruthy();
    });

    expect(screen.getByRole("button", { name: "Prototype Browser" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Rule Browser" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Placement Debugger" })).toBeTruthy();

    expect(screen.getByRole("button", { name: "明" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "清" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "國" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "森" })).toBeTruthy();

    expect(screen.queryByText(/views land in Task 6/)).toBeNull();
    expect(screen.getByText("明")).toBeTruthy();
    expect(screen.getByText("op: atomic")).toBeTruthy();
  });
});
