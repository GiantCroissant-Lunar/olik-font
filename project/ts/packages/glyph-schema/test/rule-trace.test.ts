import { describe, expect, test } from "vitest";
import { RuleTrace } from "../src/rule-trace.js";

describe("RuleTrace", () => {
  test("parses a minimal trace", () => {
    const raw = {
      decisions: [
        {
          decision_id: "d:明:composition",
          rule_id: "compose.preset_from_plan",
          inputs: { has_preset_in_plan: true, preset: "left_right" },
          output: { adapter: "preset" },
          alternatives: [],
          applied_at: "2026-04-21T00:00:00Z",
        },
      ],
    };
    const parsed = RuleTrace.parse(raw);
    expect(parsed.decisions).toHaveLength(1);
    expect(parsed.decisions[0].rule_id).toBe("compose.preset_from_plan");
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
