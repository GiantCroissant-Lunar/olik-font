import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { AuthoredDecomposition } from "../../packages/glyph-schema/src/authored-decomp.js";

const AUTHORED_ROOT = resolve(__dirname, "../../../py/data/glyph_decomp");

export default defineConfig({
  plugins: [
    react(),
    {
      name: "authored-save-writer",
      configureServer(server) {
        server.middlewares.use("/api/authored-save", async (req, res) => {
          if (req.method !== "POST") {
            res.statusCode = 405;
            res.end("method not allowed");
            return;
          }

          const chunks: Buffer[] = [];
          req.on("data", (chunk) => chunks.push(Buffer.from(chunk)));
          req.on("end", async () => {
            try {
              const payload = AuthoredDecomposition.parse(
                JSON.parse(Buffer.concat(chunks).toString("utf-8")),
              );
              await mkdir(AUTHORED_ROOT, { recursive: true });
              const target = resolve(AUTHORED_ROOT, `${payload.char}.json`);
              await writeFile(target, `${JSON.stringify(payload, null, 2)}\n`, "utf-8");
              res.setHeader("content-type", "application/json");
              res.end(JSON.stringify({ ok: true, path: target }));
            } catch (error) {
              res.statusCode = 400;
              res.end((error as Error).message);
            }
          });
        });
      },
    },
  ],
  resolve: {
    alias: {
      "@olik/glyph-schema": resolve(__dirname, "../../packages/glyph-schema/src/index.ts"),
      "@olik/glyph-viz":    resolve(__dirname, "../../packages/glyph-viz/src/index.ts"),
      "@olik/flow-nodes":   resolve(__dirname, "../../packages/flow-nodes/src/index.ts"),
      "@olik/rule-viz":     resolve(__dirname, "../../packages/rule-viz/src/index.ts"),
      "@olik/glyph-loader": resolve(
        __dirname,
        "../../packages/glyph-loader/src/load-url.ts",
      ),
    },
  },
  server: { host: "127.0.0.1", port: 5176 },
  test: { environment: "jsdom", globals: true },
});
