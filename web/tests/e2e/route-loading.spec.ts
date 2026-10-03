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
test("slow route modules keep the current page and expose a destination status", async ({
  page,
}) => {
  await mockBackend(page, { role: "admin" });
  await page.goto(APP);
  await expect(page.locator("#appContent main")).toBeVisible();
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/assets/WorksView-*.js", async (route) => {
    await gate;
    await route.continue();
  });
  const current = await page.locator("#appContent main").elementHandle();
  await page.locator(".shell-sidebar").getByRole("button", { name: "Works", exact: true }).click();
  await expect(page.locator(".route-navigation-feedback")).toContainText("Opening Works");
  expect(await current!.evaluate((node) => node.isConnected)).toBe(true);
  release();
  await expect(page.locator("#works-page-title")).toBeVisible();
  await expect(page.locator(".route-navigation-feedback")).toHaveCount(0);
});
test("failed route modules keep the current page and offer reload recovery", async ({ page }) => {
  await mockBackend(page, { role: "admin" });
  await page.goto(APP);
  await expect(page.locator("#appContent main")).toBeVisible();
  await page.route("**/assets/WorksView-*.js", (route) => route.abort("failed"));
  const current = await page.locator("#appContent main").elementHandle();
  await page.locator(".shell-sidebar").getByRole("button", { name: "Works", exact: true }).click();
  const notice = page.locator(".route-navigation-feedback");
  await expect(notice).toContainText("Could not open Works");
  expect(await current!.evaluate((node) => node.isConnected)).toBe(true);
  await expect(notice.getByRole("button", { name: "Retry", exact: true })).toBeVisible();
  await page.unroute("**/assets/WorksView-*.js");
  await notice.getByRole("button", { name: "Reload page", exact: true }).click();
  await expect(page.locator("#works-page-title")).toBeVisible();
});
for (const scheme of ["light", "dark"] as const) {
  test(`navigation error status fits a narrow ${scheme} layout`, async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 640 });
    await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
    await page.goto(
      "/iframe.html?id=shell-routenavigationfeedback--long-destination&viewMode=story",
    );
    const notice = page.locator(".route-navigation-feedback");
    await expect(notice).toBeVisible();
    expect(
      await notice.evaluate((node) => node.getBoundingClientRect().right <= window.innerWidth),
    ).toBe(true);
    const results = await new AxeBuilder({ page })
      .include(".route-navigation-feedback")
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
}
