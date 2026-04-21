import * as React from "react";
import { ReactFlow, type Edge, type Node } from "@xyflow/react";
import { NODE_TYPE_KEYS, PrototypeNode } from "@olik/flow-nodes";
import { useAppState } from "../state.js";

const nodeTypes = { [NODE_TYPE_KEYS.prototype]: PrototypeNode };

export const PrototypeLibraryBrowser: React.FC = () => {
  const [state] = useAppState();

  if (!state.library) {
    return <div style={{ padding: 24 }}>no library</div>;
  }

  const protoIds = Object.keys(state.library.prototypes);
  const usageCount = new Map<string, number>();
  const hostingChars = new Map<string, Set<string>>();

  for (const [ch, rec] of Object.entries(state.records)) {
    for (const inst of rec.component_instances) {
      usageCount.set(inst.prototype_ref, (usageCount.get(inst.prototype_ref) ?? 0) + 1);
      const set = hostingChars.get(inst.prototype_ref) ?? new Set<string>();
      set.add(ch);
      hostingChars.set(inst.prototype_ref, set);
    }
  }

  const cols = 4;
  const dx = 220;
  const dy = 280;
  const nodes: Node[] = protoIds.map((id, i) => ({
    id,
    position: { x: 60 + (i % cols) * dx, y: 60 + Math.floor(i / cols) * dy },
    type: NODE_TYPE_KEYS.prototype,
    data: {
      prototype: state.library!.prototypes[id]!,
      instanceCount: usageCount.get(id) ?? 0,
      hostingChars: [...(hostingChars.get(id) ?? [])],
    },
  }));

  const edges: Edge[] = [];

  return (
    <div style={{ height: "calc(100vh - 160px)" }}>
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView />
    </div>
  );
};
