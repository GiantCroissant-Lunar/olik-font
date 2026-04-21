import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      "@olik/glyph-schema": resolve(__dirname, "../glyph-schema/src/index.ts"),
    },
  },
  test: { testTimeout: 30000 },
});
