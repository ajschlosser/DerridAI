/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import { CORPUS_BUILD_ID, CORPUS_RECORDS, mockBackend } from "./support/mock-backend";

// Fixes reported against the Corpus Builder, checked in the real app against the mock API.
const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;
const LONG = Array.from({ length: 60 }, (_, i) => `Sentence ${i + 1} of a very long record that needs the whole pane to scroll.`).join(" ");

async function open(page: Page, records?: unknown[]) {
  await mockBackend(page, {
    fixtures: records
      ? { [`/api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records`]: { items: records, total: records.length, offset: 0, limit: 50 } }
      : {},
  });
  await page.goto(`${APP}/pdf`);
  await page.locator(".review-grid").waitFor();
}

test.beforeEach(({}, info) => test.skip(info.project.name !== "chromium-desktop", "Runs once."));

for (const width of [1440, 1100, 900]) {
  test(`the bulk actions menu stays inside the window at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 820 });
    await open(page);
    await page.getByRole("button", { name: /bulk actions/i }).first().click();
    const list = page.getByRole("menu").first();
    await expect(list).toBeVisible();
    const box = await list.boundingBox();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(width);
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.y + box!.height).toBeLessThanOrEqual(820);
  });
}

test("the end of a long record can be scrolled fully into view above the decision bar", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 800 });
  const source = CORPUS_RECORDS.find((r) => r.review_state === "metadata")!;
  await open(page, [{ ...source, text: LONG, text_length: LONG.length }, ...CORPUS_RECORDS.slice(0, 5)]);
  const pane = page.locator(".record-review-pane");
  await pane.evaluate((el) => (el.scrollTop = el.scrollHeight));
  const last = await page.locator(".record-primary-text").evaluate((el) => {
    const r = el.getBoundingClientRect();
    const dock = document.querySelector(".record-decision-dock")!.getBoundingClientRect();
    return { textBottom: r.bottom, dockTop: dock.top };
  });
  expect(last.textBottom).toBeLessThanOrEqual(last.dockTop + 1);
  await page.screenshot({ path: "test-results/long-record.png" });
});

test("bulk edit reads like Edit document metadata and applies a value it was given", async ({ page }) => {
  await open(page);
  await page.getByRole("button", { name: /bulk actions/i }).first().click();
  await page.getByRole("menuitem", { name: /bulk edit metadata/i }).click();
  const dialog = page.getByRole("dialog", { name: /bulk edit record metadata/i });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: /apply changes/i })).toBeDisabled();
  await dialog.getByLabel(/^speaker/i).fill("Jacques Derrida");
  await expect(dialog.getByText(/1 field\(s\) will change/i)).toBeVisible();
  await expect(dialog.getByRole("button", { name: /apply changes/i })).toBeDisabled(); // nothing is selected yet
  await dialog.getByRole("radio", { name: /apply to every record/i }).check();
  await expect(dialog.getByRole("button", { name: /apply changes/i })).toBeEnabled();
  await page.screenshot({ path: "test-results/bulk-editor.png" });
});

for (const scheme of ["light", "dark"] as const) {
  test(`the logo has a transparent background in the ${scheme} theme`, async ({ page }) => {
    await mockBackend(page);
    await page.emulateMedia({ colorScheme: scheme });
    await page.goto(`${APP}/`);
    await page.locator(".brand-mark img, img[src^='/brand/']").first().waitFor();
    const alpha = await page.evaluate(async () => {
      const img = new Image();
      img.src = "/brand/derridai-mark.png";
      await img.decode();
      const c = document.createElement("canvas");
      c.width = img.width; c.height = img.height;
      const x = c.getContext("2d")!;
      x.drawImage(img, 0, 0);
      return x.getImageData(2, 2, 1, 1).data[3];
    });
    expect(alpha).toBe(0);
    await page.screenshot({ path: `test-results/logo-${scheme}.png`, clip: { x: 0, y: 0, width: 420, height: 140 } });
  });
}
