/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function scan(page: Page, include: string) {
  const results = await new AxeBuilder({ page }).include(include).withTags(TAGS).analyze();
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
}

const COMPONENTS = [
  ["works-workspace-header--admin", ".ui-page-header"],
  ["works-workspace-header--researcher", ".ui-page-header"],
  ["works-corpus-context--admin", ".works-context"],
  ["works-library-toolbar--default", ".works-toolbar-shell"],
  ["works-library-card--default", ".works-card"],
  ["works-library-card--selected", ".works-card"],
  ["works-library-list--admin", ".works-list"],
  ["works-library-list--researcher", ".works-list"],
  ["works-library-card--long-title-missing-cover", ".works-card"],
  ["works-library-card--database-unavailable", ".works-card"],
  ["works-overview-card--admin", ".works-inspector"],
  ["works-overview-card--inspector-needs-review", ".works-inspector"],
] as const;

for (const [id, selector] of COMPONENTS) {
  test(`Works story ${id} has no WCAG 2.2 AA violations`, async ({ page }) => {
    await page.goto(`/iframe.html?id=${id}&viewMode=story`);
    await expect(page.locator(selector).first()).toBeVisible();
    await scan(page, selector);
  });
}

test("Works library card selects with the keyboard and exposes review status and its menu", async ({
  page,
}) => {
  await page.goto("/iframe.html?id=works-library-card--needs-review&viewMode=story");
  const card = page.locator(".works-card");
  await expect(card).toBeVisible();
  await expect(card.getByText("Pending changes")).toBeVisible();

  const select = card.getByRole("button", { name: /Adieu to Emmanuel Levinas/ }).first();
  await select.focus();
  await expect(select).toBeFocused();

  await card.getByRole("button", { name: "Actions for Adieu to Emmanuel Levinas" }).click();
  await expect(page.getByRole("menuitem", { name: "Edit metadata" })).toBeVisible();
  await expect(page.getByRole("menuitem", { name: "Remove entire work" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("menuitem", { name: "Edit metadata" })).toHaveCount(0);
});
