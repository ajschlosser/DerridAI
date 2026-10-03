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

import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import { DERRIDAI_LICENSE_HEADER } from "./scripts/apply-copyright-header.mjs";

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
        banner: DERRIDAI_LICENSE_HEADER,
      },
    },
  },
});
