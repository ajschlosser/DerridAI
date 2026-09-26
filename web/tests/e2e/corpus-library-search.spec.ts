/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import { mockBackend } from "./support/mock-backend";
import { runAxe } from "./support/axe";

async function expectWcag2AA(page: Page, include: string) {
  const results = await runAxe(page, (builder) =>
    builder.include(include).withTags(["wcag2a", "wcag2aa"]),
  );
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
}

// Finding a text in Project Gutenberg or Wikisource, in the real app against the mock API: results follow the query,
// a Wikisource chapter offers its whole work, and everything works from the keyboard.
const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

test.beforeEach(({}, info) =>
  test.skip(info.project.name !== "chromium-desktop", "Runs once, at its own viewport."),
);

async function openLibrary(page: Page) {
  await mockBackend(page);
  await page.goto(`${APP}/pdf`);
  await page.locator(".review-grid").waitFor();
  await page
    .getByRole("button", { name: /new build/i })
    .first()
    .click();
  await page.getByRole("button", { name: /search digital libraries/i }).click();
  return page.getByRole("dialog", { name: /search digital libraries/i });
}

test("results follow the query and can be imported from the keyboard", async ({ page }) => {
  const dialog = await openLibrary(page);
  const box = dialog.getByRole("searchbox");
  await expect(box).toBeFocused();
  await page.keyboard.type("Rousseau");
  const first = dialog.getByRole("button", { name: /Import The Social Contract/ });
  await expect(first).toBeVisible();
  await page.keyboard.press("ArrowDown");
  await expect(first).toBeFocused();
  await expectWcag2AA(page, ".library-search");
});

test("a Wikisource chapter offers its whole work, in the chosen language", async ({ page }) => {
  const dialog = await openLibrary(page);
  await dialog.getByRole("tab", { name: "Wikisource" }).click();
  await dialog.getByLabel("Wikisource edition").selectOption("fr");
  await dialog.getByRole("searchbox").fill("Rousseau");
  await expect(dialog.getByText("fr.wikisource.org", { exact: false })).toBeVisible();
  const row = dialog.getByRole("listitem").filter({ hasText: "Les Confessions" });
  await expect(row.getByRole("button", { name: /Import whole work/ })).toBeVisible();
  await expect(row.getByRole("button", { name: /Only this part: Les Confessions/ })).toBeVisible();
  await expect(dialog.getByRole("listitem").filter({ hasText: "Du contrat social" })).toContainText(
    "2 matching parts",
  );
  await expectWcag2AA(page, ".library-search");
});
