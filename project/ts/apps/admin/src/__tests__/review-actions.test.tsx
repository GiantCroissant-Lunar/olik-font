import { afterEach, describe, it, expect, vi } from "vitest";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";

import { ReviewActions } from "../components/ReviewActions.js";

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

describe("ReviewActions", () => {
  it("calls onApprove when Y is pressed", () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();
    render(
      <MantineProvider>
        <ReviewActions
          currentStatus="needs_review"
          reviewNote=""
          onNoteChange={() => {}}
          onApprove={onApprove}
          onReject={onReject}
          onNext={() => {}}
          onPrev={() => {}}
        />
      </MantineProvider>,
    );
    fireEvent.keyDown(window, { key: "y" });
    expect(onApprove).toHaveBeenCalledOnce();
    expect(onReject).not.toHaveBeenCalled();
  });

  it("calls onReject when N is pressed, passing the current review note", () => {
    const onReject = vi.fn();
    const { rerender } = render(
      <MantineProvider>
        <ReviewActions
          currentStatus="needs_review"
          reviewNote="bad placement"
          onNoteChange={() => {}}
          onApprove={() => {}}
          onReject={onReject}
          onNext={() => {}}
          onPrev={() => {}}
        />
      </MantineProvider>,
    );
    fireEvent.keyDown(window, { key: "n" });
    expect(onReject).toHaveBeenCalledWith("bad placement");
    rerender(<></>);
  });

  it("calls onNext/onPrev when J/K are pressed", () => {
    const onNext = vi.fn();
    const onPrev = vi.fn();
    render(
      <MantineProvider>
        <ReviewActions
          currentStatus="needs_review"
          reviewNote=""
          onNoteChange={() => {}}
          onApprove={() => {}}
          onReject={() => {}}
          onNext={onNext}
          onPrev={onPrev}
        />
      </MantineProvider>,
    );
    fireEvent.keyDown(window, { key: "j" });
    fireEvent.keyDown(window, { key: "k" });
    expect(onNext).toHaveBeenCalledOnce();
    expect(onPrev).toHaveBeenCalledOnce();
  });

  it("disables Approve for rows already verified (no self-transition keystroke)", () => {
    const onApprove = vi.fn();
    render(
      <MantineProvider>
        <ReviewActions
          currentStatus="verified"
          reviewNote=""
          onNoteChange={() => {}}
          onApprove={onApprove}
          onReject={() => {}}
          onNext={() => {}}
          onPrev={() => {}}
        />
      </MantineProvider>,
    );
    fireEvent.keyDown(window, { key: "y" });
    expect(onApprove).not.toHaveBeenCalled();
    expect(screen.getByText(/Already verified/i)).toBeTruthy();
  });
});
