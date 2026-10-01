/* Copyright 2026 Aaron John Schlosser, PhD. */
import { readdirSync, readFileSync } from "node:fs";
import { basename, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const specPath = resolve(webRoot, "tests/e2e/legacy-dom-baseline.spec.ts");
const snapshotDir = resolve(webRoot, "tests/e2e/legacy-dom-baseline.spec.ts-snapshots");
const spec = readFileSync(specPath, "utf8");
const scenarioNames = new Set(
  [...spec.matchAll(/\bname:\s*"([^"]+)"/g)].map((match) => match[1]),
);

// These scenarios deliberately use semantic assertions rather than committed DOM baselines.
const semanticOnly = new Set([
  "jobs-dock-running",
  "jobs-dock-running-dark",
  "records-loaded",
  "records-query",
  "records-sort-work",
  "records-sort-work-descending",
  "records-select-row",
  "records-select-page",
  "records-columns-dialog",
  "annotations-empty",
  "annotations-loaded",
  "annotations-recent",
  "annotations-search",
  "annotations-remove",
  "works-loaded",
  "works-search",
  "works-actions-menu",
  "works-open-records",
  "works-open-records-needing-review",
  "annotations-open-work",
]);

const hasDynamicJobDetails = spec.includes("dialog-job-details-${index}");
const files = readdirSync(snapshotDir).filter((file) => /\.(?:html|txt)$/.test(file));
const stale = [];

for (const file of files) {
  const extension = file.endsWith(".txt") ? ".txt" : ".html";
  const name = basename(file, extension);
  const dynamic = hasDynamicJobDetails && /^dialog-job-details-\d+$/.test(name);
  const active = scenarioNames.has(name) || dynamic;

  // Computed-style scenarios no longer compare snapshot files. Any committed
  // .txt baseline is therefore dead, even if a styles-* scenario still exists.
  if (
    extension === ".txt" ||
    !active ||
    semanticOnly.has(name) ||
    name.startsWith("records-")
  ) {
    stale.push(file);
  }
}

if (stale.length) {
  console.error("Unreferenced legacy DOM snapshots found:");
  for (const file of stale.sort()) console.error(`  - ${file}`);
  process.exit(1);
}

console.log(`Legacy snapshot guard: ${files.length} committed baselines are referenced.`);
