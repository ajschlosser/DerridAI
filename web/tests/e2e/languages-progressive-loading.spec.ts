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
const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

test("Languages dictionary stays usable while policy reads fail and retry", async ({
  page,
}, testInfo) => {
  await mockBackend(page, { role: "admin" });
  await page.goto(APP);
  await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  await page.waitForLoadState("networkidle");
  let policyReads = 0;
  let dictionaryReads = 0;
  let fail = true;
  await page.route("**/api/i18n/languages/*", async (route) => {
    dictionaryReads += 1;
    return route.fallback();
  });
  await page.route("**/api/i18n/languages/*/content-policy", async (route) => {
    policyReads += 1;
    await new Promise((resolve) => setTimeout(resolve, 1500));
    await route.fulfill({
      status: fail ? 503 : 200,
      contentType: "application/json",
      body: JSON.stringify(
        fail
          ? { detail: "Policy offline" }
          : {
              code: "en-US",
              status: "missing",
              blocked_terms: [],
              contextual_terms: [],
            },
      ),
    });
  });
  const start = Date.now();
  await page.getByRole("button", { name: "Manage languages", exact: true }).click();
  const identity = page.locator(".language-identity-card");
  await expect(identity).toBeVisible();
  const useful = Date.now() - start;
  const original = await identity.elementHandle();
  const policy = page.locator(".language-policy-card");
  await expect(policy.locator(".ui-loading-state")).toBeVisible();
  await identity.locator("input.control").fill("Unsaved locale name");
  await expect(policy.getByRole("alert")).toContainText("Policy offline");
  const beforeRetry = dictionaryReads;
  await page.setViewportSize({ width: 390, height: 844 });
  const feedback = await new AxeBuilder({ page })
    .include(".language-policy-card")
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(feedback.violations).toEqual([]);
  fail = false;
  await policy.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(policy.getByRole("alert")).toHaveCount(0);
  await expect(policy.locator(".ui-loading-state")).toHaveCount(0);
  await expect(identity.locator("input.control")).toHaveValue("Unsaved locale name");
  expect(await original!.evaluate((node) => node.isConnected)).toBe(true);
  expect(dictionaryReads).toBe(beforeRetry);
  expect(policyReads).toBe(2);
  await testInfo.attach("readiness", {
    body: JSON.stringify({
      syntheticPolicyDelayMs: 1500,
      firstEditableMs: useful,
      dictionaryReads,
      policyReads,
    }),
    contentType: "application/json",
  });
});
