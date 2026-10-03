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
import { CORPUS_BUILD, CORPUS_BUILD_ID, CORPUS_RECORDS, mockBackend } from "./support/mock-backend";

const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

test("repeated Enter confirms No value across empty unresolved fields", async ({ page }) => {
  const record = {
    ...CORPUS_RECORDS[0],
    speaker: "",
    position_holder: "",
    metadata_review_fields: ["speaker", "position_holder"],
    metadata_incomplete_fields: [],
    acceptance_blocking_fields: ["speaker", "position_holder"],
    metadata_complete: false,
    metadata_field_status: {
      speaker: { status: "unresolved", evaluation_status: "not_evaluated" },
      position_holder: { status: "unresolved", evaluation_status: "not_evaluated" },
    },
    review_state: "metadata",
    review_disposition: "pending",
    accepted: false,
    needs_review: true,
  };
  await mockBackend(page, {
    fixtures: {
      [`/api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records`]: {
        items: [record],
        total: 1,
        offset: 0,
        limit: 50,
      },
    },
  });
  const decisionPath = `/api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records/${record.record_id}/metadata-decision`;
  const requests: Record<string, unknown>[] = [];
  await page.route(`**${decisionPath}`, async (route) => {
    requests.push(route.request().postDataJSON());
    const decided = new Set(requests.map((request) => request.field));
    const remaining = record.metadata_review_fields.filter((field) => !decided.has(field));
    await route.fulfill({
      json: {
        record: {
          ...record,
          record_revision: 1 + requests.length,
          metadata_review_fields: remaining,
          acceptance_blocking_fields: remaining,
          metadata_complete: !remaining.length,
          metadata_field_status: {
            speaker: decided.has("speaker")
              ? { status: "confirmed_absent", method: "human" }
              : record.metadata_field_status.speaker,
            position_holder: decided.has("position_holder")
              ? { status: "confirmed_absent", method: "human" }
              : record.metadata_field_status.position_holder,
          },
        },
        build: CORPUS_BUILD,
      },
    });
  });
  await page.goto(`${APP}/pdf?workspace=review&build=${CORPUS_BUILD_ID}`);
  await expect(page.locator(".record-primary-text")).toBeVisible();
  await page.keyboard.press("m");
  const noValue = page.locator('[data-field="speaker"] [data-no-value-action]');
  await expect(noValue).toBeFocused();
  expect(requests).toHaveLength(0);
  await page.keyboard.press("Enter");
  await expect.poll(() => requests.length).toBe(1);
  expect(requests[0]).toMatchObject({
    field: "speaker",
    value: null,
    confirm_no_supported_value: true,
  });
  await expect(page.locator('[data-field="position_holder"] [data-no-value-action]')).toBeFocused();
  await page.keyboard.press("Enter");
  await expect.poll(() => requests.length).toBe(2);
  expect(requests[1]).toMatchObject({
    field: "position_holder",
    value: null,
    confirm_no_supported_value: true,
  });
});

test("ordinary Record navigation defers source reads and clean advanced draft writes", async ({
  page,
}) => {
  let sourceReads = 0;
  let viewedWrites = 0;
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (/\/api\/pdf\/assets\/[^/]+\/blocks$/.test(path)) sourceReads += 1;
    if (path.endsWith("/viewed") && request.method() === "POST") viewedWrites += 1;
  });
  await page.addInitScript(() => {
    const write = Storage.prototype.setItem;
    Storage.prototype.setItem = function (key: string, value: string) {
      if (this === localStorage && key.startsWith("derridai.pdf-corpus.metadata-draft.")) {
        write.call(
          sessionStorage,
          "performance-draft-writes",
          String(Number(sessionStorage.getItem("performance-draft-writes") || 0) + 1),
        );
      }
      write.call(this, key, value);
    };
  });
  await mockBackend(page);
  await page.goto(`${APP}/pdf?workspace=review&build=${CORPUS_BUILD_ID}`);
  await expect(page.locator(".record-primary-text")).toBeVisible();
  expect(sourceReads).toBe(0);
  expect(viewedWrites).toBe(0);
  expect(await page.evaluate(() => sessionStorage.getItem("performance-draft-writes"))).toBeNull();

  await page.locator("#review-tab-evidence").click();
  await expect.poll(() => sourceReads).toBe(1);
  await page.locator("#review-tab-metadata").click();
  await page.locator("#review-tab-source").click();
  await expect(page.locator("#review-tab-source")).toHaveAttribute("aria-selected", "true");
  expect(sourceReads).toBe(1);
  expect(viewedWrites).toBe(0);
  expect(await page.evaluate(() => sessionStorage.getItem("performance-draft-writes"))).toBeNull();
  await page.locator("#review-tab-metadata").click();
  const advanced = page.locator("details.record-data");
  await expect(advanced.locator("#pdf-corpus-metadata")).toHaveValue("");
  await advanced.locator("summary").click();
  await expect(advanced.locator("#pdf-corpus-metadata")).not.toHaveValue("");
  await advanced.locator("#pdf-corpus-metadata").fill('{ "speaker": "Recoverable draft" }');
  await advanced.locator("summary").click();
  await page.locator("#review-tab-evidence").click();
  await page.locator("#review-tab-metadata").click();
  await advanced.locator("summary").click();
  await expect(advanced.locator("#pdf-corpus-metadata")).toHaveValue(
    '{ "speaker": "Recoverable draft" }',
  );
});

test("cached Record activation stays below the 250-ms navigation budget", async ({ page }) => {
  const records = CORPUS_RECORDS.slice(0, 2);
  await mockBackend(page, {
    fixtures: {
      [`/api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records`]: {
        items: records,
        total: records.length,
        offset: 0,
        limit: 50,
      },
    },
  });
  await page.goto(`${APP}/pdf?workspace=review&build=${CORPUS_BUILD_ID}&queue=all`);
  await expect(page.locator(".record-primary-text")).toBeVisible();
  for (const record of records) {
    await page
      .locator(".record-row")
      .filter({ has: page.locator(`b[title="${record.record_id}"]`) })
      .click();
    await expect(page.locator(".record-primary-text")).toContainText(record.text);
  }
  let reads = 0;
  page.on("request", (request) => {
    if (
      request.url().endsWith("/api/graphql") &&
      request.postDataJSON()?.operationName === "CorpusReviewRecords"
    )
      reads += 1;
  });
  const samples = await page.evaluate(
    async (targets) => {
      const times: number[] = [];
      for (let index = 0; index < 40; index++) {
        const target = targets[index % targets.length];
        const button = document
          .querySelector(`.record-row b[title="${target.record_id}"]`)
          ?.closest("button");
        if (!button) throw new Error("Cached navigation target is missing.");
        const started = performance.now();
        button.click();
        while (
          !document.querySelector(".record-primary-text")?.textContent?.includes(target.text)
        ) {
          if (performance.now() - started > 2000) throw new Error("Cached Record did not render.");
          await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
        }
        await new Promise<void>((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
        );
        times.push(performance.now() - started);
      }
      return times;
    },
    records.map(({ record_id, text }) => ({ record_id, text })),
  );
  const sorted = [...samples].sort((a, b) => a - b);
  const p50 = sorted[Math.ceil(sorted.length * 0.5) - 1];
  const p95 = sorted[Math.ceil(sorted.length * 0.95) - 1];
  await test.info().attach("cached-record-navigation", {
    body: JSON.stringify({
      contract: "corpus-cached-navigation-v1",
      sample_count: samples.length,
      p50_ms: p50,
      p95_ms: p95,
      samples_ms: samples,
      basis:
        "production Chromium; two warmed synthetic Records; mocked API; no enrichment contention",
    }),
    contentType: "application/json",
  });
  expect(reads).toBe(0);
  expect(p95).toBeLessThan(250);
});

test("background completion retains the reader, active inspector and a later draft", async ({
  page,
}) => {
  const original = CORPUS_RECORDS.find((record) => record.review_state === "metadata")!;
  let records = [{ ...original }];
  let complete: (() => void) | undefined;
  let subscribed = false;
  let eventId = 0;
  let recordReads = 0;
  let queueReads = 0;
  page.on("request", (request) => {
    if (
      request.url().endsWith("/api/graphql") &&
      request.postDataJSON()?.operationName === "CorpusReviewRecords"
    )
      recordReads += 1;
    if (
      request.url().endsWith("/api/graphql") &&
      request.postDataJSON()?.operationName === "CorpusReviewQueue"
    )
      queueReads += 1;
  });
  await mockBackend(page, {
    fixtures: {
      [`/api/pdf/corpus-builds/${CORPUS_BUILD_ID}`]: {
        ...CORPUS_BUILD,
        status: "running",
        stage: "enriching",
        record_count: 1,
        metadata_total: 1,
      },
      [`/api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records`]: () => ({
        items: records,
        total: 1,
        offset: 0,
        limit: 50,
      }),
    },
  });
  await page.routeWebSocket(
    (url) => url.pathname === "/api/ws/events",
    (socket) => {
      socket.send(
        JSON.stringify({
          type: "connection.ready",
          timestamp: "2026-10-02T23:00:00Z",
          payload: {
            protocol_version: 1,
            connection_id: "refresh-regression",
            last_event_id: 0,
            heartbeat_seconds: 20,
            idle_timeout_seconds: 60,
          },
        }),
      );
      socket.onMessage((raw) => {
        const message = JSON.parse(String(raw)) as { type: string; topics?: string[] };
        if (message.type === "subscribe") {
          subscribed ||= Boolean(message.topics?.includes(`corpus-build:${CORPUS_BUILD_ID}`));
          socket.send(
            JSON.stringify({
              type: "subscription.updated",
              timestamp: "2026-10-02T23:00:00Z",
              payload: { topics: message.topics || [], rejected: [] },
            }),
          );
        }
      });
      complete = () =>
        socket.send(
          JSON.stringify({
            type: "corpus.record_completed",
            event_id: ++eventId,
            resource_type: "corpus_build",
            resource_id: CORPUS_BUILD_ID,
            revision: eventId,
            timestamp: "2026-10-02T23:00:01Z",
            payload: { metadata: { record_id: original.record_id, state: "complete" } },
          }),
        );
    },
  );
  await page.goto(`${APP}/pdf?workspace=review&build=${CORPUS_BUILD_ID}`);
  const reader = page.locator(".record-primary-text");
  await expect(reader).toContainText(original.text);
  await expect.poll(() => subscribed).toBe(true);
  await page.locator("#review-tab-evidence").click();
  await reader.evaluate((element) => element.setAttribute("data-refresh-identity", "retained"));

  for (let revision = 2; revision <= 4; revision++) {
    records = [
      { ...original, record_revision: revision, text: `Refreshed source revision ${revision}.` },
    ];
    const before = recordReads;
    complete!();
    await expect.poll(() => recordReads).toBeGreaterThan(before);
    await expect(reader).toContainText(`Refreshed source revision ${revision}.`);
    await expect(reader).toHaveAttribute("data-refresh-identity", "retained");
    await expect(page.locator("#review-tab-evidence")).toHaveAttribute("aria-selected", "true");
  }

  await page.getByRole("button", { name: "Edit text", exact: true }).click();
  const editor = page.locator(".record-review-pane textarea");
  await editor.fill("Uncommitted reviewer correction.");
  const before = recordReads;
  const queueBefore = queueReads;
  complete!();
  await expect.poll(() => queueReads).toBeGreaterThan(queueBefore);
  expect(recordReads).toBe(before);
  await expect(editor).toHaveValue("Uncommitted reviewer correction.");
  await expect(editor).toBeFocused();
  await expect(page.locator("#review-tab-evidence")).toHaveAttribute("aria-selected", "true");
});

for (const colorScheme of ["light", "dark"] as const) {
  for (const stage of ["finalizing_review", "constructing_records", "document_intelligence"]) {
    test(`${stage} keeps reviewed-text editing and saving available (${colorScheme})`, async ({
      page,
    }) => {
      await page.emulateMedia({ colorScheme });
      const original = CORPUS_RECORDS.find((record) => record.review_state === "metadata")!;
      let record = { ...original };
      let savedText = "";
      await mockBackend(page, {
        fixtures: {
          [`/api/pdf/corpus-builds/${CORPUS_BUILD_ID}`]: {
            ...CORPUS_BUILD,
            status: "running",
            stage,
            text_review_available_at: "2026-10-03T00:00:00Z",
            topology_validation: { valid: true },
            record_count: 1,
            metadata_total: 1,
          },
          [`/api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records`]: () => ({
            items: [record],
            total: 1,
            offset: 0,
            limit: 50,
          }),
        },
      });
      await page.route(
        (url) =>
          url.pathname ===
          `/api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records/${original.record_id}/text`,
        async (route) => {
          const payload = route.request().postDataJSON() as {
            text: string;
            expected_revision: number;
          };
          expect(route.request().method()).toBe("PATCH");
          expect(payload.expected_revision).toBe(Number(original.record_revision || 1));
          savedText = payload.text;
          record = {
            ...record,
            text: savedText,
            text_length: savedText.length,
            record_revision: payload.expected_revision + 1,
          };
          await route.fulfill({ json: record });
        },
      );
      await page.goto(`${APP}/pdf?workspace=review&build=${CORPUS_BUILD_ID}`);
      await expect(page.locator("html")).toHaveAttribute("data-color-scheme", colorScheme);
      const reader = page.locator(".record-primary-text");
      await expect(reader).toContainText(original.text);
      const edit = page.getByRole("button", { name: "Edit text", exact: true });
      await expect(edit).toBeEnabled();
      if (stage !== "finalizing_review") {
        await expect(page.locator(".decision-list [data-primary-action]").first()).toBeDisabled();
        await expect(page.getByText("Text review is available.", { exact: false })).toBeVisible();
      }
      await edit.focus();
      await edit.press("Enter");
      const editor = page.locator(".record-review-pane textarea");
      await expect(editor).toBeVisible();
      if (stage !== "finalizing_review")
        await expect(page.getByRole("button", { name: "Clean text", exact: true })).toBeDisabled();
      await editor.fill("A reviewed correction saved during final validation.");
      await expect(editor).toBeFocused();
      const accessibility = await runAxe(page, (builder) =>
        builder
          .include(".record-review-pane")
          .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]),
      );
      expect(accessibility.violations, JSON.stringify(accessibility.violations, null, 2)).toEqual(
        [],
      );
      await page
        .locator(".record-review-pane")
        .getByRole("button", { name: "Save", exact: true })
        .click();
      await expect
        .poll(() => savedText)
        .toBe("A reviewed correction saved during final validation.");
      await expect(editor).toHaveCount(0);
      await expect(reader).toContainText(savedText);
    });
  }
}
