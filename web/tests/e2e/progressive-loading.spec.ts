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

import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mockBackend } from "./support/mock-backend";
const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;
for (const delay of [0, 1000, 5000]) {
  test(`Record remains usable during a ${delay}ms secondary read and refresh`, async ({
    page,
  }, testInfo) => {
    await mockBackend(page, { role: "admin" });
    let requests = 0;
    await page.route("**/api/graphql", async (route) => {
      const body = route.request().postDataJSON() as { operationName?: string };
      if (body.operationName !== "RecordGraph") return route.fallback();
      requests += 1;
      await new Promise((resolve) => setTimeout(resolve, delay));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: { record_graph: null } }),
      });
    });
    await page.goto(APP);
    await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
    await page.waitForLoadState("networkidle");
    await page.setInputFiles("#fileInput", {
      name: "loading.jsonl",
      mimeType: "application/x-ndjson",
      buffer: Buffer.from(
        JSON.stringify({
          record_id: "loading-a",
          work: "Loading pilot",
          text: "Authoritative reading text.",
          source_document_id: "doc-a",
        }),
      ),
    });
    await expect(page.getByText("Loaded 1 records")).toBeVisible();
    const started = Date.now();
    await page.evaluate(() =>
      window.dispatchEvent(
        new CustomEvent("derridai:navigate-native", {
          detail: { path: "/record", runtimeView: "record" },
        }),
      ),
    );
    const pane = page.locator(".record-reading-pane");
    await expect(pane).toContainText("Authoritative reading text.");
    const useful = Date.now() - started;
    const original = await pane.elementHandle();
    await page.getByRole("button", { name: "Edit record", exact: true }).click();
    const dialog = page.locator("dialog.record-edit-sheet");
    await expect(dialog).toBeVisible();
    const input = dialog.locator("textarea").first();
    await input.fill("Unsaved draft");
    await page.evaluate(() => window.dispatchEvent(new Event("derridai:record-updated")));
    await expect(input).toHaveValue("Unsaved draft");
    expect(await original!.evaluate((node) => node.isConnected)).toBe(true);
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
    const find = page.locator(".record-reading-search input");
    await find.fill("reading");
    await expect(find).toBeFocused();
    expect(await original!.evaluate((node) => node.isConnected)).toBe(true);
    await expect.poll(() => requests).toBeGreaterThan(0);
    await page.waitForTimeout(delay + 100);
    expect(await original!.evaluate((node) => node.isConnected)).toBe(true);
    const results = await new AxeBuilder({ page })
      .include(".record-workspace-page")
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(results.violations).toEqual([]);
    await testInfo.attach("readiness", {
      body: JSON.stringify({
        syntheticSecondaryDelayMs: delay,
        firstUsefulMs: useful,
        graphRequests: requests,
      }),
      contentType: "application/json",
    });
  });
}
test("compact French updating status supports narrow layouts and reduced motion", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/iframe.html?id=ui-uiloadingstate--inline-french&viewMode=story");
  await expect(page.getByRole("status")).toContainText("Mise à jour");
  expect(await page.locator("body").evaluate((node) => node.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  const results = await new AxeBuilder({ page })
    .include(".ui-loading-state")
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(results.violations).toEqual([]);
});
