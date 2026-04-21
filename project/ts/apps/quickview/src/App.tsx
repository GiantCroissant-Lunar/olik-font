import * as React from "react";
import type { GlyphRecord } from "./types.js";
import { GlyphSvg } from "./glyph-svg.js";
import { DecompTree } from "./decomp-tree.js";

// Seed characters defined by the spec. Records appear in .preview-records/
// (gitignored dropbox) as soon as any Archon workflow's preview node copies
// them in — typically Plan 03's CLI emits them. Fallback path: hand-authored
// hello-record.json from Plan 01 (under project/schema/examples/).
const PICKER = [
  { key: "明", label: "明", path: "/glyph-record-明.json" },
  { key: "清", label: "清", path: "/glyph-record-清.json" },
  { key: "國", label: "國", path: "/glyph-record-國.json" },
  { key: "森", label: "森", path: "/glyph-record-森.json" },
] as const;

export const App: React.FC = () => {
  const [pick, setPick] = React.useState<(typeof PICKER)[number]>(PICKER[0]);
  const [record, setRecord] = React.useState<GlyphRecord | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setRecord(null);
    setError(null);
    fetch(pick.path)
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status} — file not found yet`);
        // Sanity-check: dev server returns index.html as a fallback for missing files.
        const text = await r.text();
        if (text.startsWith("<!DOCTYPE") || text.startsWith("<html")) {
          throw new Error("not built yet — Plan 03's CLI hasn't produced this record");
        }
        return JSON.parse(text) as GlyphRecord;
      })
      .then((data) => setRecord(data))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, [pick]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <header
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid #cbd5e1",
          display: "flex",
          gap: 12,
          alignItems: "center",
        }}
      >
        <h1 style={{ margin: 0, fontSize: 18 }}>olik quickview</h1>
        <span style={{ color: "#64748b", fontSize: 12, fontFamily: "monospace" }}>
          glyph + decomposition tree · live preview of project/schema/examples/*.json
        </span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          {PICKER.map((p) => (
            <button
              key={p.key}
              type="button"
              onClick={() => setPick(p)}
              style={{
                fontSize: 24,
                fontFamily: "serif",
                padding: "4px 12px",
                background: pick.key === p.key ? "#fef3c7" : "#fff",
                border: "1px solid #cbd5e1",
                borderRadius: 4,
                cursor: "pointer",
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      </header>

      <main style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <section
          style={{
            flex: "0 0 520px",
            padding: 20,
            borderRight: "1px solid #cbd5e1",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 12,
          }}
        >
          <h2 style={{ margin: 0, fontSize: 14, color: "#64748b" }}>SVG preview</h2>
          {record ? (
            <GlyphSvg record={record} size={480} />
          ) : error ? (
            <div style={{ color: "#dc2626", fontFamily: "monospace", fontSize: 12 }}>
              <div>load failed for {pick.path}:</div>
              <div>{error}</div>
              <div style={{ marginTop: 12, color: "#64748b" }}>
                Records land in <code>.preview-records/</code> automatically when
                Plan 03's CLI runs. Run <code>task archon:run WF=plan-03-python-compose-cli</code>
                {" "}— it'll copy the freshly built records there as part of its preview node.
              </div>
            </div>
          ) : (
            <div style={{ color: "#64748b" }}>loading…</div>
          )}
        </section>
        <section style={{ flex: 1, padding: 20, display: "flex", flexDirection: "column" }}>
          <h2 style={{ margin: 0, fontSize: 14, color: "#64748b", marginBottom: 8 }}>
            Decomposition tree (xyflow)
          </h2>
          <div style={{ flex: 1 }}>
            {record ? <DecompTree root={record.layout_tree} /> : null}
          </div>
        </section>
      </main>
    </div>
  );
};
