// Copyright 2026 Aaron John Schlosser, PhD.
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  build: {
    emptyOutDir: false,
    lib: {
      entry: fileURLToPath(new URL("./sdk/src/index.ts", import.meta.url)),
      formats: ["es"],
      fileName: () => "index.js",
    },
    minify: false,
    sourcemap: true,
    outDir: fileURLToPath(new URL("./sdk/dist", import.meta.url)),
    rollupOptions: {
      output: {
        banner: "/* Copyright 2026 Aaron John Schlosser, PhD. */",
      },
    },
  },
});
