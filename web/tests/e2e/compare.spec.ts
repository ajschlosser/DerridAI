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
  for (let attempt = 0; ; attempt++) {
    try {
      return await new AxeBuilder({ page }).include(include).withTags(TAGS).analyze();
    } catch (error) {
      if (attempt >= 10 || !String(error).includes("already running")) throw error;
      await page.waitForTimeout(400);
    }
  }
}

test("Compare picker has no WCAG 2.2 AA violations", async ({ page }) => {
  await page.goto("/iframe.html?id=compare-picker--default&viewMode=story");
  await expect(page.locator(".compare-picker").first()).toBeVisible();
  const results = await scan(page, ".compare-picker");
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
});

test("Compare diff has no WCAG 2.2 AA violations", async ({ page }) => {
  await page.goto("/iframe.html?id=compare-diff--changed&viewMode=story");
  await expect(page.locator(".compare-diff").first()).toBeVisible();
  const results = await scan(page, ".compare-diff");
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
});
