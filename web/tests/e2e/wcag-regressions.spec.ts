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

test.beforeEach(({}, info) => {
  test.skip(info.project.name !== "chromium-desktop", "Runs once in Chromium.");
});

test("bulk metadata modal contains keyboard focus", async ({ page }) => {
  await page.goto(
    "/iframe.html?id=corpus-builder-review-bulk-metadata-editor--default&viewMode=story",
  );

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();

  const focusable = dialog.locator(
    'button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex]:not([tabindex="-1"])',
  );
  const first = focusable.first();
  const last = focusable.last();

  await last.focus();
  await page.keyboard.press("Tab");
  await expect(first).toBeFocused();

  await page.keyboard.press("Shift+Tab");
  await expect(last).toBeFocused();
});

test("run guidance removable cues meet the WCAG 2.2 target-size minimum", async ({ page }) => {
  await page.goto("/iframe.html?id=corpus-builder-setup-run-guidance--seeded&viewMode=story");

  const removeButtons = page.locator(".rg-chip button");
  await expect(removeButtons.first()).toBeVisible();

  const boxes = await removeButtons.evaluateAll((buttons) =>
    buttons.map((button) => {
      const box = button.getBoundingClientRect();
      return { width: box.width, height: box.height };
    }),
  );

  for (const box of boxes) {
    expect(box.width).toBeGreaterThanOrEqual(24);
    expect(box.height).toBeGreaterThanOrEqual(24);
  }
});
