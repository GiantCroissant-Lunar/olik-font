import * as React from "react";
import type { RuleTrace } from "@olik/glyph-schema";
import { traceToHighlight } from "./types.js";

export interface TraceHighlightSummaryProps {
  trace: RuleTrace;
}

export const TraceHighlightSummary: React.FC<TraceHighlightSummaryProps> = ({ trace }) => {
  const hi = traceToHighlight(trace);

  return (
    <div style={{ fontSize: 12, fontFamily: "monospace", padding: 8 }}>
      <div>decisions: {trace.decisions.length}</div>
      <div>fired: {[...hi.firedRuleIds].join(", ")}</div>
      <div>considered (not fired): {[...hi.alternativeRuleIds].join(", ") || "—"}</div>
    </div>
  );
};
