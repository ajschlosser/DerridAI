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

import { readdirSync, readFileSync } from "node:fs";
import { basename, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const specPath = resolve(webRoot, "tests/e2e/legacy-dom-baseline.spec.ts");
const snapshotDir = resolve(webRoot, "tests/e2e/legacy-dom-baseline.spec.ts-snapshots");
const spec = readFileSync(specPath, "utf8");
const scenarioNames = new Set([...spec.matchAll(/\bname:\s*"([^"]+)"/g)].map((match) => match[1]));

// These scenarios deliberately use semantic assertions rather than committed DOM baselines.
const nonSnapshotScenarios = new Set([
  "jobs-dock-running",
  "jobs-dock-running-dark",
  // Ported to Vue components; the scenario asserts the dialog's title instead.
  "dialog-works-separate",
  "dialog-works-edit-metadata",
  "dialog-works-remove-work",
  "dialog-works-populate-all",
  "dialog-merge",
  "dialog-ocr-cleanup",
  "record-edit-sheet",
  "dialog-job-details-0",
  "dialog-job-details-1",
  "dialog-job-details-2",
  "dialog-job-results-review",
]);

const hasDynamicJobDetails = spec.includes("dialog-job-details-${index}");
const files = readdirSync(snapshotDir).filter((file) => /\.(?:html|txt)$/.test(file));
const stale = [];

for (const file of files) {
  const extension = file.endsWith(".txt") ? ".txt" : ".html";
  const name = basename(file, extension);
  const dynamic = hasDynamicJobDetails && /^dialog-job-details-\d+$/.test(name);
  const active = scenarioNames.has(name) || dynamic;

  // Computed-style baselines are retired. Every remaining HTML snapshot must
  // correspond to an active scenario that still reaches toMatchSnapshot().
  if (extension === ".txt" || !active || nonSnapshotScenarios.has(name)) {
    stale.push(file);
  }
}

if (stale.length) {
  console.error("Unreferenced legacy DOM snapshots found:");
  for (const file of stale.sort()) console.error(`  - ${file}`);
  process.exit(1);
}

console.log(`Legacy snapshot guard: ${files.length} committed baselines are referenced.`);
