import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { App } from "../src/App.js";

vi.mock("@olik/glyph-loader", () => ({
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
  test("loads app state and renders top nav + char picker", async () => {
    render(<App />);

    expect(screen.getByText("loading…")).toBeTruthy();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Decomposition Explorer" })).toBeTruthy();
    });

    expect(screen.getByRole("button", { name: "Prototype Library" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Rule Browser" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Placement Debugger" })).toBeTruthy();

    expect(screen.getByRole("button", { name: "明" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "清" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "國" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "森" })).toBeTruthy();

    expect(screen.getByText((_, element) => element?.textContent === "view decomposition, char 明 (views land in Task 6)")).toBeTruthy();
  });
});
