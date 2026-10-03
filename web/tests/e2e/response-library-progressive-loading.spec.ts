/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mockBackend } from "./support/mock-backend";
const APP = "http://127.0.0.1:" + (process.env.APP_PORT || "5199");
const response = {
  record_id: "saved-a",
  question: "A saved research question",
  text: "An authoritative saved answer.",
  provider: "Local",
  model: "fixture",
  evidence: [],
};
const body = { records: [response], count: 1, total: 1 };

test("delayed archive reads mount the frame and filtering failures preserve the answer with local retry", async ({
  page,
}) => {
  await mockBackend(page);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let failed = true;
  let reads = 0;
  await page.route("**/api/response-cache/records?**", async (route) => {
    reads++;
    const query = new URL(route.request().url()).searchParams.get("query");
    if (!query) await gate;
    await route.fulfill({
      status: query && failed ? 503 : 200,
      contentType: "application/json",
      body: JSON.stringify(query && failed ? { detail: "Archive unavailable" } : body),
    });
  });
  await page.goto(APP + "/faq");
  await expect(page.locator("#response-faq-title")).toBeVisible();
  await page.locator(".response-faq-page-actions").getByRole("button", { name: /Find/ }).click();
  await expect(page.locator(".response-archive-body .is-skeleton")).toBeVisible();
  await expect(page.locator(".response-archive-count")).toHaveCount(0);
  release();
  await expect(page.locator(".response-archive-body")).toContainText(response.question);
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await expect(page.locator(".response-faq-workspace")).toContainText(response.text);
  await page.locator(".response-faq-workspace").evaluate((element) => {
    element.setAttribute("data-preserved", "yes");
  });
  await page.locator(".response-faq-page-actions").getByRole("button", { name: /Find/ }).click();
  await page.locator(".response-archive-search input").fill("hospitality");
  await expect(page.locator(".response-archive-body [role=alert]")).toContainText(
    "Archive unavailable",
  );
  await expect(page.locator(".response-archive-count")).toHaveCount(0);
  await expect(page.locator(".response-archive-body")).not.toContainText("No matches");
  failed = false;
  await page.locator(".response-archive-body").getByRole("button", { name: "Retry" }).click();
  await expect(page.locator(".response-archive-body [role=alert]")).toHaveCount(0);
  await expect(page.locator(".response-faq-workspace")).toHaveAttribute("data-preserved", "yes");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    (await new AxeBuilder({ page }).include(".response-archive-dialog").analyze()).violations,
  ).toEqual([]);
  await page.getByRole("button", { name: "Close", exact: true }).click();
  expect(
    (await new AxeBuilder({ page }).include(".response-faq-page").analyze()).violations,
  ).toEqual([]);
  expect(reads).toBe(4); // first read, one failed read plus its existing query retry, explicit retry
});

test("an initial failure has a retry and never claims an empty library", async ({ page }) => {
  await mockBackend(page);
  let failed = true;
  await page.route("**/api/response-cache/records?**", (route) =>
    route.fulfill({
      status: failed ? 503 : 200,
      contentType: "application/json",
      body: JSON.stringify(failed ? { detail: "Saved responses unavailable" } : body),
    }),
  );
  await page.goto(APP + "/faq");
  await expect(page.locator(".response-faq-read-error")).toContainText(
    "Saved responses unavailable",
  );
  failed = false;
  await page.locator(".response-faq-read-error").getByRole("button", { name: "Retry" }).click();
  await expect(page.locator(".response-faq-workspace")).toContainText(response.text);
});
