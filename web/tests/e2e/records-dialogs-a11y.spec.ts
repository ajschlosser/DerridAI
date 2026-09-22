/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// The Records table dialogs and the shared page header, in light and dark, against WCAG 2.0 to
// 2.2 A and AA.
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const STORIES = [
  "ui-table-columns-dialog--with-widths",
  "ui-table-columns-dialog--choose-and-order",
  "records-subset-dialog--open",
  "records-subset-condition--with-value",
  "records-subset-condition--valueless",
];

async function scan(page: Page) {
  // Storybook's a11y addon runs axe as each story loads; wait out its run rather than racing it.
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
      // Dialog stories teleport to <body>; the condition story renders in the story root.
      await expect(page.locator("[role=dialog], .subset-condition").first()).toBeVisible();
      await page.waitForTimeout(300);
      const { violations } = await scan(page);
      expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
    });
  }
}

test("the subset dialog is operable from the keyboard alone", async ({ page }) => {
  await page.goto("/iframe.html?id=records-subset-dialog--open&viewMode=story");
  const dialog = page.getByRole("dialog", { name: "Create JSONL subset" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("status")).toContainText("3 of 4 source records match");
  // Tab to "Add group" and press it; the new group's controls are labelled.
  await dialog.getByRole("button", { name: "Add group" }).focus();
  await page.keyboard.press("Enter");
  await expect(dialog.getByRole("group", { name: "Group (item 2)" })).toBeVisible();
  await expect(dialog.getByLabel("Field for condition 1 of item 2")).toBeVisible();
  // Focus stays inside the modal dialog.
  for (let i = 0; i < 40; i++) await page.keyboard.press("Tab");
  expect(await dialog.evaluate((node) => node.contains(document.activeElement))).toBe(true);
});
