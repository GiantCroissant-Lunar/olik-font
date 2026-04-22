import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@olik/glyph-db": resolve(__dirname, "../../packages/glyph-db/src/index.ts"),
      "@olik/glyph-schema": resolve(
        __dirname,
        "../../packages/glyph-schema/src/index.ts",
      ),
    },
  },
  server: { port: 5174 },
  test: { environment: "jsdom", globals: true },
});
