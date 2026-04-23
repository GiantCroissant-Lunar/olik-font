import { describe, expect, test } from "vitest";
import { RuleTrace } from "../src/rule-trace.js";

describe("RuleTrace", () => {
  test("parses a minimal trace", () => {
    const raw = {
      decisions: [
        {
          decision_id: "d:明:composition",
          rule_id: "compose.measured_from_mmh",
          inputs: { compose_source: "measured_transforms" },
          output: { adapter: "measured" },
          alternatives: [],
          applied_at: "2026-04-21T00:00:00Z",
        },
      ],
    };
    const parsed = RuleTrace.parse(raw);
    expect(parsed.decisions).toHaveLength(1);
    expect(parsed.decisions[0].rule_id).toBe("compose.measured_from_mmh");
  });

  test("rejects missing applied_at", () => {
    const raw = {
      decisions: [
        {
          decision_id: "d:test",
          rule_id: "x",
          inputs: {},
          output: {},
          alternatives: [],
        },
      ],
    };
    expect(() => RuleTrace.parse(raw)).toThrow();
  });
});
