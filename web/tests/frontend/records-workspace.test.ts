/* Copyright 2026 Aaron John Schlosser, PhD. */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createRecordsWorkspace } from "../../src/domain/recordsWorkspace";
import { TABLE_DEFAULTS } from "../../src/domain/runtimeConstants";
import { createRuntimeState } from "../../src/runtime/runtimeState";

// The Records workspace commands set per-file fields on the runtime state, save preferences and sync the URL. The
// rendered view is covered by the legacy baseline's records scenarios; these pin the commands themselves.
function setup(activeFile: unknown = { id: "f1", name: "a.jsonl", records: [] }) {
  const state = createRuntimeState() as unknown as Record<string, any>;
  const calls: string[] = [];
  const overrides: Record<string, unknown> = {
    state,
    activeFile: () => activeFile,
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
        if (name === "persistPrefs" || name === "syncUrl") calls.push(name);
      });
    },
  });
  const workspace = createRecordsWorkspace(deps as never) as Record<
    string,
    (...args: unknown[]) => unknown
  >;
  return { state, calls, workspace };
}

describe("records workspace commands", () => {
  let ctx: ReturnType<typeof setup>;
  beforeEach(() => {
    ctx = setup();
  });

  it("sets a file's query, returns it to page one, saves and syncs the URL", () => {
    ctx.state.pages.f1 = 4;
    ctx.workspace.setRecordsListQuery("hospitality");
    expect(ctx.state.searches.f1).toBe("hospitality");
    expect(ctx.state.pages.f1).toBe(1);
    expect(ctx.calls).toEqual(["persistPrefs", "syncUrl"]);
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
