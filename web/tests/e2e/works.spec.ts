/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function scan(page: Page, include: string) {
  const results = await new AxeBuilder({ page }).include(include).withTags(TAGS).analyze();
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
}

test("Works library card has no WCAG 2.2 AA violations", async ({ page }) => {
  await page.goto("/iframe.html?id=works-library-card--default&viewMode=story");
  const card = page.locator(".work-library-card");
  await expect(card).toBeVisible();
  await scan(page, ".work-library-card");
});

test("Works overview card has no WCAG 2.2 AA violations", async ({ page }) => {
  await page.goto("/iframe.html?id=works-overview-card--admin&viewMode=story");
  const card = page.locator(".work-overview-card");
  await expect(card).toBeVisible();
  await scan(page, ".work-overview-card");
});

test("Works library card exposes review status and its action menu", async ({ page }) => {
  await page.goto("/iframe.html?id=works-library-card--needs-review&viewMode=story");
  const card = page.locator(".work-library-card");
  await expect(card).toBeVisible();
  await expect(card.getByText("Pending changes")).toBeVisible();

  await card.locator("summary").click();
  await expect(card.getByRole("button", { name: "Edit metadata" })).toBeVisible();
  await expect(card.getByRole("button", { name: "Remove entire work" })).toBeVisible();
});
