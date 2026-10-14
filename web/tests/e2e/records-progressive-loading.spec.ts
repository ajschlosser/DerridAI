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
import { mockBackend, STORE_RECORDS } from "./support/mock-backend";
const APP = "http://127.0.0.1:" + (process.env.APP_PORT || "5199");
test("Records keeps its frame during delayed corpus hydration and retries a failed export", async ({
  page,
}) => {
  await mockBackend(page);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let failed = true;
  let reads = 0;
  await page.route("**/api/stores/derrida_primary/export", async (route) => {
    reads++;
    await gate;
    await route.fulfill({
      status: failed ? 503 : 200,
      contentType: "application/json",
      body: JSON.stringify(failed ? { detail: "Corpus unavailable" } : { records: STORE_RECORDS }),
    });
  });
  await page.goto(APP + "/records");
  await expect(page.locator("#records-page-title")).toBeVisible();
  await expect(page.locator(".records-hydration .is-skeleton")).toBeVisible();
  await expect(page.locator(".records-stats")).toHaveCount(0);
  expect((await new AxeBuilder({ page }).include(".records-page").analyze()).violations).toEqual(
    [],
  );
  release();
  await expect(page.locator(".records-hydration-error")).toBeVisible();
  await expect(page.locator(".records-layout")).toHaveCount(0);
  expect((await new AxeBuilder({ page }).include(".records-page").analyze()).violations).toEqual(
    [],
  );
  failed = false;
  await page.locator(".records-hydration-error").getByRole("button", { name: "Retry" }).click();
  await expect(page.locator(".records-table tbody tr")).toHaveCount(STORE_RECORDS.length);
  expect(reads).toBe(2);
  await page.setViewportSize({ width: 390, height: 844 });
  // The existing filter row has two empty selection/action headers. Keep this visible as
  // a baseline exception until the separately requested label fix is authorized.
  const findings = (await new AxeBuilder({ page }).include(".records-page").analyze()).violations;
  expect(findings.map((finding) => finding.id)).toEqual(["empty-table-header"]);
  expect(findings[0].nodes).toHaveLength(2);
});
