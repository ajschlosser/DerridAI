/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it, vi } from "vitest";
import { createWorksWorkspace } from "../../src/domain/worksWorkspace";
import { createRuntimeState } from "../../src/runtime/runtimeState";

// The rendered Works view is covered by the legacy baseline's works scenarios (recorded before this logic moved);
// these pin the commands themselves.
function setup(overrides: Record<string, unknown> = {}) {
  const state = createRuntimeState() as unknown as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
  const calls: string[] = [];
  const spies: Record<string, ReturnType<typeof vi.fn>> = {};
  let ids = 0;
  const deps = new Proxy(
    { state, uid: () => `id${++ids}`, ...overrides } as Record<string, unknown>,
    {
      get: (target, name: string) => {
        if (name in target) return target[name];
        spies[name] ??= vi.fn(() => {
          if (name === "persistPrefs" || name === "syncUrl" || name === "navigateTo")
            calls.push(name);
        });
        return spies[name];
      },
    },
  );
  const workspace = createWorksWorkspace(deps as never) as Record<
    string,
    (...args: unknown[]) => unknown
  >;
  return { state, calls, spies, workspace };
}

describe("works workspace commands", () => {
  it("sets the works filter and the overview, saving and syncing the URL", () => {
    const { state, calls, workspace } = setup();
    workspace.setWorksSearch("Glas");
    workspace.setWorksOverview("Of Grammatology");
    expect(state.worksSearch).toBe("Glas");
    expect(state.workOverview).toBe("Of Grammatology");
    expect(calls).toEqual(["persistPrefs", "syncUrl", "persistPrefs", "syncUrl"]);
    workspace.setWorksSearch(null);
    expect(state.worksSearch).toBe("");
  });

  it("opens a work's records in Search, optionally only those needing review", () => {
    const { state, calls, workspace } = setup();
    workspace.searchWorkRecords("Glas");
    expect(state.globalSearchMode).toBe("traditional");
    expect(state.globalFilters).toEqual([{ id: "id1", field: "work", op: "eq", value: "Glas" }]);
    expect(calls).toEqual(["persistPrefs", "navigateTo"]);
    workspace.searchWorkRecords("Glas", { needsReview: true });
    expect(state.globalFilters.map((filter: { field: string }) => filter.field)).toEqual([
      "work",
      "needs_review",
    ]);
    expect(state.globalPage).toBe(1);
  });

  it("opens a work's annotations by its name", () => {
    const { state, spies, workspace } = setup();
    workspace.openWorkAnnotations("Glas");
    expect(state.annotationSearch).toBe("Glas");
    expect(state.annotationView).toBe("works");
    expect(spies.navigateTo).toHaveBeenCalledWith("annotations");
  });

  it("reviews only a work's flagged records", () => {
    const rows = [{ record: { needs_review: true } }];
    const { spies, workspace } = setup({
      workIndex: () => new Map([["Glas", { rows }]]),
      needsReviewItems: (items: unknown[]) => items,
    });
    workspace.reviewFlaggedWork("Glas");
    expect(spies.openTouchup).toHaveBeenCalledWith(rows);
    workspace.reviewFlaggedWork("Unknown work");
    expect(spies.openTouchup).toHaveBeenLastCalledWith([]);
  });
});
