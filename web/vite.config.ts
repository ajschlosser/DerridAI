/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const root = dirname(fileURLToPath(import.meta.url));
const pkg = JSON.parse(readFileSync(join(root, "package.json"), "utf8")) as {
  version: string;
  codename: string;
};

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
const appCodename = pkg.codename;
const appGitCommit = gitCommit();
const releaseLabel = appCodename ? `${appVersion} - ${appCodename}` : appVersion;
const versionLabel = appGitCommit ? `${releaseLabel} (${appGitCommit})` : releaseLabel;

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
    __APP_CODENAME__: JSON.stringify(appCodename),
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
      "/api/ws": { target: "ws://127.0.0.1:8000", ws: true },
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
