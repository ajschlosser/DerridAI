// Copyright 2026 Aaron John Schlosser, PhD.

import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  build: {
    emptyOutDir: false,
    lib: {
      entry: fileURLToPath(new URL("./sdk/src/index.ts", import.meta.url)),
      name: "DerridAI",
      formats: ["iife"],
      fileName: () => "derridai-sdk.js",
    },
    minify: false,
    outDir: fileURLToPath(new URL("../api/app/site_assets", import.meta.url)),
    rollupOptions: {
      output: {
        banner: "/* Copyright 2026 Aaron John Schlosser, PhD. */",
      },
    },
  },
});
