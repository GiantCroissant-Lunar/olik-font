import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

// Resolve @olik/glyph-schema to source during tests so a fresh clone's
// `pnpm -r test` works without requiring `pnpm --filter @olik/glyph-schema
// build` first. Production builds still consume the compiled dist via the
// package.json exports map.
export default defineConfig({
  resolve: {
    alias: {
      "@olik/glyph-schema": resolve(__dirname, "../glyph-schema/src/index.ts"),
    },
  },
});
