/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import { mockBackend } from "./support/mock-backend";

const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;
const ANNOTATION_ROWS = [
  {
    record_id: "grammatology-00001",
    work: "Of Grammatology",
    page_start: 3,
    text: "The sign and divinity have the same place and time of birth.",
    annotations: [
      {
        id: "n1",
        note: "Central claim",
        quote: "the sign",
        tags: ["sign", "presence"],
        author: "admin",
        created_at: "2026-02-01T10:00:00Z",
        field: "text",
      },
      {
        id: "n2",
        note: "Cf. Glas",
        tags: ["glas"],
        author: "reviewer",
        created_at: "2026-02-03T10:00:00Z",
      },
    ],
  },
  {
    record_id: "glas-00001",
    work: "Glas",
    page_start: 5,
    text: "What remains of the text remains to be read.",
    annotations: [
      {
        id: "n3",
        note: "On remains",
        quote: "remains",
        tags: ["remains"],
        author: "admin",
        created_at: "2026-02-02T10:00:00Z",
      },
    ],
  },
];

async function openAnnotationsWorkflow(page: Page) {
  await mockBackend(page, { role: "admin" });
  await page.goto(APP);
  await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await page.setInputFiles("#fileInput", {
    name: "annotations-workflow.jsonl",
    mimeType: "application/x-ndjson",
    buffer: Buffer.from(ANNOTATION_ROWS.map((row) => JSON.stringify(row)).join("\n")),
  });
  await expect(page.getByText("Loaded 2 records")).toBeVisible({ timeout: 10_000 });
  await page
    .locator(".shell-sidebar")
    .getByRole("button", { name: "Annotations", exact: true })
    .first()
    .click();
  await expect(page.locator("#annotations-page-title")).toBeVisible();
}

test("Annotations modern workflow covers search, recent view, and removal", async ({ page }) => {
  await openAnnotationsWorkflow(page);

  const central = page.locator(".annotation-feed-item").filter({ hasText: "Central claim" });
  await expect(central).toBeVisible();
  await central.getByRole("button", { name: "Remove" }).click();
  await expect(central).toHaveCount(0, { timeout: 15_000 });

  const search = page.getByPlaceholder(/Search annotations/);
  await search.fill("remains");
  await expect(page.getByText("On remains")).toBeVisible();

  await search.fill("");
  await page.waitForTimeout(250);
  await page.getByRole("tab", { name: "Recent" }).click();
  await expect(page.getByText("Recent annotations")).toBeVisible();
});

test("Annotations modern workflow opens the owning work and record", async ({ page }) => {
  await openAnnotationsWorkflow(page);

  const grammatology = page.locator("details").filter({ hasText: "Of Grammatology" }).first();
  await grammatology.getByRole("button", { name: "Open work overview" }).click();
  await expect(page.locator("#works-page-title")).toBeVisible();
  await expect(page.getByText("Of Grammatology").first()).toBeVisible();

  await page.getByRole("button", { name: "Annotations", exact: true }).click();
  await expect(page.locator("#annotations-page-title")).toBeVisible();
  const central = page.locator(".annotation-feed-item").filter({ hasText: "Central claim" });
  await central.getByRole("button", { name: "Open record" }).click();
  await expect(page.locator("main.record-workspace-page")).toBeVisible();
  await expect(
    page.getByText("The sign and divinity have the same place and time of birth."),
  ).toBeVisible();
});
