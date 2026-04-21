import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

// Alias workspace deps to source so tests run on a fresh clone without a
// prior `pnpm build`. Same pattern as glyph-loader's vitest.config.ts.
export default defineConfig({
  resolve: {
    alias: {
      "@olik/glyph-schema": resolve(__dirname, "../glyph-schema/src/index.ts"),
      "@olik/glyph-viz":    resolve(__dirname, "../glyph-viz/src/index.ts"),
    },
  },
  test: { environment: "jsdom", globals: true },
  esbuild: { jsx: "automatic" },
});
