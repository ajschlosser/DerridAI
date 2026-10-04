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

import { describe, expect, it, vi } from "vitest";
import { createDashboardData } from "../../src/domain/dashboardData";

// The dashboard's markup is covered by the legacy baseline's home scenarios; this pins the latest-annotation click.
describe("dashboard latest annotation", () => {
  it("opens the shared annotation's record in its own store", () => {
    const openAnnotationsWorkspaceRecord = vi.fn();
    const deps = new Proxy(
      { state: {}, openAnnotationsWorkspaceRecord } as Record<string, unknown>,
      { get: (target, name: string) => target[name] ?? vi.fn() },
    );
    createDashboardData(deps as never).openSharedAnnotationRecord("derrida", "rec-7");
    expect(openAnnotationsWorkspaceRecord).toHaveBeenCalledWith({
      server: true,
      source: "derrida",
      record_id: "rec-7",
    });
  });
});

function dataWith(overrides: Record<string, unknown>) {
  const state = {
    files: [],
    stores: [],
    storeWorkStats: [],
    activeStore: "",
    ...(overrides.state as object),
  };
  const base: Record<string, unknown> = {
    state,
    allRows: () => [],
    api: vi.fn(),
    isResearcher: () => false,
    memoCorpus: (_key: string, build: () => unknown) => build(),
    openAnnotationsWorkspaceRecord: vi.fn(),
    recordStores: () => [],
    researcherDbRecords: () => [],
    responseCacheStore: () => null,
    ...overrides,
  };
  return createDashboardData(base as never);
}

describe("dashboard totals", () => {
  it("counts works, flagged records and edits across the loaded corpus", () => {
    const rows = [
      { record: { work: "A", needs_review: true, updates: [1, 2] } },
      { record: { work: "A", updates: [] } },
      { record: { work: "B" } },
    ];
    const data = dataWith({
      state: { files: [{}] },
      allRows: () => rows,
      recordStores: () => [{ count: 4 }, { count: 6 }],
      responseCacheStore: () => ({ count: 3 }),
    });
    expect(data.dashboardTotals()).toMatchObject({
      records: 3,
      works: 2,
      flagged: 1,
      files: 1,
      changes: 2,
      dbs: 2,
      dbRecords: 10,
      cacheResponses: 3,
    });
  });

  it("reports the active store for a researcher, without a response cache", () => {
    const data = dataWith({
      state: { activeStore: "b", storeWorkStats: [{}, {}] },
      isResearcher: () => true,
      recordStores: () => [
        { name: "a", count: 1 },
        { name: "b", count: 5 },
      ],
    });
    expect(data.dashboardTotals()).toMatchObject({
      records: 5,
      works: 2,
      dbs: 2,
      cacheResponses: 0,
    });
  });
});

describe("dashboard record preview", () => {
  it("returns the last viewed workspace record, then falls back to a loaded one", async () => {
    const file = { id: "f1", records: [{ title: "x" }, { title: "y" }] };
    const viewed = dataWith({
      state: { files: [file], lastViewedRecord: { kind: "workspace", fileId: "f1", index: 1 } },
    });
    expect(await viewed.dashboardRecordPreview()).toEqual({
      record: file.records[1],
      target: { kind: "workspace", fileId: "f1", index: 1 },
      lastViewed: true,
    });
    const empty = dataWith({});
    expect(await empty.dashboardRecordPreview()).toEqual({
      record: null,
      target: null,
      lastViewed: false,
    });
  });

  it("fetches a last viewed database record that is not in the loaded page", async () => {
    const api = vi.fn().mockResolvedValue({ record_id: "r1" });
    const data = dataWith({
      api,
      state: { activeStore: "s", lastViewedRecord: { kind: "database", store: "s", id: "r1" } },
    });
    expect((await data.dashboardRecordPreview()).target).toEqual({
      kind: "database",
      store: "s",
      id: "r1",
    });
    expect(api).toHaveBeenCalledWith("/api/stores/s/records/r1");
  });
});
