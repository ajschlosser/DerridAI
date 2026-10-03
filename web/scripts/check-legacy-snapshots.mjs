/* Copyright 2026 Aaron John Schlosser, PhD. */
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
