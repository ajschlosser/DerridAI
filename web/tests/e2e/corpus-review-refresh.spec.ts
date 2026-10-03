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
import { CORPUS_BUILD, CORPUS_BUILD_ID, CORPUS_RECORDS, mockBackend } from "./support/mock-backend";

const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

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
