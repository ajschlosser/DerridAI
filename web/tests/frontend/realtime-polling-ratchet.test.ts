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

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

// Ratchet for docs/REALTIME.md: pages read server data through useDataQuery (or followResource for
// job/build progress) and are refreshed by realtime events, so they neither poll nor offer manual
// reload buttons. Remove entries as pages migrate; never add one.
const SRC = join(__dirname, "../../src");

// Local clocks that make no requests.
const INTERVAL_ALLOWED = new Set([
  "components/OperationsPanel.vue",
  "components/CorpusModelActivity.vue",
]);
// Pages and dialogs that still carry a manual refresh control (see docs/REALTIME.md).
const REFRESH_CONTROL_ALLOWED = new Set([
  "components/OperationsPanel.vue",
  "components/capture/CorpusCaptureDialog.vue",
  "components/research/ResearchRunsDrawer.vue",
  "components/system-data/SystemDataAdvanced.vue",
  "components/system-data/SystemDataDatabases.vue",
  "components/JobReviewDialog.vue",
  "domain/operationsPanelBridge.ts",
  "views/SourcesView.vue",
]);

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return name === "realtime" ? [] : sources(path);
    return /\.(vue|ts)$/.test(name) && !name.endsWith(".stories.ts") ? [path] : [];
  });
}

function offenders(pattern: RegExp, allowed: Set<string>): string[] {
  return sources(SRC)
    .map((path) => ({
      file: relative(SRC, path).replace(/\\/g, "/"),
      text: readFileSync(path, "utf8"),
    }))
    .filter(({ file, text }) => pattern.test(text) && !allowed.has(file))
    .map(({ file }) => file);
}

describe("realtime polling ratchet", () => {
  it("does not add setInterval timers outside realtime/", () => {
    expect(offenders(/\bsetInterval\s*\(/, INTERVAL_ALLOWED)).toEqual([]);
  });

  it("does not add manual refresh controls to data pages", () => {
    expect(
      offenders(
        /['"`](?:ui|common|dialog|review|metadata_memory)\.refresh['"`]/,
        REFRESH_CONTROL_ALLOWED,
      ),
    ).toEqual([]);
  });
});
