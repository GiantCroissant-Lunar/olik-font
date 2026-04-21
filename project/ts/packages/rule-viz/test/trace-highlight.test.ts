import { describe, expect, test } from "vitest";
import { traceToHighlight } from "../src/types.js";

describe("traceToHighlight", () => {
  test("flattens fired + alternatives", () => {
    const hi = traceToHighlight({
      decisions: [
        {
          decision_id: "d:1",
          rule_id: "r1",
          inputs: {},
          output: {},
          alternatives: [{ rule_id: "r2", would_output: {} }],
          applied_at: "t",
        },
        {
          decision_id: "d:2",
          rule_id: "r3",
          inputs: {},
          output: {},
          alternatives: [],
          applied_at: "t",
        },
      ],
    });
    expect([...hi.firedRuleIds].sort()).toEqual(["r1", "r3"]);
    expect([...hi.alternativeRuleIds]).toEqual(["r2"]);
  });
});
