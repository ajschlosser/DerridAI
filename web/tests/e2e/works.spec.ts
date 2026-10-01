/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mockBackend } from "./support/mock-backend";

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

const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;
const WORKS_WORKFLOW_ROWS = [
  {
    record_id: "works-1",
    work: "Of Grammatology",
    page_start: 3,
    text: "The sign and divinity have the same place and time of birth.",
    needs_review: false,
  },
  {
    record_id: "works-2",
    work: "Of Grammatology",
    page_start: 4,
    text: "There is nothing outside the text.",
    needs_review: true,
  },
  {
    record_id: "works-3",
    work: "On Cosmopolitanism and Forgiveness",
    page_start: 5,
    text: "What then would such a concept be?",
    needs_review: false,
  },
];

async function openWorksWorkflow(page: Page) {
  await mockBackend(page, { role: "admin" });
  await page.goto(APP);
  await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await page.setInputFiles("#fileInput", {
    name: "works-workflow.jsonl",
    mimeType: "application/x-ndjson",
    buffer: Buffer.from(WORKS_WORKFLOW_ROWS.map((row) => JSON.stringify(row)).join("\n")),
  });
  await expect(page.getByText("Loaded 3 records")).toBeVisible({ timeout: 10_000 });
  await page
    .locator(".shell-sidebar")
    .getByRole("button", { name: "Works", exact: true })
    .first()
    .click();
  await expect(page.locator("#works-page-title")).toBeVisible();
}

test("Works modern workflow covers search, actions, and Search handoffs", async ({ page }) => {
  await openWorksWorkflow(page);

  const search = page.locator("#worksSearch");
  await search.fill("Cosmopolitanism");
  await expect(page.locator(".works-card")).toHaveCount(1);
  await expect(page.getByText("On Cosmopolitanism and Forgiveness").first()).toBeVisible();
  await search.fill("");

  await page
    .locator("main")
    .getByRole("button", { name: /^Actions for / })
    .first()
    .click();
  await expect(page.getByRole("menuitem", { name: "Edit metadata" })).toBeVisible();
  await page.keyboard.press("Escape");

  await page
    .getByRole("button", { name: /^Open \d+ records for Of Grammatology$/ })
    .click();
  await expect(page.locator("#search-page-title")).toBeVisible();
  await expect(page.getByText("Work equals Of Grammatology")).toBeVisible();
  await expect(page.getByText("Needs review equals true")).toHaveCount(0);

  await page
    .locator(".shell-sidebar")
    .getByRole("button", { name: "Works", exact: true })
    .first()
    .click();
  await expect(page.locator("#works-page-title")).toBeVisible();
  await page
    .getByRole("button", { name: /records needing review for Of Grammatology/ })
    .click();
  await expect(page.locator("#search-page-title")).toBeVisible();
  await expect(page.getByText("Work equals Of Grammatology")).toBeVisible();
  await expect(page.getByText("Needs review equals true")).toBeVisible();
});
