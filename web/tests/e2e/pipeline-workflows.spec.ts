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

import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function scan(page: Page, include: string) {
  const results = await new AxeBuilder({ page }).include(include).withTags(TAGS).analyze();
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
}

const stories = [
  ["pipelines-workflow-contract--reviewer-evidence", ".workflow-contract"],
  ["pipelines-strategies-workspace--all-strategies", ".strategies-workspace"],
  ["pipelines-definition-navigator--evidence-workflow", ".pipeline-definition-navigator"],
  ["pipelines-definition-navigator--multiple-versions", ".pipeline-definition-navigator"],
  ["pipelines-version-editor-panel--inspect-only-stage", ".editor-card"],
  ["pipelines-definition-detail--assigned", ".pipeline-detail"],
  ["pipelines-definition-header--draft-inspect-only", ".definition-header"],
  ["pipelines-operational-health--populated", ".metrics-workspace"],
  ["pipelines-executions-workspace--default", ".executions-workspace"],
  ["pipelines-execution-list--default", ".execution-list"],
  ["pipelines-stage-inspector--executed-with-fallback", ".stage-inspector"],
  ["pipelines-stage-navigator--default", ".stage-navigator"],
  ["pipelines-strategy-inspector--used", ".strategy-inspector"],
  ["pipelines-comparison-result--benchmark-with-drift-warning", ".comparison-result"],
  ["pipelines-comparison-workspace--default", ".comparison-workspace"],
  ["pipelines-evidence-comparison-result--default", ".comparison-result"],
  ["pipelines-benchmark-case-list--default", ".case-list"],
  ["pipelines-studio-help-dialog--open", "[role=dialog]"],
  ["pipelines-data-type-chip--all-types", ".type-chip"],
  ["pipelines-stage-inputs-and-outputs--connected", ".ports"],
  ["pipelines-stage-inputs-and-outputs--not-connected", ".ports"],
  ["pipelines-stage-inputs-and-outputs--wrong-type", ".ports"],
  ["pipelines-stage-palette--after-retrieval", "[role=dialog]"],
  ["pipelines-new-pipeline-dialog--workflow-chosen", "[role=dialog]"],
  ["pipelines-analysis-panel--partly-measured", ".analysis"],
  ["pipelines-analysis-panel--never-run", ".analysis"],
  ["pipelines-definition-editor--with-analysis", ".pipeline-editor"],
  ["pipelines-strategy-inspector--with-observed-latency", ".strategy-inspector"],
] as const;

for (const scheme of ["light", "dark"] as const) {
  for (const [id, root] of stories) {
    test(`${id} has no WCAG 2.2 AA violations (${scheme})`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
      await page.goto(`/iframe.html?id=${id}&viewMode=story`);
      await page.evaluate((value) => {
        document.documentElement.dataset.colorScheme = value;
      }, scheme);
      await expect(page.locator(root).first()).toBeVisible();
      await scan(page, root);
    });
  }
}

test("strategy search and selection work from the keyboard", async ({ page }) => {
  await page.goto("/iframe.html?id=pipelines-strategies-workspace--all-strategies&viewMode=story");
  const search = page.getByRole("searchbox", { name: "Search strategies" });
  await search.focus();
  await page.keyboard.type("cross-encoder");
  const row = page.locator('tr[data-strategy="rerank.cross_encoder"]');
  await expect(row).toBeVisible();
  await expect(row).toContainText("Relevance ranking only — does not establish support");

  await row.getByRole("button").focus();
  await page.keyboard.press("Enter");
  const inspector = page.locator(".strategy-inspector");
  await expect(inspector).toContainText("rerank.cross_encoder");
  await expect(
    inspector.getByRole("button", { name: /Research — current production chain/ }),
  ).toBeVisible();
});

test("advanced strategy filters are reachable and counted", async ({ page }) => {
  await page.goto("/iframe.html?id=pipelines-strategies-workspace--all-strategies&viewMode=story");
  const filters = page.getByRole("button", { name: "Filters" });
  await expect(filters).toHaveAttribute("aria-expanded", "false");
  await filters.focus();
  await page.keyboard.press("Enter");
  await expect(filters).toHaveAttribute("aria-expanded", "true");
  await page.getByLabel("Computation").selectOption("deterministic");
  await expect(page.getByRole("button", { name: "Filters (1)" })).toBeVisible();
});

test("pipeline versions group under one pipeline and expand from the keyboard", async ({
  page,
}) => {
  await page.goto(
    "/iframe.html?id=pipelines-definition-navigator--multiple-versions&viewMode=story",
  );
  const toggle = page.getByRole("button", { name: "3 versions" });
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await expect(page.locator(".version-choice")).toHaveCount(3);
  await toggle.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".version-choice")).toHaveCount(0);
});

test("used-for and status filters are compact selects", async ({ page }) => {
  await page.goto(
    "/iframe.html?id=pipelines-definition-navigator--evidence-workflow&viewMode=story",
  );
  await expect(page.getByLabel("Used for")).toHaveValue("evidence");
  await expect(page.locator(".pipeline-choice")).toHaveCount(2);
});

test("clone editor explains disabled operations for the selected stage", async ({ page }) => {
  await page.goto(
    "/iframe.html?id=pipelines-version-editor-panel--inspect-only-stage&viewMode=story",
  );
  await expect(page.getByText("Purpose is fixed for this version.")).toBeVisible();
  await page.locator(".stage-row", { hasText: "source-diversity" }).click();
  await expect(page.locator(".stage-fit-note").first()).toContainText("stays inspect-only");
  await page.getByText("Advanced").click();
  await page.getByLabel(/Show operations this workflow cannot run/).check();
  await expect(page.locator('option[value="llm.generate_answer"]').first()).toHaveAttribute(
    "disabled",
    "",
  );
});

test("the graph and the stage list select the same stage", async ({ page }) => {
  await page.goto(
    "/iframe.html?id=pipelines-version-editor-panel--reviewer-evidence-clone&viewMode=story",
  );
  await page.locator(".diagram-node", { hasText: "support" }).click();
  await expect(page.locator(".stage-inspector-editor h4")).toHaveText("support");
  await expect(page.locator(".stage-row[aria-current=true]")).toContainText("support");
});

test("the diagram lens switches what each stage shows, from the keyboard", async ({ page }) => {
  await page.goto("/iframe.html?id=pipelines-definition-editor--with-analysis&viewMode=story");
  const lens = page.getByRole("group", { name: "What the diagram shows on each stage" });
  const latency = lens.getByRole("button", { name: "Latency" });
  await expect(latency).toHaveAttribute("aria-pressed", "false");
  await latency.focus();
  await page.keyboard.press("Enter");
  await expect(latency).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".diagram-node", { hasText: "≈ 400 ms" })).toBeVisible();
  await lens.getByRole("button", { name: "Complexity" }).click();
  await expect(page.locator(".diagram-node", { hasText: "O(q + d·log N + k)" })).toBeVisible();
});

test("an input's source is chosen from a list of what can legitimately feed it", async ({
  page,
}) => {
  await page.goto("/iframe.html?id=pipelines-definition-editor--with-analysis&viewMode=story");
  await page.locator(".stage-row", { hasText: "b" }).first().click();
  const ports = page.locator(".ports");
  await expect(ports).toContainText("Currently: a → candidates");
  const source = ports.getByLabel("Source").first();
  await expect(source.locator("option")).toHaveCount(2);
  await expect(source.locator("optgroup")).toHaveAttribute("label", "Earlier stages");
});

test("the stage palette offers only stages that fit, and can show the rest with a reason", async ({
  page,
}) => {
  await page.goto("/iframe.html?id=pipelines-stage-palette--after-retrieval&viewMode=story");
  const dialog = page.getByRole("dialog", { name: "Add a stage" });
  await expect(dialog.locator("strong", { hasText: "Cross-encoder reranker" })).toBeVisible();
  await expect(dialog.locator("strong", { hasText: "Research answer generation" })).toHaveCount(0);
  await dialog.getByLabel("Only stages that fit this position").uncheck();
  await expect(dialog.locator("strong", { hasText: "Research answer generation" })).toBeVisible();
  await expect(dialog).toContainText("Takes Context packet, but dense provides Candidate set.");
});

test("analysis tabs move with the arrow keys and show complexity in plain terms", async ({
  page,
}) => {
  await page.goto("/iframe.html?id=pipelines-analysis-panel--partly-measured&viewMode=story");
  const latency = page.getByRole("tab", { name: "Latency" });
  await latency.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Complexity" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.locator(".complexity")).toContainText("Grows with the collection");
});
