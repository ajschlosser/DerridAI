/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function scan(page: Page, include: string) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await new AxeBuilder({ page }).include(include).withTags(TAGS).analyze();
    } catch (error) {
      await page.waitForTimeout(400);
    }
  }
}

test("Records workspace header has no WCAG 2.2 AA violations", async ({ page }) => {
  await page.goto("/iframe.html?id=records-workspace-header--default&viewMode=story");
  await expect(page.locator(".records-hero").first()).toBeVisible();
  const results = await scan(page, ".records-hero");
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
});

test("Records file rail has no WCAG 2.2 AA violations", async ({ page }) => {
  await page.goto("/iframe.html?id=records-file-rail--populated&viewMode=story");
  await expect(page.locator(".records-file-rail").first()).toBeVisible();
  const results = await scan(page, ".records-file-rail");
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
});
