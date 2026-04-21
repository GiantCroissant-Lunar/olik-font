import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@olik/glyph-loader": resolve(
        __dirname,
        "../../packages/glyph-loader/src/load-url.ts",
      ),
    },
  },
  server: { port: 5173 },
  test: { environment: "jsdom", globals: true },
});
