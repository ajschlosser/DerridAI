/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test } from "@playwright/test";
import { mockBackend } from "./support/mock-backend";

const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

function records(count: number) {
  return Array.from({ length: count }, (_, index) => ({
    record_id: `derrida-grammatology-${String(index + 1).padStart(5, "0")}`,
    work: "Of Grammatology",
    document_author: "Jacques Derrida",
    page_start: index + 1,
    page_end: index + 1,
    text: `Passage ${index + 1}. The sign and divinity have the same place and time of birth.`,
    speaker: "Derrida",
    needs_review: false,
  }));
}

test("the page scrolls when the pointer is over the results table", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium-desktop", "Runs once.");
  await mockBackend(page);
  await page.goto(`${APP}/`);
  await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await page.setInputFiles("#fileInput", {
    name: "scroll.jsonl",
    mimeType: "application/x-ndjson",
    buffer: Buffer.from(
      records(40)
        .map((row) => JSON.stringify(row))
        .join("\n"),
    ),
  });
  await expect(page.getByText("Loaded 40 records")).toBeVisible({ timeout: 10_000 });
  await page
    .locator("nav, aside")
    .getByRole("button", { name: "Search", exact: true })
    .first()
    .click();
  const table = page.locator(".search-table-scroll");
  await expect(table).toBeVisible();
  const before = await page.evaluate(() => scrollY);
  const box = (await table.boundingBox())!;
  await page.mouse.move(box.x + Math.min(240, box.width / 2), box.y + Math.min(80, box.height / 2));
  await page.mouse.wheel(0, 900);
  await expect.poll(() => page.evaluate(() => scrollY)).toBeGreaterThan(before);
});

test("the page scrolls when the pointer is over the command surface", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium-desktop", "Runs once.");
  await mockBackend(page);
  await page.goto(`${APP}/`);
  await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await page.setInputFiles("#fileInput", {
    name: "scroll.jsonl",
    mimeType: "application/x-ndjson",
    buffer: Buffer.from(
      records(40)
        .map((row) => JSON.stringify(row))
        .join("\n"),
    ),
  });
  await expect(page.getByText("Loaded 40 records")).toBeVisible({ timeout: 10_000 });
  await page
    .locator("nav, aside")
    .getByRole("button", { name: "Search", exact: true })
    .first()
    .click();
  const surface = page.locator(".search-command-surface");
  await expect(surface).toBeVisible();
  const before = await page.evaluate(() => scrollY);
  const box = (await surface.boundingBox())!;
  await page.mouse.move(box.x + Math.min(240, box.width / 2), box.y + Math.min(40, box.height / 2));
  await page.mouse.wheel(0, 900);
  await expect.poll(() => page.evaluate(() => scrollY)).toBeGreaterThan(before);
});
