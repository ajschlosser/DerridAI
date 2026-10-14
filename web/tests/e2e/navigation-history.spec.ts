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
import { mockBackend } from "./support/mock-backend";

// The router is the only navigation history: the breadcrumb Back/Forward buttons walk it, and they keep
// working after the sidebar has been used to move between pages.
const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

test("breadcrumb Back and Forward walk the router history", async ({ page }, testInfo) => {
  test.skip(
    testInfo.project.name !== "chromium-desktop",
    "Navigation history is viewport-independent.",
  );
  await mockBackend(page, { role: "admin" });
  await page.goto(APP + "/");

  const back = page.getByRole("button", { name: "Back" });
  const forward = page.getByRole("button", { name: "Forward" });
  const sidebar = page.locator(".shell-sidebar");
  await expect(back).toBeDisabled();

  await sidebar.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page).toHaveURL(/\/search/);
  await sidebar.getByRole("button", { name: "Works", exact: true }).click();
  await expect(page).toHaveURL(/\/works/);
  await expect(back).toBeEnabled();
  await expect(forward).toBeDisabled();

  await back.click();
  await expect(page).toHaveURL(/\/search/);
  await expect(forward).toBeEnabled();

  await forward.click();
  await expect(page).toHaveURL(/\/works/);

  // Navigation is still live afterwards.
  await sidebar.getByRole("button", { name: "Home", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
});
