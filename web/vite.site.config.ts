/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 */

import { fileURLToPath, URL } from "node:url";
import vue from "@vitejs/plugin-vue";
import { defineConfig, type Plugin } from "vite";
import { DERRIDAI_LICENSE_HEADER } from "./scripts/apply-copyright-header.mjs";

function inlinePublishedSiteCss(): Plugin {
  return {
    name: "derridai-inline-published-site-css",
    enforce: "post",
    generateBundle(_options, bundle) {
      const cssParts: string[] = [];
      let entryChunk: Extract<(typeof bundle)[string], { type: "chunk" }> | undefined;

      for (const [fileName, item] of Object.entries(bundle)) {
        if (item.type === "asset" && fileName.endsWith(".css")) {
          cssParts.push(String(item.source || ""));
          delete bundle[fileName];
        } else if (item.type === "chunk" && item.isEntry) {
          entryChunk = item;
        }
      }

      if (!entryChunk || !cssParts.length) return;
      const css = cssParts.join("\n");
      const installer = `(()=>{const style=document.createElement("style");style.dataset.derridaiPublishedSiteVue="";style.textContent=${JSON.stringify(
        css,
      )};document.head.appendChild(style)})();\n`;
      entryChunk.code = installer + entryChunk.code;
    },
  };
}

export default defineConfig({
  plugins: [vue(), inlinePublishedSiteCss()],
  // The published runtime is a standalone browser bundle. Vue's distributed
  // runtime contains NODE_ENV guards; replace them at build time rather than
  // leaking a Node-only `process` reference into file:// and static hosting.
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  build: {
    target: "es2022",
    emptyOutDir: false,
    cssCodeSplit: false,
    lib: {
      entry: fileURLToPath(new URL("./site/main.ts", import.meta.url)),
      name: "DerridAIReferenceSite",
      formats: ["iife"],
      fileName: () => "derridai-site.js",
    },
    minify: false,
    outDir: fileURLToPath(new URL("../api/app/site_assets", import.meta.url)),
    rollupOptions: {
      output: {
        banner: DERRIDAI_LICENSE_HEADER,
      },
    },
  },
});
