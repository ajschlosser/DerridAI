// Copyright 2026 Aaron John Schlosser, PhD.
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const root = dirname(fileURLToPath(import.meta.url));
const pkg = JSON.parse(readFileSync(join(root, "package.json"), "utf8")) as { version: string };

function gitCommit(): string {
  const fromEnv = String(process.env.GIT_COMMIT || process.env.SOURCE_COMMIT || "").trim();
  if (fromEnv) return fromEnv.split(/\s+/)[0].slice(0, 40);
  try {
    return execSync("git rev-parse --short HEAD", { encoding: "utf8", cwd: root }).trim();
  } catch {
    return "";
  }
}

const appVersion = pkg.version;
const appGitCommit = gitCommit();
const versionLabel = appGitCommit ? `${appVersion} (${appGitCommit})` : appVersion;

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
    __APP_GIT_COMMIT__: JSON.stringify(appGitCommit),
  },
  plugins: [
    vue(),
    {
      name: "derridai-version-title",
      transformIndexHtml(html) {
        return html.replace(
          /<title>DerridAI [^<]+<\/title>/,
          `<title>DerridAI ${versionLabel}</title>`,
        );
      },
    },
  ],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  build: {
    target: "es2022",
    sourcemap: false,
    chunkSizeWarningLimit: 850,
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ["vue", "vue-router", "pinia"],
          pdf: ["pdfjs-dist/legacy/build/pdf.mjs"],
        },
      },
    },
  },
});
