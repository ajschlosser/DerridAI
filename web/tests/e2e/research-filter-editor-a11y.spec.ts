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

// The Research filter editor in every state, in light and dark, against WCAG 2.0 to 2.2 A and AA.
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const STORIES = [
  "research-filter-editor--empty",
  "research-filter-editor--valid-expression",
  "research-filter-editor--with-document-condition",
  "research-filter-editor--syntax-error",
  "research-filter-editor--server-rejected",
  "research-filter-editor--no-declared-fields",
  "research-filter-editor--indexed-schema-catalog",
];

async function scan(page: Page) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await new AxeBuilder({ page }).withTags(TAGS).analyze();
    } catch (error) {
      if (attempt >= 10 || !String(error).includes("already running")) throw error;
      await page.waitForTimeout(400);
    }
  }
}

for (const scheme of ["light", "dark"] as const) {
  for (const id of STORIES) {
    test(`${id} is WCAG 2.2 AA clean in ${scheme} mode`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
      await page.goto(`/iframe.html?id=${id}&viewMode=story`);
      await page.evaluate((s) => {
        document.documentElement.dataset.colorScheme = s;
      }, scheme);
      await expect(page.locator(".research-filter-editor")).toBeVisible();
      await page.waitForTimeout(600);
      const { violations } = await scan(page);
      expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
    });
  }
}

test("the filter editor is operable from the keyboard and announces results", async ({ page }) => {
  await page.goto("/iframe.html?id=research-filter-editor--interactive&viewMode=story");
  const input = page.getByRole("textbox", { name: "Filter expression" });
  await input.focus();
  await page.keyboard.type('work = "Of Grammatology"');
  const status = page.getByRole("status");
  await expect(status).toContainText("Filter understood.");
  await expect(status).toContainText("The server accepted this filter");
  await expect(page.getByText("View Chroma expression")).toBeVisible();
  await page.getByRole("button", { name: "Insert and" }).focus();
  await page.keyboard.press("Enter");
  await expect(input).toHaveValue('work = "Of Grammatology" and ');
});

for (const scheme of ["light", "dark"] as const) {
  for (const id of ["custom-schema-fields", "model-assisted-proposal", "model-unavailable"]) {
    test(`scope ${id} is accessible at narrow width in ${scheme}`, async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 900 });
      await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
      await page.goto(`/iframe.html?id=research-scope-suggestions--${id}&viewMode=story`);
      await expect(page.locator(".research-scope")).toBeVisible();
      if (id !== "custom-schema-fields") {
        await page.getByRole("button", { name: "Suggest scope with Ollama" }).focus();
        await page.keyboard.press("Enter");
        if (id === "model-unavailable") await expect(page.getByRole("alert")).toBeVisible();
        else await expect(page.getByRole("status")).toContainText("Model-assisted proposal");
      }
      const { violations } = await scan(page);
      expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      ).toBe(true);
    });
  }
}
