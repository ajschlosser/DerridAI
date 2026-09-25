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
