import { describe, it, expect, vi } from "vitest";
import { makeQueries } from "../queries.js";
import { InvalidTransition } from "../types.js";

function mockSurreal(getRows: unknown, updateSpy: ReturnType<typeof vi.fn>) {
  return {
    query: vi.fn().mockImplementation((sql: string) => {
      if (sql.startsWith("SELECT * FROM glyph")) {
        return {
          collect: async () => [[getRows]],
        };
      }
      if (sql.startsWith("UPDATE type::record")) {
        return {
          collect: async () => {
            updateSpy(sql);
            return [[{}]];
          },
        };
      }
      throw new Error(`unexpected SQL: ${sql}`);
    }),
  } as unknown as Parameters<typeof makeQueries>[0];
}

describe("updateGlyphStatus", () => {
  it("writes status + review_note + reviewed_at + reviewed_by on a valid transition", async () => {
    const updateSpy = vi.fn();
    const raw = mockSurreal([{ char: "林", status: "needs_review" }], updateSpy);
    const db = makeQueries(raw);
    await db.updateGlyphStatus("林", {
      newStatus: "verified",
      reviewNote: "looks good",
      reviewedBy: "alice",
    });
    expect(updateSpy).toHaveBeenCalledTimes(1);
    const callArgs = (raw.query as ReturnType<typeof vi.fn>).mock.calls.at(-1)!;
    expect(callArgs[1].patch.status).toBe("verified");
    expect(callArgs[1].patch.review_note).toBe("looks good");
    expect(callArgs[1].patch.reviewed_by).toBe("alice");
    expect(typeof callArgs[1].patch.reviewed_at).toBe("string");
  });

  it("defaults reviewedBy to 'browser' and accepts null review_note", async () => {
    const updateSpy = vi.fn();
    const raw = mockSurreal([{ char: "林", status: "needs_review" }], updateSpy);
    const db = makeQueries(raw);
    await db.updateGlyphStatus("林", { newStatus: "failed_extraction" });
    const callArgs = (raw.query as ReturnType<typeof vi.fn>).mock.calls.at(-1)!;
    expect(callArgs[1].patch.reviewed_by).toBe("browser");
    expect(callArgs[1].patch.review_note).toBeNull();
  });

  it("throws InvalidTransition when the target is not in VALID_TRANSITIONS[current]", async () => {
    const updateSpy = vi.fn();
    // verified → unsupported_op is not allowed under the mirrored Python rules
    // (see Plan 10 spec §6.5).
    const raw = mockSurreal([{ char: "林", status: "verified" }], updateSpy);
    const db = makeQueries(raw);
    await expect(
      db.updateGlyphStatus("林", { newStatus: "unsupported_op" }),
    ).rejects.toBeInstanceOf(InvalidTransition);
    expect(updateSpy).not.toHaveBeenCalled();
  });

  it("throws when the glyph does not exist", async () => {
    const updateSpy = vi.fn();
    const raw = mockSurreal(undefined, updateSpy);
    const db = makeQueries(raw);
    await expect(
      db.updateGlyphStatus("XX", { newStatus: "verified" }),
    ).rejects.toThrow(/not found/);
    expect(updateSpy).not.toHaveBeenCalled();
  });
});
