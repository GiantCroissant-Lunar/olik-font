import * as React from "react";
import {
  type GlyphRecord,
  type PrototypeLibrary,
  type RefinementMode,
} from "@olik/glyph-schema";

type SupersededSource = "mmh" | "animcjk" | "cjk-decomp";

type SerializedPartitionNode = {
  prototype_ref: string;
  mode?: RefinementMode;
  source_stroke_indices?: number[];
  children?: SerializedPartitionNode[];
  replacement_proto_ref?: string;
};

type AuthoredDecompositionT = {
  schema_version: "0.1";
  char: string;
  supersedes: SupersededSource;
  rationale: string;
  authored_by: string;
  authored_at: string;
  partition: SerializedPartitionNode[];
};

export interface AuthoringNode {
  id: string;
  prototype_ref?: string;
  mode?: RefinementMode;
  input_adapter?: string;
  decomp_source?: Record<string, unknown>;
  source_stroke_indices: number[];
  replacement_proto_ref?: string;
  children: AuthoringNode[];
}

export interface AuthoringDocument {
  char: string;
  supersedes: SupersededSource;
  rationale: string;
  authored_by: string;
  root: AuthoringNode;
}

interface AuthoringPanelProps {
  document: AuthoringDocument;
  library: PrototypeLibrary | null;
  selectedNodeId: string | null;
  onDocumentChange: (document: AuthoringDocument) => void;
}

interface PrototypePickerProps {
  label: string;
  library: PrototypeLibrary;
  onPick: (prototypeRef: string) => void;
}

const PANEL_WIDTH = 360;

export const AuthoringPanel: React.FC<AuthoringPanelProps> = ({
  document: authoringDocument,
  library,
  selectedNodeId,
  onDocumentChange,
}) => {
  const [refineCount, setRefineCount] = React.useState(2);
  const [replacePickerOpen, setReplacePickerOpen] = React.useState(false);
  const [childPickerNodeId, setChildPickerNodeId] = React.useState<string | null>(null);
  const [saveStatus, setSaveStatus] = React.useState<string | null>(null);
  const selectedNode = selectedNodeId
    ? findAuthoringNode(authoringDocument.root, selectedNodeId)
    : null;
  const selectedLabel =
    selectedNode?.prototype_ref?.replace("proto:", "") ??
    (selectedNode?.id === authoringDocument.root.id
      ? authoringDocument.char
      : selectedNode?.id ?? null);
  const prototypeOptions = library ? Object.values(library.prototypes) : [];
  const canEditSelectedNode = selectedNode !== null;
  const isRootSelection = selectedNode?.id === authoringDocument.root.id;

  React.useEffect(() => {
    setReplacePickerOpen(false);
    setChildPickerNodeId(null);
    setSaveStatus(null);
  }, [selectedNodeId]);

  async function handleSave(): Promise<void> {
    const payload = serializeAuthoringDocument(authoringDocument);
    const body = `${JSON.stringify(payload, null, 2)}\n`;

    try {
      if (shouldPostToLocalWriter(window.location)) {
        const response = await fetch("/api/authored-save", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body,
        });
        if (!response.ok) {
          const message = await response.text();
          throw new Error(message || `save failed: ${response.status}`);
        }
        const result = (await response.json()) as { path?: string };
        setSaveStatus(result.path ? `saved to ${result.path}` : "saved");
        return;
      }

      const blob = new Blob([body], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = window.document.createElement("a");
      link.href = url;
      link.download = `${payload.char}.json`;
      link.click();
      URL.revokeObjectURL(url);
      setSaveStatus(`downloaded ${payload.char}.json`);
    } catch (error) {
      setSaveStatus((error as Error).message);
    }
  }

  function updateNode(nodeId: string, updater: (node: AuthoringNode) => AuthoringNode): void {
    onDocumentChange(updateAuthoringNode(authoringDocument, nodeId, updater));
  }

  return (
    <aside
      style={{
        width: PANEL_WIDTH,
        borderLeft: "1px solid #cbd5e1",
        background:
          "linear-gradient(180deg, rgba(248,250,252,0.98), rgba(241,245,249,0.98))",
        padding: 18,
        overflowY: "auto",
      }}
    >
      <div style={{ display: "grid", gap: 14 }}>
        <div>
          <div style={{ fontSize: 11, color: "#475569", textTransform: "uppercase" }}>
            Authoring Panel
          </div>
          <div style={{ fontSize: 28, fontFamily: "serif", color: "#0f172a" }}>
            {authoringDocument.char}
          </div>
        </div>

        <label style={{ display: "grid", gap: 6, fontSize: 13, color: "#0f172a" }}>
          Authored by
          <input
            value={authoringDocument.authored_by}
            onChange={(event) =>
              onDocumentChange({
                ...authoringDocument,
                authored_by: event.target.value || "inspector",
              })
            }
            style={inputStyle}
          />
        </label>

        <label style={{ display: "grid", gap: 6, fontSize: 13, color: "#0f172a" }}>
          Supersedes
          <select
            value={authoringDocument.supersedes}
            onChange={(event) =>
              onDocumentChange({
                ...authoringDocument,
                supersedes: event.target.value as SupersededSource,
              })
            }
            style={inputStyle}
          >
            <option value="mmh">mmh</option>
            <option value="animcjk">animcjk</option>
            <option value="cjk-decomp">cjk-decomp</option>
          </select>
        </label>

        <label style={{ display: "grid", gap: 6, fontSize: 13, color: "#0f172a" }}>
          Rationale
          <textarea
            value={authoringDocument.rationale}
            onChange={(event) =>
              onDocumentChange({
                ...authoringDocument,
                rationale: event.target.value,
              })
            }
            rows={4}
            style={{ ...inputStyle, resize: "vertical" }}
          />
        </label>

        <div
          style={{
            border: "1px solid #cbd5e1",
            borderRadius: 14,
            padding: 14,
            background: "#ffffff",
            display: "grid",
            gap: 10,
          }}
        >
          <div style={{ fontSize: 11, color: "#475569", textTransform: "uppercase" }}>
            Selected Node
          </div>
          {selectedLabel ? (
            <>
              <div style={{ fontSize: 22, fontFamily: "serif", color: "#0f172a" }}>{selectedLabel}</div>
              <div style={{ fontFamily: "monospace", fontSize: 11, color: "#475569" }}>
                {selectedNode?.id}
              </div>
              <div style={{ fontSize: 12, color: "#475569" }}>
                Mode: {selectedNode?.mode ?? "keep"}
                {" · "}
                Strokes: {selectedNode?.source_stroke_indices.length ?? 0}
              </div>
            </>
          ) : (
            <div style={{ fontSize: 13, color: "#64748b" }}>Select a node in the tree to edit it.</div>
          )}

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              disabled={!canEditSelectedNode || isRootSelection}
              onClick={() => {
                if (!selectedNodeId || isRootSelection) return;
                updateNode(selectedNodeId, (node) => ({
                  ...node,
                  mode: "keep",
                  replacement_proto_ref: undefined,
                  children: [],
                  decomp_source: { ...(node.decomp_source ?? {}), source: "authored" },
                }));
              }}
              style={actionButtonStyle("#0f766e")}
            >
              Keep
            </button>

            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <input
                type="number"
                min={1}
                value={refineCount}
                onChange={(event) => setRefineCount(Math.max(1, Number(event.target.value) || 1))}
                style={{ ...inputStyle, width: 68 }}
              />
              <button
                type="button"
                disabled={!canEditSelectedNode || library === null || prototypeOptions.length === 0}
                onClick={() => {
                  if (!selectedNodeId || !library) return;
                  onDocumentChange(
                    refineAuthoringNode(authoringDocument, selectedNodeId, refineCount, library),
                  );
                  setReplacePickerOpen(false);
                }}
                style={actionButtonStyle("#b45309")}
              >
                Refine into N
              </button>
            </div>

            <button
              type="button"
              disabled={!canEditSelectedNode || isRootSelection || library === null}
              onClick={() => setReplacePickerOpen((open) => !open)}
              style={actionButtonStyle("#7e22ce")}
            >
              Replace with…
            </button>
          </div>

          {replacePickerOpen && selectedNodeId && selectedNode && library ? (
            <PrototypePicker
              label="Pick replacement prototype"
              library={library}
              onPick={(prototypeRef) => {
                updateNode(selectedNodeId, (node) => ({
                  ...node,
                  mode: "replace",
                  replacement_proto_ref: prototypeRef,
                  children: [],
                  decomp_source: { ...(node.decomp_source ?? {}), source: "authored" },
                }));
                setReplacePickerOpen(false);
              }}
            />
          ) : null}

          {selectedNode && selectedNode.children.length > 0 && library ? (
            <div style={{ display: "grid", gap: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#0f172a" }}>Children</div>
              {selectedNode.children.map((child, index) => (
                <div
                  key={child.id}
                  style={{
                    border: "1px solid #e2e8f0",
                    borderRadius: 10,
                    padding: 10,
                    background: "#f8fafc",
                    display: "grid",
                    gap: 8,
                  }}
                >
                  <div style={{ fontSize: 12, color: "#0f172a" }}>
                    Child {index + 1}: {child.prototype_ref?.replace("proto:", "") ?? child.id}
                  </div>
                  <div style={{ fontFamily: "monospace", fontSize: 11, color: "#475569" }}>
                    {child.prototype_ref ?? "unassigned"}
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      setChildPickerNodeId((openId) => (openId === child.id ? null : child.id))
                    }
                    style={secondaryButtonStyle}
                  >
                    Pick prototype
                  </button>
                  {childPickerNodeId === child.id ? (
                    <PrototypePicker
                      label={`Choose prototype for child ${index + 1}`}
                      library={library}
                      onPick={(prototypeRef) => {
                        updateNode(child.id, (node) => ({
                          ...node,
                          prototype_ref: prototypeRef,
                          decomp_source: { ...(node.decomp_source ?? {}), source: "authored" },
                        }));
                        setChildPickerNodeId(null);
                      }}
                    />
                  ) : null}
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <button type="button" onClick={() => void handleSave()} style={saveButtonStyle}>
          Save
        </button>

        {saveStatus ? (
          <div
            data-testid="authoring-save-status"
            style={{
              fontSize: 12,
              color: saveStatus.startsWith("saved") || saveStatus.startsWith("downloaded")
                ? "#166534"
                : "#b91c1c",
            }}
          >
            {saveStatus}
          </div>
        ) : null}
      </div>
    </aside>
  );
};

export function createAuthoringDocument(record: GlyphRecord): AuthoringDocument {
  const strokeIndexMap = new Map<string, number[]>();

  for (const stroke of record.stroke_instances ?? []) {
    const bucket = strokeIndexMap.get(stroke.instance_id) ?? [];
    bucket.push(stroke.order);
    strokeIndexMap.set(stroke.instance_id, bucket);
  }

  for (const values of strokeIndexMap.values()) {
    values.sort((left, right) => left - right);
  }

  return {
    char: record.glyph_id,
    supersedes: inferSupersededSource(record),
    rationale: `Authored override for ${record.glyph_id} created in inspector.`,
    authored_by: "inspector",
    root: record.layout_tree
      ? layoutTreeToAuthoringNode(record.layout_tree, strokeIndexMap)
      : {
          id: `draft:${record.glyph_id}`,
          mode: "keep",
          source_stroke_indices: [],
          children: [],
        },
  };
}

export function serializeAuthoringDocument(
  document: AuthoringDocument,
): AuthoredDecompositionT {
  return assertAuthoredDecomposition({
    schema_version: "0.1",
    char: document.char,
    supersedes: document.supersedes,
    rationale: document.rationale.trim(),
    authored_by: document.authored_by.trim(),
    authored_at: new Date().toISOString(),
    partition: document.root.children.map(serializeAuthoringNode),
  });
}

export function findAuthoringNode(
  node: AuthoringNode,
  nodeId: string,
): AuthoringNode | null {
  if (node.id === nodeId) {
    return node;
  }
  for (const child of node.children) {
    const match = findAuthoringNode(child, nodeId);
    if (match) {
      return match;
    }
  }
  return null;
}

export function updateAuthoringNode(
  document: AuthoringDocument,
  nodeId: string,
  updater: (node: AuthoringNode) => AuthoringNode,
): AuthoringDocument {
  return {
    ...document,
    root: mapAuthoringNode(document.root, nodeId, updater),
  };
}

export function refineAuthoringNode(
  document: AuthoringDocument,
  nodeId: string,
  childCount: number,
  library: PrototypeLibrary,
): AuthoringDocument {
  const prototypeIds = Object.keys(library.prototypes).sort();
  if (prototypeIds.length === 0) {
    return document;
  }

  return updateAuthoringNode(document, nodeId, (node) => {
    const slices = splitStrokeIndices(node.source_stroke_indices, childCount);
    const nextChildren = Array.from({ length: childCount }, (_, index) => {
      const prior = node.children[index];
      return {
        id: `${node.id}::child_${index + 1}`,
        prototype_ref: prior?.prototype_ref ?? prototypeIds[index % prototypeIds.length],
        mode: "keep" as const,
        input_adapter: "authored",
        decomp_source: { source: "authored" },
        source_stroke_indices: slices[index] ?? [],
        replacement_proto_ref: undefined,
        children: [],
      };
    });

    return {
      ...node,
      mode: node.id === document.root.id && node.prototype_ref === undefined ? node.mode : "refine",
      replacement_proto_ref: undefined,
      children: nextChildren,
      decomp_source: { ...(node.decomp_source ?? {}), source: "authored" },
    };
  });
}

export function shouldPostToLocalWriter(locationLike: Pick<Location, "hostname" | "protocol">): boolean {
  return (
    locationLike.protocol.startsWith("http") &&
    (locationLike.hostname === "127.0.0.1" || locationLike.hostname === "localhost")
  );
}

function layoutTreeToAuthoringNode(
  node: GlyphRecord["layout_tree"],
  strokeIndexMap: Map<string, number[]>,
): AuthoringNode {
  const children = (node.children ?? []).map((child) =>
    layoutTreeToAuthoringNode(child, strokeIndexMap),
  );
  const ownStrokeIndices = strokeIndexMap.get(node.id) ?? [];
  const childStrokeIndices = children.flatMap((child) => child.source_stroke_indices);
  const sourceStrokeIndices = [...new Set([...ownStrokeIndices, ...childStrokeIndices])].sort(
    (left, right) => left - right,
  );

  return {
    id: node.id,
    prototype_ref: node.prototype_ref,
    mode: node.mode ?? "keep",
    input_adapter: node.input_adapter,
    decomp_source: node.decomp_source as Record<string, unknown> | undefined,
    source_stroke_indices: sourceStrokeIndices,
    replacement_proto_ref: undefined,
    children,
  };
}

function serializeAuthoringNode(node: AuthoringNode): SerializedPartitionNode {
  if (!node.prototype_ref) {
    throw new Error(`authoring node ${node.id} is missing prototype_ref`);
  }
  const payload: SerializedPartitionNode = {
    prototype_ref: node.prototype_ref,
    mode: node.mode ?? "keep",
  };
  if (node.source_stroke_indices.length > 0) {
    payload.source_stroke_indices = node.source_stroke_indices;
  }
  if (node.children.length > 0) {
    payload.children = node.children.map(serializeAuthoringNode);
  }
  if (node.mode === "replace" && node.replacement_proto_ref) {
    payload.replacement_proto_ref = node.replacement_proto_ref;
  }
  return payload;
}

function mapAuthoringNode(
  node: AuthoringNode,
  nodeId: string,
  updater: (node: AuthoringNode) => AuthoringNode,
): AuthoringNode {
  if (node.id === nodeId) {
    return updater(node);
  }
  if (node.children.length === 0) {
    return node;
  }
  return {
    ...node,
    children: node.children.map((child) => mapAuthoringNode(child, nodeId, updater)),
  };
}

function inferSupersededSource(record: GlyphRecord): SupersededSource {
  const layoutSource =
    (record.layout_tree?.decomp_source as
      | { source?: string | null; adapter?: string | null }
      | undefined) ?? undefined;
  const recordSource = (record.source as { decomp_source?: string | null } | undefined) ?? undefined;
  const candidates = [
    layoutSource?.source,
    layoutSource?.adapter,
    recordSource?.decomp_source,
  ];
  for (const candidate of candidates) {
    if (candidate === "mmh" || candidate === "animcjk" || candidate === "cjk-decomp") {
      return candidate;
    }
  }
  return "mmh";
}

function splitStrokeIndices(strokeIndices: number[], parts: number): number[][] {
  const count = Math.max(1, parts);
  const slices: number[][] = [];
  let cursor = 0;

  for (let index = 0; index < count; index += 1) {
    const remainingItems = strokeIndices.length - cursor;
    const remainingParts = count - index;
    const sliceSize = remainingParts > 0 ? Math.ceil(remainingItems / remainingParts) : 0;
    slices.push(strokeIndices.slice(cursor, cursor + sliceSize));
    cursor += sliceSize;
  }

  return slices;
}

function assertAuthoredDecomposition(
  payload: AuthoredDecompositionT,
): AuthoredDecompositionT {
  if (payload.schema_version !== "0.1") {
    throw new Error("schema_version must be 0.1");
  }
  if (payload.char.length !== 1) {
    throw new Error("char must be a single character");
  }
  if (payload.rationale.trim().length === 0) {
    throw new Error("rationale must not be empty");
  }
  if (payload.authored_by.trim().length === 0) {
    throw new Error("authored_by must not be empty");
  }
  if (payload.partition.length === 0) {
    throw new Error("partition must contain at least one node");
  }
  if (!/^\d{4}-\d{2}-\d{2}T/.test(payload.authored_at)) {
    throw new Error("authored_at must be ISO-8601");
  }
  payload.partition.forEach(assertSerializedPartitionNode);
  return payload;
}

function assertSerializedPartitionNode(node: SerializedPartitionNode): void {
  if (!/^proto:[A-Za-z0-9_]+$/.test(node.prototype_ref)) {
    throw new Error(`invalid prototype_ref: ${node.prototype_ref}`);
  }
  if (node.mode === "replace" && !node.replacement_proto_ref) {
    throw new Error("replace nodes require replacement_proto_ref");
  }
  if (node.mode !== "replace" && node.replacement_proto_ref) {
    throw new Error("replacement_proto_ref is only allowed for replace nodes");
  }
  if (node.replacement_proto_ref && !/^proto:[A-Za-z0-9_]+$/.test(node.replacement_proto_ref)) {
    throw new Error(`invalid replacement_proto_ref: ${node.replacement_proto_ref}`);
  }
  if (node.source_stroke_indices && node.source_stroke_indices.length === 0) {
    throw new Error("source_stroke_indices must not be empty when present");
  }
  node.children?.forEach(assertSerializedPartitionNode);
}

const inputStyle: React.CSSProperties = {
  border: "1px solid #cbd5e1",
  borderRadius: 10,
  padding: "8px 10px",
  fontSize: 13,
  color: "#0f172a",
  background: "#ffffff",
};

function actionButtonStyle(color: string): React.CSSProperties {
  return {
    border: `1px solid ${color}`,
    color,
    background: "#ffffff",
    borderRadius: 999,
    padding: "7px 12px",
    fontSize: 12,
    cursor: "pointer",
  };
}

const secondaryButtonStyle: React.CSSProperties = {
  border: "1px solid #cbd5e1",
  color: "#334155",
  background: "#ffffff",
  borderRadius: 999,
  padding: "6px 12px",
  fontSize: 12,
  cursor: "pointer",
};

const saveButtonStyle: React.CSSProperties = {
  border: "none",
  color: "#ffffff",
  background: "linear-gradient(135deg, #0284c7, #0f766e)",
  borderRadius: 14,
  padding: "12px 16px",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
};

const PrototypePicker: React.FC<PrototypePickerProps> = ({ label, library, onPick }) => {
  const [query, setQuery] = React.useState("");
  const prototypes = Object.values(library.prototypes)
    .slice()
    .sort((left, right) => left.name.localeCompare(right.name, "zh-Hant"));
  const filtered = prototypes.filter((prototype) => {
    const haystack = `${prototype.name} ${prototype.id}`.toLowerCase();
    return haystack.includes(query.trim().toLowerCase());
  });

  return (
    <div
      style={{
        border: "1px dashed #cbd5e1",
        borderRadius: 10,
        padding: 10,
        display: "grid",
        gap: 8,
        background: "#ffffff",
      }}
    >
      <div style={{ fontSize: 12, color: "#0f172a" }}>{label}</div>
      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Filter by name or proto id"
        style={inputStyle}
      />
      <div style={{ display: "grid", gap: 6, maxHeight: 220, overflowY: "auto" }}>
        {filtered.map((prototype) => (
          <button
            key={prototype.id}
            type="button"
            onClick={() => onPick(prototype.id)}
            style={{
              border: "1px solid #cbd5e1",
              borderRadius: 10,
              background: "#f8fafc",
              color: "#0f172a",
              padding: "8px 10px",
              textAlign: "left",
              cursor: "pointer",
            }}
          >
            <div style={{ fontSize: 18, fontFamily: "serif" }}>{prototype.name}</div>
            <div style={{ fontFamily: "monospace", fontSize: 11, color: "#475569" }}>
              {prototype.id}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};
