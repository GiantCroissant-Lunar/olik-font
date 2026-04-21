import { z } from "zod";

export const RuleTraceAlternative = z.object({
  rule_id: z.string(),
  would_output: z.record(z.unknown()),
}).strict();

export const RuleTraceEntry = z.object({
  decision_id: z.string(),
  rule_id: z.string(),
  inputs: z.record(z.unknown()),
  output: z.record(z.unknown()),
  alternatives: z.array(RuleTraceAlternative),
  applied_at: z.string(),
}).strict();
export type RuleTraceEntry = z.infer<typeof RuleTraceEntry>;

export const RuleTrace = z.object({
  decisions: z.array(RuleTraceEntry),
}).strict();
export type RuleTrace = z.infer<typeof RuleTrace>;
