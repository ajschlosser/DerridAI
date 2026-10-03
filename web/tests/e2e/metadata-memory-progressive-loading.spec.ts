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

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { mockBackend } from "./support/mock-backend";

const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

function payload(value = "Levinas") {
  return {
    items: [
      {
        id: "mex-1",
        memory_type: "evidence_bound",
        kind: "correction",
        field: "position_holder",
        value,
        rejected_value: "Derrida",
        authority: "human_override",
        review_method: "human_review_of_llm_proposal",
        record_id: "r1",
        record_revision: 4,
        build_id: "build-1",
        source_document_id: "asset-1",
        schema_id: "derrida",
        schema_version: "v1",
        language: "en",
        region_type: "main_text",
        page_start: 12,
        page_end: 12,
        evidence_bound: true,
        evidence_hash: "hash",
        evidence_block_ids: ["b2"],
        evidence_text: "For Levinas, responsibility precedes freedom.",
        context_text: "Context around the evidence.",
        source_current: true,
        evidence_current: true,
      },
    ],
    total: 1,
    offset: 0,
    limit: 50,
    summary: { entries: 1, evidence_bound: 1, corrections: 1, fields: 1, backends: 1 },
    facets: {
      fields: ["position_holder"],
      kinds: ["correction"],
      languages: ["en"],
      builds: ["build-1"],
    },
    derived: true,
    authoritative_source: "reviewed corpus metadata and evidence",
    available: true,
    error: "",
  };
}

function emptyPayload() {
  return {
    ...payload(),
    items: [],
    total: 0,
    summary: { entries: 0, evidence_bound: 0, corrections: 0, fields: 0, backends: 1 },
    facets: { fields: [], kinds: [], languages: [], builds: [] },
  };
}

function unavailablePayload(message: string) {
  return {
    ...emptyPayload(),
    available: false,
    error: message,
  };
}

async function navigate(page: Page, path: string, runtimeView?: string) {
  await page.evaluate(
    ({ nextPath, nextRuntimeView }) =>
      window.dispatchEvent(
        new CustomEvent("derridai:navigate-native", {
          detail: { path: nextPath, runtimeView: nextRuntimeView },
        }),
      ),
    { nextPath: path, nextRuntimeView: runtimeView },
  );
}

test("a cached empty memory is revalidated on revisit before it is presented as current", async ({
  page,
}) => {
  await mockBackend(page, { role: "admin" });
  let latest = false;
  let reads = 0;
  let releaseLatest!: () => void;
  const latestGate = new Promise<void>((resolve) => {
    releaseLatest = resolve;
  });

  await page.route("**/api/system/metadata-memory**", async (route) => {
    reads += 1;
    if (!latest) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(emptyPayload()),
      });
      return;
    }
    await latestGate;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(payload()),
    });
  });

  await page.goto(APP + "/metadata-memory");
  await expect(page.locator("#metadata-memory-title")).toBeVisible();
  await expect(page.locator(".empty-cell")).toContainText("No precedents yet");

  await navigate(page, "/providers", "providers");
  await expect(page.locator("#providers-page-title")).toBeVisible();

  latest = true;
  await navigate(page, "/metadata-memory");
  await expect(page.locator("#metadata-memory-title")).toBeVisible();
  await expect(page.locator(".memory-table-loading")).toBeVisible();
  await expect(page.locator(".empty-cell")).toHaveCount(0);

  releaseLatest();
  await expect(page.locator(".memory-table")).toContainText("Levinas");
  expect(reads).toBe(2);
});

test("a failed revalidation retains the last successful memory and is WCAG 2.2 AA clean", async ({
  page,
}) => {
  await mockBackend(page, { role: "admin" });
  let fail = false;

  await page.route("**/api/system/metadata-memory**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        fail ? unavailablePayload("projection temporarily unavailable") : payload(),
      ),
    });
  });

  await page.goto(APP + "/metadata-memory");
  await expect(page.locator(".memory-table")).toContainText("Levinas");

  await navigate(page, "/providers", "providers");
  await expect(page.locator("#providers-page-title")).toBeVisible();
  fail = true;
  await navigate(page, "/metadata-memory");

  await expect(page.locator(".memory-read-error")).toContainText(
    "projection temporarily unavailable",
  );
  await expect(page.locator(".memory-table")).toContainText("Levinas");
  await expect(page.locator(".empty-cell")).toHaveCount(0);

  await page.setViewportSize({ width: 390, height: 844 });
  const result = await new AxeBuilder({ page })
    .include(".metadata-memory-page")
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(result.violations).toEqual([]);

  fail = false;
  await page.locator(".memory-read-error").getByRole("button", { name: "Retry" }).click();
  await expect(page.locator(".memory-read-error")).toHaveCount(0);
  await expect(page.locator(".memory-table")).toContainText("Levinas");
});
