import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
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
  server: { port: 5173 },
  test: { environment: "jsdom", globals: true },
});
