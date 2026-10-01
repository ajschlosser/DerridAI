/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mockBackend } from "./support/mock-backend";

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


const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;
const RECORD_WORKFLOW_ROWS = [
  {
    record_id: "records-1",
    work: "Of Grammatology",
    page_start: 3,
    text: "The sign and divinity have the same place and time of birth.",
    needs_review: false,
  },
  {
    record_id: "records-2",
    work: "Of Grammatology",
    page_start: 4,
    text: "There is nothing outside the text.",
    needs_review: true,
  },
  {
    record_id: "records-3",
    work: "On Cosmopolitanism and Forgiveness",
    page_start: 5,
    text: "What then would such a concept be?",
    needs_review: false,
  },
];

async function openRecordsWorkflow(page: Page) {
  await mockBackend(page, { role: "admin" });
  await page.goto(APP);
  await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await page.setInputFiles("#fileInput", {
    name: "records-workflow.jsonl",
    mimeType: "application/x-ndjson",
    buffer: Buffer.from(RECORD_WORKFLOW_ROWS.map((row) => JSON.stringify(row)).join("\n")),
  });
  await expect(page.getByText("Loaded 3 records")).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: "Records", exact: true }).click();
  await expect(page.locator("#records-page-title")).toBeVisible();
}

test("Records modern workflow covers query, sort, selection, and column configuration", async ({
  page,
}) => {
  await openRecordsWorkflow(page);

  const query = page.getByPlaceholder("Search text in this file");
  await query.fill("outside");
  await expect(page.locator(".records-table tbody tr")).toHaveCount(1);
  await query.fill("");
  await expect(page.locator(".records-table tbody tr")).toHaveCount(3);

  const workSort = page.getByRole("button", { name: "Sort by Work" });
  const workHeader = workSort.locator("xpath=..");
  await workSort.click();
  await expect(workHeader).toHaveAttribute("aria-sort", "ascending");
  await workSort.click();
  await expect(workHeader).toHaveAttribute("aria-sort", "descending");

  const firstRowSelection = page.locator(".records-table tbody input[type=checkbox]").first();
  await firstRowSelection.check();
  await expect(firstRowSelection).toBeChecked();

  const pageSelection = page.locator(".records-table thead input[type=checkbox]").first();
  await pageSelection.check();
  await expect(pageSelection).toBeChecked();

  await page.getByRole("button", { name: "Columns" }).click();
  const dialog = page.getByRole("dialog", { name: "Configure columns" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("Speaker")).toBeVisible();
});
