/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import { mockBackend } from "./support/mock-backend";
import { runAxe } from "./support/axe";

const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

test.beforeEach(({}, info) =>
  test.skip(info.project.name !== "chromium-desktop", "Runs once, at its own viewport."),
);

async function expectWcag2AA(page: Page, include: string) {
  const results = await runAxe(page, (builder) =>
    builder.include(include).withTags(["wcag2a", "wcag2aa"]),
  );
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
}

test("Sources opens Corpus Capture with provider-backed options", async ({ page }) => {
  await mockBackend(page);
  await page.goto(`${APP}/sources`);
  await page.locator(".sources-page").waitFor();

  await expect(page.locator("#sources-title")).toHaveText("Sources");
  await page.locator('[data-action="capture"]').click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const authorSearch = dialog.locator(".author-resolver input[type=search]");
  await authorSearch.fill("Derrida");
  await dialog.locator(".ar-search button[type=submit]").click();

  const person = dialog.locator('[data-qid="Q130631"]');
  await expect(person).toContainText("Jacques Derrida");
  await person.locator('input[type="radio"]').check();
  await dialog.locator('[data-action="next"]').click();

  const options = dialog.locator(".capture-options");
  await expect(options).toBeVisible();
  await expect(options.locator('[data-provider="gutenberg"]')).toBeChecked();
  await expect(options.locator('[data-provider="wikisource"]')).toBeChecked();

  await options.locator('[data-languages="some"]').check();
  await expect(options.locator('[data-language="fr"]')).toBeVisible();
  await expect(options.locator('[data-language="de"]')).toBeVisible();

  await expectWcag2AA(page, ".sources-page");
});
