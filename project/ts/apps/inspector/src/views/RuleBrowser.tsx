import * as React from "react";
import { ReactFlow, type Edge, type Node } from "@xyflow/react";
import { RuleNode, traceToHighlight } from "@olik/rule-viz";
import { useAppState } from "../state.js";

interface RulesJson {
  decomposition: Array<{ id: string; when: Record<string, unknown>; action: Record<string, unknown> }>;
  composition: Array<{ id: string; when: Record<string, unknown>; action: Record<string, unknown> }>;
  prototype_extraction: Array<{ id: string; when: Record<string, unknown>; action: Record<string, unknown> }>;
}

const nodeTypes = { "olik-rule": RuleNode };

export const RuleBrowser: React.FC = () => {
  const [state] = useAppState();
  const [rules, setRules] = React.useState<RulesJson | null>(null);

  React.useEffect(() => {
    fetch("/data/rules.json")
      .then((r) => r.json())
      .then(setRules)
      .catch(() => setRules(null));
  }, []);

  if (!rules) {
    return (
      <div style={{ padding: 24 }}>
        load rules.json (re-run <code>olik build</code>)
      </div>
    );
  }

  const trace = state.traces[state.char];
  const highlight = trace
    ? traceToHighlight(trace)
    : { firedRuleIds: new Set<string>(), alternativeRuleIds: new Set<string>() };

  const buckets: Array<[keyof RulesJson, number]> = [
    ["decomposition", 60],
    ["composition", 380],
    ["prototype_extraction", 700],
  ];
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  for (const [bucket, x] of buckets) {
    rules[bucket].forEach((rule, i) => {
      const id = `${bucket}:${rule.id}`;
      nodes.push({
        id,
        position: { x, y: 60 + i * 160 },
        type: "olik-rule",
        data: {
          ruleId: rule.id,
          bucket,
          when: rule.when,
          action: rule.action,
          firedInView: highlight.firedRuleIds.has(rule.id),
          isAlternativeInView: highlight.alternativeRuleIds.has(rule.id),
        },
      });

      if (i > 0) {
        edges.push({
          id: `${bucket}-fallback-${i}`,
          source: `${bucket}:${rules[bucket][i - 1]!.id}`,
          target: id,
        });
      }
    });
  }

  return (
    <div style={{ height: "calc(100vh - 160px)" }}>
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView />
    </div>
  );
};
