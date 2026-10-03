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
test("Relationships trace is independent of model failure and retry", async ({ page }) => {
  await mockBackend(page, { role: "admin" });
  await page.goto(APP);
  await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  await page.waitForLoadState("networkidle");
  let traces = 0;
  let models = 0;
  let fail = true;
  await page.route("**/api/graphql", async (route) => {
    const body = route.request().postDataJSON() as { operationName: string };
    if (body.operationName === "CelfModel") {
      models += 1;
      await new Promise((resolve) => setTimeout(resolve, 1500));
      return route.fulfill({
        status: fail ? 503 : 200,
        contentType: "application/json",
        body: JSON.stringify(
          fail
            ? { detail: "Model offline" }
            : {
                data: {
                  celf_model: {
                    specification_version: "1.0",
                    nodes: [
                      {
                        type: "Record",
                        label: "Record",
                        profile: "Core",
                        persistence: "durable",
                        normative: true,
                      },
                    ],
                    edges: [],
                  },
                },
              },
        ),
      });
    }
    if (body.operationName === "RecordGraph") {
      traces += 1;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            record_graph: {
              specification_version: "1.0",
              root_id: "Record:r1",
              nodes: [
                {
                  id: "Record:r1",
                  object_id: "r1",
                  object_type: "Record",
                  label: "Retained record r1",
                  summary: "Retained source identity",
                  materialization: "materialized",
                },
              ],
              edges: [],
            },
          },
        }),
      });
    }
    return route.fallback();
  });
  await page.evaluate(() =>
    window.dispatchEvent(
      new CustomEvent("derridai:navigate-native", {
        detail: { path: "/relationships?record=r1", runtimeView: "relationships" },
      }),
    ),
  );
  const focus = page.locator(".traceability-focus-card");
  await expect(focus).toContainText("Retained record r1");
  const original = await focus.elementHandle();
  await expect(page.locator(".relationship-model-status")).toBeVisible();
  fail = false;
  await page
    .locator(".relationship-model-status")
    .getByRole("button", { name: "Retry", exact: true })
    .click();
  await expect(page.locator(".relationship-model-status")).toHaveCount(0);
  await expect(page.getByRole("tab", { name: "cELF model", exact: true })).toBeVisible();
  await expect.poll(() => models).toBe(2);
  expect(traces).toBe(1);
  expect(await original!.evaluate((node) => node.isConnected)).toBe(true);
  await page.getByRole("tab", { name: "cELF model", exact: true }).click();
  await expect(focus).toContainText("Core");
  await page.setViewportSize({ width: 390, height: 844 });
  const result = await new AxeBuilder({ page })
    .include(".relationship-browser")
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(result.violations).toEqual([]);
});
