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

import { expect, test, type Page } from "@playwright/test";
import { runAxe } from "./support/axe";
import { mockBackend } from "./support/mock-backend";

const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

async function expectHelpAxeClean(page: Page) {
  const scan = await runAxe(page, (builder) =>
    builder.include(".help-center").withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]),
  );
  expect(
    scan.violations.map(
      (violation) => `${violation.id}: ${violation.nodes.map((node) => node.target).join(" ")}`,
    ),
  ).toEqual([]);
}

test.beforeEach(({}, info) => {
  test.skip(info.project.name !== "chromium-desktop", "Runs once in Chromium.");
});

test("Help Center is task-first, searchable, deep-linkable, and WCAG 2.2 AA clean", async ({
  page,
}) => {
  await mockBackend(page, { role: "admin" });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(APP + "/help");

  await expect(page.getByRole("heading", { level: 1, name: "Help center" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Start with a task" })).toBeVisible();
  await expect(page.locator(".help-start-card")).toHaveCount(6);
  await expect(page.getByText("Technical glossary & parameter reference").first()).toBeVisible();

  await page.keyboard.press("/");
  const search = page.locator("#help-search-input");
  await expect(search).toBeFocused();
  await search.fill("pipeline trace");
  await expect(page).toHaveURL(/q=pipeline(?:\+|%20)trace/);
  await expect(page.locator("#help-search-status")).toContainText("matches");
  await expect(page.locator("#help-term-pipeline_trace")).toBeVisible();

  await search.fill("");
  await page.getByRole("button", { name: "Storage & indexes" }).click();
  await expect(page).toHaveURL(/topic=storage/);

  await page.goto(APP + "/help#help-question-pipeline_trace");
  const question = page.locator("#help-question-pipeline_trace");
  await expect(question).toHaveAttribute("open", "");
  await question.getByRole("button").count().catch(() => 0);
  await expectHelpAxeClean(page);

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".help-toc nav")).toBeVisible();
  await expect(page.locator(".help-start-grid")).toBeVisible();
  await expectHelpAxeClean(page);

  await page.emulateMedia({ forcedColors: "active", reducedMotion: "reduce" });
  await expectHelpAxeClean(page);
});

test("Help Center hides administrator-only workflows from a Researcher", async ({ page }) => {
  await mockBackend(page, { role: "researcher" });
  await page.goto(APP + "/help");

  await expect(page.getByRole("heading", { level: 1, name: "Help center" })).toBeVisible();
  await expect(page.getByText("Build a corpus", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Review metadata", { exact: true })).toHaveCount(0);

  await page.locator("#help-search-input").fill("provider");
  await expect(page.getByText("LLM Providers", { exact: true })).toHaveCount(0);
  await expect(page.locator("#help-term-provider")).toBeVisible();

  await expectHelpAxeClean(page);
});
