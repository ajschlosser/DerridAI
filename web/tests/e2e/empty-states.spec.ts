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

for (const story of ["database-required", "database-required-without-access"]) {
  test(`database-required empty state (${story}) is announced and WCAG 2.0 AA clean`, async ({
    page,
  }) => {
    await page.goto(`/iframe.html?id=foundations-feedback-empty-state--${story}&viewMode=story`);
    const state = page.locator(".accessible-empty-state");
    await expect(state).toBeVisible();
    await expect(state).toHaveAttribute("role", "status");
    await expect(state.getByRole("heading", { level: 2 })).toContainText("corpus database");
    const button = state.getByRole("button");
    await expect(button).toHaveCount(story === "database-required" ? 1 : 0);
    const results = await runAxe(page, (builder) =>
      builder.include(".accessible-empty-state").withTags(["wcag2a", "wcag2aa"]),
    );
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}
