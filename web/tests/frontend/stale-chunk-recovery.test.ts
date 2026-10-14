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

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  claimStaleChunkRecovery,
  currentEntryScriptPath,
  deploymentShellChanged,
  entryScriptPathFromHtml,
  isLikelyStaleModuleError,
} from "../../src/router/staleChunkRecovery";

function memoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem(key: string) {
      return values.get(key) ?? null;
    },
    setItem(key: string, value: string) {
      values.set(key, value);
    },
  };
}

function shell(entry: string) {
  return `<!doctype html><html><head><script type="module" src="${entry}"></script></head></html>`;
}

describe("stale deployment chunk recovery", () => {
  it.each([
    "Failed to fetch dynamically imported module: /assets/ProvidersView-old.js",
    "error loading dynamically imported module: /assets/ProvidersView-old.js",
    "Importing a module script failed.",
    "Unable to preload CSS for /assets/view-old.css",
    "Loading chunk 123 failed.",
    "ChunkLoadError: route chunk unavailable",
  ])("recognises route-asset load failures: %s", (message) => {
    expect(isLikelyStaleModuleError(new Error(message))).toBe(true);
  });

  it("does not classify ordinary application errors as stale chunks", () => {
    expect(isLikelyStaleModuleError(new Error("API returned 503"))).toBe(false);
    expect(isLikelyStaleModuleError(new Error("Permission denied"))).toBe(false);
  });

  it("allows one reload per build in the recovery window", () => {
    const storage = memoryStorage();
    expect(claimStaleChunkRecovery(storage, 1_000, "build-a")).toBe(true);
    expect(claimStaleChunkRecovery(storage, 2_000, "build-a")).toBe(false);
    expect(claimStaleChunkRecovery(storage, 2_000, "build-b")).toBe(true);
    expect(claimStaleChunkRecovery(storage, 32_001, "build-b")).toBe(true);
  });

  it("compares the running entry bundle with the current server shell", async () => {
    const doc = new DOMParser().parseFromString(shell("/assets/index-old.js"), "text/html");
    expect(currentEntryScriptPath(doc)).toBe("/assets/index-old.js");
    expect(entryScriptPathFromHtml(shell("/assets/index-new.js"))).toBe("/assets/index-new.js");

    const changed = await deploymentShellChanged(
      async () => new Response(shell("/assets/index-new.js"), { status: 200 }),
      doc,
    );
    expect(changed).toBe(true);

    const unchanged = await deploymentShellChanged(
      async () => new Response(shell("/assets/index-old.js"), { status: 200 }),
      doc,
    );
    expect(unchanged).toBe(false);
  });

  it("serves the HTML shell uncached while keeping hashed assets immutable", () => {
    const nginx = readFileSync("nginx.conf", "utf8");
    expect(nginx).toContain("location = /index.html");
    expect(nginx).toContain('Cache-Control "no-cache, no-store, must-revalidate"');
    expect(nginx).toContain("location /assets/");
    expect(nginx).toContain('Cache-Control "public, max-age=31536000, immutable"');
    expect(nginx).toContain("try_files $uri =404");
  });
});
