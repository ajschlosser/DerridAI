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
const stores = {
  stores: [{ name: "loading-collection", count: 3, status: "ready", retrieval_mode: "hybrid" }],
};
const health = {
  available: true,
  mode: "embedded",
  path: "/data/chroma",
  host_path_hint: "./data/chroma",
  data_root: "/data",
  url: null,
  tenant: null,
  database: null,
  token_configured: false,
  writable: true,
  heartbeat_ok: true,
  chroma_version: "1",
  collection_count: 1,
  identity: "Local Chroma",
  error: null,
};
async function start(page: Page) {
  await mockBackend(page, {
    role: "admin",
    fixtures: { "/api/stores": stores, "/api/chroma/connection": health },
  });
  await page.goto(APP);
  await expect(page.locator("#appContent main")).toBeVisible();
  await page.waitForLoadState("networkidle");
}
async function open(page: Page) {
  await page.evaluate(() =>
    window.dispatchEvent(
      new CustomEvent("derridai:navigate-native", {
        detail: { path: "/databases", runtimeView: "vector" },
      }),
    ),
  );
}
test("collection browsing is usable throughout a five-second health delay", async ({
  page,
}, info) => {
  await start(page);
  let release!: () => void;
  const gate = new Promise<void>((done) => {
    release = done;
  });
  await page.route("**/api/chroma/connection", async (route) => {
    await gate;
    await route.fallback();
  });
  const started = Date.now();
  await open(page);
  await expect(page.locator("#vector-page-title")).toBeVisible();
  const frameMs = Date.now() - started;
  await expect(page.locator(".vector-collection-list")).toContainText("loading-collection");
  const contentMs = Date.now() - started;
  await page.locator("#vector-collection-filter").fill("loading");
  await page.waitForTimeout(5000);
  await expect(page.locator("#vector-collection-filter")).toHaveValue("loading");
  await expect(page.locator(".vector-workspace-header")).toContainText(
    "Checking storage connection",
  );
  release();
  await expect(page.locator(".vector-workspace-header")).toContainText("Local Chroma");
  await info.attach("readiness", {
    body: JSON.stringify({ syntheticHealthDelayMs: 5000, frameMs, contentMs }),
    contentType: "application/json",
  });
});
test("collection contents stay pending until their own browse resolves", async ({ page }) => {
  await start(page);
  let release!: () => void;
  const gate = new Promise<void>((done) => {
    release = done;
  });
  await page.route("**/api/graphql", async (route) => {
    const body = route.request().postDataJSON() as { operationName?: string } | null;
    if (body?.operationName === "VectorStoreBrowse") await gate;
    await route.fallback();
  });
  await open(page);
  await page.locator("#vector-section-tab-data").click();
  const works = page.locator("#vector-browse-panel-works");
  await expect(works).toContainText("Loading works");
  await expect(works).not.toContainText("No work metadata");
  release();
  await expect(works).toContainText("No work metadata was found");
});
test("retrieval search distinguishes a pending query from the idle prompt", async ({ page }) => {
  await start(page);
  let release!: () => void;
  const gate = new Promise<void>((done) => {
    release = done;
  });
  await page.route("**/api/stores/*/search", async (route) => {
    await gate;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ results: [] }),
    });
  });
  await open(page);
  await page.locator("#vector-section-tab-retrieval").click();
  const results = page.locator(".vector-search-results");
  await expect(results).toContainText("Search results will appear here.");
  await page.locator("#vector-store-query").fill("trace");
  await page
    .locator("form.vector-search-config")
    .getByRole("button", { name: "Search", exact: true })
    .click();
  await expect(results).toContainText("Searching");
  await expect(results).not.toContainText("Search results will appear here.");
  await expect(results).not.toContainText("No records matched this query.");
  release();
  await expect(results).toContainText("No records matched this query.");
  await expect(results).not.toContainText("Search results will appear here.");
});
test("provider failure stays local and retry does not reload collections", async ({ page }) => {
  await start(page);
  let offline = true;
  let collectionReads = 0;
  await page.route("**/api/stores", async (route) => {
    collectionReads += 1;
    await route.fallback();
  });
  await page.route("**/api/system/researcher-providers", async (route) => {
    if (!offline) return route.fallback();
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "provider discovery offline" }),
    });
  });
  await open(page);
  const region = page.locator(".vector-native-page");
  await expect(region.locator(".vector-collection-list")).toContainText("loading-collection");
  const rail = await region.locator(".vector-collection-list").elementHandle();
  const failure = region.locator(".info.error").filter({ hasText: "provider discovery offline" });
  await expect(failure).toBeVisible();
  await expect(
    region.locator(".vector-workspace-header").getByRole("button", { name: "New", exact: true }),
  ).toBeDisabled();
  const reads = collectionReads;
  offline = false;
  await failure.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(failure).toHaveCount(0);
  expect(collectionReads).toBe(reads);
  expect(await rail!.evaluate((node) => node.isConnected)).toBe(true);
  const result = await new AxeBuilder({ page })
    .include(".vector-native-page")
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(result.violations).toEqual([]);
});
