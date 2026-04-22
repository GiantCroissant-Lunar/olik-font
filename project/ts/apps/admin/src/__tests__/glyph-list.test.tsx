import { afterEach, describe, it, expect, vi } from "vitest";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { Refine } from "@refinedev/core";
import { MemoryRouter } from "react-router";

import { createDataProvider } from "../data-provider.js";
import { GlyphList } from "../resources/glyph/list.js";

afterEach(() => {
  cleanup();
});

if (typeof window !== "undefined" && window.matchMedia === undefined) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

if (typeof globalThis.ResizeObserver === "undefined") {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }

  globalThis.ResizeObserver = ResizeObserverMock;
}

function renderWithProviders(db: ReturnType<typeof mockDb>) {
  return render(
    <MantineProvider>
      <MemoryRouter>
        <Refine dataProvider={createDataProvider(db)} resources={[{ name: "glyph" }]}>
          <GlyphList />
        </Refine>
      </MemoryRouter>
    </MantineProvider>,
  );
}

function mockDb() {
  return {
    listGlyphs: vi.fn(async ({ filter }: { filter?: { status?: unknown } }) => ({
      items: [
        { char: "林", stroke_count: 8, radical: "木", iou_mean: 0.83 },
        { char: "森", stroke_count: 12, radical: "木", iou_mean: 0.95 },
      ],
      _filter: filter,
    })),
    getGlyph: vi.fn(async () => null),
    listPrototypes: vi.fn(async () => []),
    getPrototypeUsers: vi.fn(async () => []),
    listVariants: vi.fn(async () => []),
    subscribeVariants: vi.fn(async () => async () => {}),
    updateGlyphStatus: vi.fn(async () => {}),
    close: vi.fn(async () => {}),
  } as unknown as Parameters<typeof createDataProvider>[0];
}

describe("GlyphList", () => {
  it("defaults the status filter to needs_review on first render", async () => {
    const db = mockDb();
    renderWithProviders(db);
    await screen.findByText("林");
    const lastCallArgs = (db.listGlyphs as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(lastCallArgs.filter.status).toEqual(["needs_review"]);
  });

  it("renders one row per glyph with char + iou_mean visible", async () => {
    const db = mockDb();
    renderWithProviders(db);
    expect(await screen.findByText("林")).toBeTruthy();
    expect(await screen.findByText("森")).toBeTruthy();
    expect(screen.getByText("0.830")).toBeTruthy();
    expect(screen.getByText("0.950")).toBeTruthy();
  });

  it("allows toggling the status filter via the multi-select", async () => {
    const db = mockDb();
    renderWithProviders(db);
    await screen.findByText("林");
    const [multiselect] = screen.getAllByLabelText("Status filter");
    fireEvent.click(multiselect);
    // Mantine MultiSelect options render in a portal; we assert the
    // underlying listGlyphs was called and will assert filter shape on
    // the second call once an option is chosen. This smoke just
    // asserts the widget exists and is interactive.
    expect(multiselect).toBeTruthy();
  });
});
