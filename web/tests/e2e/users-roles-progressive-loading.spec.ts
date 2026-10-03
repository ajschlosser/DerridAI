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

test("Users exposes accounts before roles, retries locally and retains rows", async ({ page }) => {
  await mockBackend(page, { role: "admin" });
  await page.goto(APP);
  await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "System", exact: true }).click();
  let usersReads = 0;
  let rolesReads = 0;
  let fail = true;
  await page.route("**/api/auth/users", async (route) => {
    usersReads += 1;
    await route.fallback();
  });
  await page.route("**/api/auth/roles", async (route) => {
    rolesReads += 1;
    await new Promise((resolve) => setTimeout(resolve, 1200));
    if (fail)
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: '{"detail":"offline"}',
      });
    else await route.fallback();
  });
  await page.getByRole("button", { name: "Users & roles", exact: true }).click();
  await expect(page.locator(".user-row")).toHaveCount(1);
  const row = await page.locator(".user-row").elementHandle();
  await expect(page.locator("#new-username")).toBeDisabled();
  await expect(page.locator(".users-role-error")).toBeVisible();
  const initialUsersReads = usersReads;
  fail = false;
  await page
    .locator(".users-role-error")
    .getByRole("button", { name: "Retry", exact: true })
    .click();
  await expect(page.locator("#new-username")).toBeEnabled();
  expect(usersReads).toBe(initialUsersReads);
  expect(rolesReads).toBe(3); // Initial read, shared automatic retry, local retry.
  expect(await row!.evaluate((node) => node.isConnected)).toBe(true);
  await page.locator("#new-username").fill("Unsaved account");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    (
      await new AxeBuilder({ page })
        .include(".users-page")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
});

test("Roles retains the permission editor through atomic failure and retry", async ({ page }) => {
  await mockBackend(page, { role: "admin" });
  await page.goto(APP);
  await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "System", exact: true }).click();
  await page.getByRole("button", { name: "Roles & permissions", exact: true }).click();
  await expect(page.locator(".role-editor")).toBeVisible();
  const editor = await page.locator(".role-editor").elementHandle();
  let fail = true;
  let reads = 0;
  await page.route("**/api/auth/users", async (route) => {
    reads += 1;
    await new Promise((resolve) => setTimeout(resolve, 1000));
    if (fail)
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: '{"detail":"offline"}',
      });
    else await route.fallback();
  });
  await page.locator(".roles-page").getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(
    page.locator(".roles-page").getByRole("button", { name: "Create role", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".roles-page").getByRole("alert")).toContainText(
    "Previously loaded content",
  );
  fail = false;
  await page.locator(".roles-page").getByRole("button", { name: "Retry", exact: true }).click();
  await expect(
    page.locator(".roles-page").getByRole("button", { name: "Create role", exact: true }),
  ).toBeEnabled();
  expect(await editor!.evaluate((node) => node.isConnected)).toBe(true);
  expect(reads).toBe(2);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    (
      await new AxeBuilder({ page })
        .include(".roles-page")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
});
