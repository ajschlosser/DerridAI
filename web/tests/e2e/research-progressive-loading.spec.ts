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
test("slow optional reads leave the Research composer usable and failed reads retry locally", async ({
  page,
}) => {
  await mockBackend(page);
  await page.goto(APP + "/");
  await page.waitForLoadState("networkidle");
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let failed = true;
  let pipelineReads = 0;
  await page.route("**/api/system/pipelines/research-options", async (route) => {
    pipelineReads++;
    await gate;
    await route.fulfill({
      status: failed ? 503 : 200,
      contentType: "application/json",
      body: JSON.stringify(
        failed
          ? { detail: "Pipeline choices unavailable" }
          : { assignment: null, pipelines: [], strategies: [], override_allowed: false },
      ),
    });
  });
  await page.goto(APP + "/rag");
  await expect(page.locator("#research-page-title")).toBeVisible();
  await expect(page.locator("#researchQuestion")).toBeEnabled();
  await page.locator("#researchQuestion").fill("Keep this research draft");
  await expect(page.locator(".research-pipelines-status")).toHaveCount(0);
  release();
  await expect(page.locator(".research-pipelines-status")).toContainText(
    "Pipeline choices unavailable",
  );
  failed = false;
  await page.locator(".research-pipelines-status").getByRole("button", { name: "Retry" }).click();
  await expect(page.locator(".research-pipelines-status")).toHaveCount(0);
  await expect(page.locator("#researchQuestion")).toHaveValue("Keep this research draft");
  expect(pipelineReads).toBe(2);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator("#researchQuestion")).toBeVisible();
  const findings = await new AxeBuilder({ page }).include(".research-native-page").analyze();
  expect(findings.violations).toEqual([]);
});
