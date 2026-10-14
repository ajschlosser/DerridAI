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
import { mockBackend } from "./support/mock-backend";

const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

function records(count: number) {
  return Array.from({ length: count }, (_, index) => ({
    record_id: `derrida-grammatology-${String(index + 1).padStart(5, "0")}`,
    work: "Of Grammatology",
    document_author: "Jacques Derrida",
    page_start: index + 1,
    page_end: index + 1,
    text: `Passage ${index + 1}. The sign and divinity have the same place and time of birth.`,
    speaker: "Derrida",
    needs_review: false,
  }));
}

/** Load a small corpus, open Search, and switch it to the corpus-database scope. */
async function openDatabaseSearch(page: Page) {
  await mockBackend(page);
  await page.goto(`${APP}/`);
  await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await page.setInputFiles("#fileInput", {
    name: "search-loading.jsonl",
    mimeType: "application/x-ndjson",
    buffer: Buffer.from(
      records(6)
        .map((row) => JSON.stringify(row))
        .join("\n"),
    ),
  });
  await expect(page.getByText("Loaded 6 records")).toBeVisible({ timeout: 10_000 });
  await page
    .locator("nav, aside")
    .getByRole("button", { name: "Search", exact: true })
    .first()
    .click();
  await expect(page.locator("#search-page-title")).toBeVisible();
  await page
    .locator(".search-scope-switch")
    .getByRole("button", { name: /Corpus database/ })
    .click();
  await expect(page.locator(".search-run-button")).toBeVisible();
}

test("a pending query neither keeps the previous results nor reports zero matches", async ({
  page,
}, info) => {
  test.skip(info.project.name !== "chromium-desktop", "Runs once.");
  await openDatabaseSearch(page);

  let release!: () => void;
  let gate = new Promise<void>((done) => {
    release = done;
  });
  let payload = [
    { id: "db-1", distance: 0.1, record: { record_id: "db-1", work: "Dissemination" } },
  ];
  await page.route("**/api/stores/*/search", async (route) => {
    await gate;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ results: payload }),
    });
  });

  const results = page.locator(".search-results-panel");
  const query = page.locator(".search-command-input input");
  await query.fill("sign");
  await page.locator(".search-run-button").click();
  await expect(results).toContainText("Searching");
  await expect(results).not.toContainText("No matching records");
  release();
  await expect(results).toContainText("Dissemination");

  // Editing the input must not make the results of the last submitted query look current.
  await expect(page.locator(".search-results-identity")).toHaveCount(0);
  await query.fill("divinity");
  await expect(page.locator(".search-results-identity")).toContainText("sign");

  // A second query must not leave the first query's rows standing in as its result.
  gate = new Promise<void>((done) => {
    release = done;
  });
  payload = [{ id: "db-2", distance: 0.2, record: { record_id: "db-2", work: "Margins" } }];
  await page.locator(".search-run-button").click();
  await expect(results).toContainText("Searching");
  await expect(results).not.toContainText("Dissemination");
  release();
  await expect(results).toContainText("Margins");
  await expect(page.locator(".search-results-identity")).toHaveCount(0);
});

test("database result columns can be resized without a pointing device", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium-desktop", "Runs once.");
  await openDatabaseSearch(page);

  await page.route("**/api/stores/*/search", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        results: [
          {
            id: "db-keyboard-resize",
            distance: 0.1,
            record: {
              record_id: "db-keyboard-resize",
              work: "Of Grammatology",
              text: "Keyboard-resizable result column.",
            },
          },
        ],
      }),
    });
  });

  await page.locator(".search-command-input input").fill("sign");
  await page.locator(".search-run-button").click();
  await expect(page.locator(".search-results-panel")).toContainText("Of Grammatology");
  await page.getByRole("button", { name: "Compact table", exact: true }).click();

  const resizer = page.locator(".search-column-resizer").first();
  await resizer.focus();
  const before = await resizer.evaluate(
    (node) => node.closest("th")?.getBoundingClientRect().width ?? 0,
  );
  await page.keyboard.press("ArrowRight");
  const after = await resizer.evaluate(
    (node) => node.closest("th")?.getBoundingClientRect().width ?? 0,
  );

  expect(after).toBeGreaterThan(before);
  await expect(resizer).toHaveAttribute("aria-keyshortcuts", "ArrowLeft ArrowRight");
});

test("a failed query is reported as a failure, not as an empty corpus", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium-desktop", "Runs once.");
  await openDatabaseSearch(page);

  let offline = true;
  await page.route("**/api/stores/*/search", async (route) => {
    if (!offline)
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          results: [{ id: "db-1", distance: 0.1, record: { record_id: "db-1", work: "Glas" } }],
        }),
      });
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "retrieval backend offline" }),
    });
  });

  const results = page.locator(".search-results-panel");
  await page.locator(".search-command-input input").fill("sign");
  await page.locator(".search-run-button").click();

  const failure = results.locator(".search-results-status");
  await expect(failure).toContainText("retrieval backend offline");
  await expect(failure).toHaveAttribute("role", "alert");
  await expect(page.locator("#search-results-title")).toContainText("Result count unavailable");
  await expect(results).not.toContainText("No matching records");

  const audit = await new AxeBuilder({ page })
    .include(".search-native-page")
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(audit.violations).toEqual([]);

  offline = false;
  await failure.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(results).toContainText("Glas");
  await expect(failure).toHaveCount(0);
});
