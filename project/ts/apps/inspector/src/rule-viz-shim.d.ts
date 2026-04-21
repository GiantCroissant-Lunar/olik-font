declare module "@olik/rule-viz" {
  import type * as React from "react";
  import type { RuleTrace } from "@olik/glyph-schema";

  export const RuleNode: React.ComponentType<any>;

  export function traceToHighlight(trace: RuleTrace): {
    firedRuleIds: Set<string>;
    alternativeRuleIds: Set<string>;
  };
}
