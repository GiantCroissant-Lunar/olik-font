import type { RuleTrace } from "@olik/glyph-schema";

export interface RuleNodeData {
  ruleId: string;
  bucket: "decomposition" | "composition" | "prototype_extraction";
  when: Record<string, unknown>;
  action: Record<string, unknown>;
  firedBy?: readonly string[];
}

export type TraceHighlight = {
  firedRuleIds: Set<string>;
  alternativeRuleIds: Set<string>;
};

export function traceToHighlight(trace: RuleTrace): TraceHighlight {
  const fired = new Set<string>();
  const alts = new Set<string>();

  for (const d of trace.decisions) {
    fired.add(d.rule_id);
    for (const a of d.alternatives) {
      alts.add(a.rule_id);
    }
  }

  return { firedRuleIds: fired, alternativeRuleIds: alts };
}
