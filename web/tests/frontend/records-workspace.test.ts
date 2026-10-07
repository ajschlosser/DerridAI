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

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createRecordsWorkspace } from "../../src/domain/recordsWorkspace";
import { TABLE_DEFAULTS } from "../../src/domain/runtimeConstants";
import { createRuntimeState } from "../../src/state/runtimeState";
import { createListState, listState } from "../../src/state/workspaceState";

// The Records workspace commands set per-file fields on the runtime state, save preferences and sync the URL. The
// modern Records Playwright workflow covers rendered interactions; these tests pin the commands themselves.
function setup(activeFile: unknown = { id: "f1", name: "a.jsonl", records: [] }) {
  // The list fields are shared module state, so start each test from the defaults.
  Object.assign(listState, createListState());
  const state = createRuntimeState() as unknown as Record<string, any>;
  const calls: string[] = [];
  const refreshPresenceForRows = vi.fn(async () => undefined);
  const needsReviewItems = vi.fn((rows: any[] = []) =>
    rows.filter((row) => row.record.needs_review === true),
  );
  const tableAvailableFields = vi.fn(() => ["text"]);
  let corpusVersion = 0;
  const overrides: Record<string, unknown> = {
    state,
    activeFile: () => activeFile,
    canUse: () => true,
    hasCapability: () => true,
    hasCorpusDb: () => false,
    dbUnavailableReason: () => "",
    recordStores: () => [],
    corpusVersion: () => corpusVersion,
    pageInfo: (count: number, page: number) => {
      const pageSize = Math.max(1, Number(state.pageSize) || 100);
      const pages = Math.max(1, Math.ceil(count / pageSize));
      const current = Math.min(pages, Math.max(1, Number(page) || 1));
      const start = (current - 1) * pageSize;
      return { page: current, pages, start, end: Math.min(count, start + pageSize) };
    },
    needsReviewItems,
    tableAvailableFields,
    getTableColumns: () => ["text"],
    rowMatchesListFilters: () => true,
    recordDbStatus: () => ({ kind: "unknown", label: "Unknown", title: "" }),
    recordsListCell: (row: any) => String(row.record.text || ""),
    reviewKey: (file: any, index: number) => `${file.id}::${index}`,
    evidenceIsSelected: () => false,
    workspaceEvidenceSelectionKey: (file: any, index: number) => `workspace:${file.id}:${index}`,
    refreshPresenceForRows,
    toggleSort: (sort: { key: string; dir: number }, key: string) => {
      if (sort.key === key) sort.dir *= -1;
      else {
        sort.key = key;
        sort.dir = 1;
      }
    },
  };
  const deps = new Proxy(overrides, {
    get: (target, name: string) => {
      if (name in target) return target[name];
      return vi.fn(() => {
        if (name.startsWith("persist") || name === "syncUrl") calls.push(name);
      });
    },
  });
  const workspace = createRecordsWorkspace(deps as never) as Record<
    string,
    (...args: unknown[]) => unknown
  >;
  return {
    state,
    calls,
    workspace,
    refreshPresenceForRows,
    needsReviewItems,
    tableAvailableFields,
    bumpCorpusVersion: () => {
      corpusVersion += 1;
    },
  };
}

describe("records workspace commands", () => {
  let ctx: ReturnType<typeof setup>;
  beforeEach(() => {
    ctx = setup();
  });

  it("keeps snapshot reads pure and refreshes visible-row presence only on command", async () => {
    const record = { record_id: "r1", text: "trace" };
    const local = setup({ id: "f1", name: "a.jsonl", records: [record] });

    const snapshot = local.workspace.getRecordsListSnapshot() as { rows: Array<{ index: number }> };
    expect(snapshot.rows.map((row) => row.index)).toEqual([0]);
    expect(local.refreshPresenceForRows).not.toHaveBeenCalled();

    await local.workspace.refreshRecordsListPresence([0]);
    expect(local.refreshPresenceForRows).toHaveBeenCalledWith([
      { file: expect.any(Object), record, index: 0 },
    ]);
  });

  it("caches corpus-derived row metadata and never normalizes page state during a read", () => {
    const local = setup({
      id: "f1",
      name: "a.jsonl",
      records: [
        { record_id: "r1", text: "trace", needs_review: true },
        { record_id: "r2", text: "writing", needs_review: false },
      ],
    });
    local.state.pages.f1 = 99;

    const first = local.workspace.getRecordsListSnapshot() as { page: number; flagged: number };
    const second = local.workspace.getRecordsListSnapshot() as { page: number; flagged: number };

    expect(first.page).toBe(1);
    expect(second.flagged).toBe(1);
    expect(local.state.pages.f1).toBe(99);
    expect(local.needsReviewItems).toHaveBeenCalledTimes(1);
    expect(local.tableAvailableFields).toHaveBeenCalledTimes(1);

    local.bumpCorpusVersion();
    local.workspace.getRecordsListSnapshot();
    expect(local.needsReviewItems).toHaveBeenCalledTimes(2);
    expect(local.tableAvailableFields).toHaveBeenCalledTimes(2);
  });

  it("sets a file's query, returns it to page one, saves and syncs the URL", () => {
    ctx.state.pages.f1 = 4;
    ctx.workspace.setRecordsListQuery("hospitality");
    expect(ctx.state.searches.f1).toBe("hospitality");
    expect(ctx.state.pages.f1).toBe(1);
    expect(ctx.calls).toEqual(["persistListPreferences", "syncUrl"]);
  });

  it("does nothing without an active file", () => {
    const none = setup(null);
    none.workspace.setRecordsListQuery("x");
    none.workspace.setRecordsListPage(3);
    expect(none.state.searches).toEqual({});
    expect(none.calls).toEqual([]);
  });

  it("never sets a page below one", () => {
    ctx.workspace.setRecordsListPage(-2);
    expect(ctx.state.pages.f1).toBe(1);
    ctx.workspace.setRecordsListPage("6");
    expect(ctx.state.pages.f1).toBe(6);
  });

  it("starts sorting by start page, then flips the direction on the same key", () => {
    ctx.workspace.setRecordsListSort("work");
    expect(ctx.state.sorts.f1).toEqual({ key: "work", dir: 1 });
    ctx.workspace.setRecordsListSort("work");
    expect(ctx.state.sorts.f1).toEqual({ key: "work", dir: -1 });
    expect(ctx.state.pages.f1).toBe(1);
  });

  it("clears a file's filters and restores the default columns", () => {
    ctx.state.listFilters.f1 = { work: "Glas" };
    ctx.workspace.clearRecordsListFilters();
    expect(ctx.state.listFilters.f1).toEqual({});
    ctx.state.tableColumns.list = ["text"];
    ctx.workspace.resetRecordsListColumns();
    expect(ctx.state.tableColumns.list).toEqual(TABLE_DEFAULTS.list);
    expect(ctx.state.tableColumns.list).not.toBe(TABLE_DEFAULTS.list);
  });
});
