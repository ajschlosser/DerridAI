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

import { expect, test, type Locator } from "@playwright/test";

const story = (id: string) => `/iframe.html?id=${id}&viewMode=story`;

async function expectNoHorizontalOverflow(locator: Locator) {
  const metrics = await locator.evaluate((element: HTMLElement) => ({
    scrollWidth: element.scrollWidth,
    clientWidth: element.clientWidth,
  }));
  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth + 1);
}

async function expectFrenchStory(page: import("@playwright/test").Page) {
  await expect(page.locator("html")).toHaveAttribute("lang", "fr-CA");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
}

test.describe("long translated string layout contract", () => {
  test.use({ viewport: { width: 640, height: 900 } });

  test("representative navigation, table, form, dialog, and Help surfaces keep controls usable", async ({
    page,
  }) => {
    await page.goto(story("shell-sidebar-navigator--french-length-stress"));
    await expectFrenchStory(page);
    const navigation = page.locator(".shell-navigation");
    await expect(navigation).toBeVisible();
    await expect(navigation.locator('input[type="search"]')).toBeVisible();
    await expect(navigation.locator("button").first()).toBeVisible();
    await expectNoHorizontalOverflow(navigation);

    await page.goto(story("system-metadata-schemas-fields--french-length-stress"));
    await expectFrenchStory(page);
    const fields = page.locator(".fields-panel");
    await expect(fields).toBeVisible();
    await expect(fields.locator('input[type="search"]')).toBeVisible();
    await expect(fields.locator(".field-select").first()).toBeVisible();
    await expect(fields.locator(".field-inspector")).toBeVisible();
    await expectNoHorizontalOverflow(fields);

    await page.goto(story("system-metadata-schemas-field-form--french-length-stress"));
    await expectFrenchStory(page);
    const form = page.locator("#storybook-root");
    await expect(form.locator("input").first()).toBeVisible();
    await expect(form.locator("select").first()).toBeVisible();
    await expect(form.locator("details").first()).toBeVisible();
    await expectNoHorizontalOverflow(form);

    await page.goto(story("foundations-overlays-dialog--french-length-stress"));
    await expectFrenchStory(page);
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("heading")).toBeVisible();
    await expect(dialog.getByRole("button").last()).toBeVisible();
    await expectNoHorizontalOverflow(dialog);

    await page.goto(story("help-center-search-hero--french-length-stress"));
    await expectFrenchStory(page);
    const help = page.locator(".help-hero");
    await expect(help).toBeVisible();
    await expect(help.getByRole("searchbox")).toBeVisible();
    await expect(help.getByRole("heading", { level: 1 })).toBeVisible();
    await expectNoHorizontalOverflow(help);
  });
});
