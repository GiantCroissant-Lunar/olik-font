import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { existsSync, mkdirSync } from "node:fs";

// Serve from <repo-root>/.preview-records/ — Archon workflows drop
// freshly-generated JSON records there (gitignored). Falls back to
// project/schema/examples/ which holds the hand-authored hello-*.json
// from Plan 01. Either path can populate the seed-character UI.
//
// Vite's publicDir is single-valued, but a small middleware below lets
// us layer the two: dropbox first, examples second.
const repoRoot = resolve(__dirname, "../../../..");
const dropbox = resolve(repoRoot, ".preview-records");
const examples = resolve(repoRoot, "project/schema/examples");

if (!existsSync(dropbox)) {
  mkdirSync(dropbox, { recursive: true });
}

export default defineConfig({
  plugins: [
    react(),
    {
      name: "olik-record-fallback",
      configureServer(server) {
        // For any /<file>.json request: try dropbox first, then examples.
        // (publicDir already serves dropbox; this only fires when dropbox
        // doesn't have the file, returning the examples copy if present.)
        server.middlewares.use((req, res, next) => {
          if (!req.url || !req.url.endsWith(".json")) return next();
          const candidate = resolve(examples, req.url.replace(/^\//, ""));
          if (!existsSync(candidate)) return next();
          // Only fall through to examples when the dropbox doesn't have it.
          const dropCandidate = resolve(dropbox, req.url.replace(/^\//, ""));
          if (existsSync(dropCandidate)) return next();
          import("node:fs").then(({ createReadStream }) => {
            res.setHeader("content-type", "application/json");
            createReadStream(candidate).pipe(res);
          });
        });
      },
    },
  ],
  publicDir: dropbox,
  server: { port: 5174, open: true },
});
