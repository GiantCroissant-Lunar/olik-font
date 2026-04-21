import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

// Resolve @olik/* workspace packages to source during tests so a fresh
// clone's `pnpm -r test` works without needing the dependency packages'
// dist/ to be built first. Production bundling (Remotion / render) still
// goes through package.json exports → dist.
export default defineConfig({
  resolve: {
    alias: {
      "@olik/glyph-schema": resolve(__dirname, "../../packages/glyph-schema/src/index.ts"),
      "@olik/glyph-viz":    resolve(__dirname, "../../packages/glyph-viz/src/index.ts"),
      "@olik/glyph-loader": resolve(__dirname, "../../packages/glyph-loader/src/index.ts"),
    },
  },
});
