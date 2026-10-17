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
import { runAxe } from "./support/axe";

test("details use keyboard tabs in an opaque modal and restore the launcher", async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 900 });
  await page.goto(
    "/iframe.html?id=corpus-builder-workflow-build-details--with-warnings&viewMode=story",
  );
  const launcher = page.getByRole("button", { name: "Build details", exact: true });
  await launcher.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toHaveAttribute("aria-modal", "true");
  const activity = page.getByRole("tab", { name: "Activity", exact: true });
  await activity.focus();
  await activity.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Issues", exact: true })).toBeFocused();
  await expect(page.getByRole("tabpanel", { name: "Issues", exact: true })).toContainText(
    "structured_output_invalid",
  );
  await page.getByRole("tab", { name: "Issues", exact: true }).press("End");
  await expect(page.getByRole("tab", { name: "Settings", exact: true })).toBeFocused();
  const results = await runAxe(page, (builder) =>
    builder.include(".ui-dialog").withTags(["wcag2a", "wcag2aa", "wcag21aa"]),
  );
  expect(results.violations).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(launcher).toBeFocused();
});

test("docked details allow focus outside the pane and do not consume Escape there", async ({
  page,
}) => {
  await page.setViewportSize({ width: 2000, height: 1000 });
  await page.goto("/iframe.html?id=corpus-builder-workflow-build-details--docked&viewMode=story");
  const launcher = page.getByRole("button", { name: "Build details", exact: true });
  await launcher.click();
  const pane = page.getByRole("region", { name: "Build details", exact: true });
  await expect(pane).toBeVisible();
  await expect(pane).not.toHaveAttribute("aria-modal");
  await launcher.focus();
  await launcher.press("Escape");
  await expect(pane).toBeVisible();
  await page.getByRole("tab", { name: "Activity", exact: true }).focus();
  await page.keyboard.press("Escape");
  await expect(pane).toBeHidden();
  await expect(launcher).toBeFocused();
});

test("grouped issues retain original messages and verified current Record links", async ({
  page,
}) => {
  await page.goto(
    "/iframe.html?id=corpus-builder-status-build-warnings--current-records&viewMode=story",
  );
  await page.locator(".build-warnings > summary").click();
  await page.locator(".warning-group > summary").click();
  await expect(page.locator(".warning-group li")).toHaveCount(3);
  await expect(page.locator(".warning-records button")).toHaveCount(2);
  await expect(page.locator(".warning-records")).not.toContainText("record-0");
  const results = await runAxe(page, (builder) =>
    builder.include(".build-warnings").withTags(["wcag2a", "wcag2aa", "wcag21aa"]),
  );
  expect(results.violations).toEqual([]);
});
