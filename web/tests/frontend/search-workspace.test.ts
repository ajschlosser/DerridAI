/* Copyright 2026 Aaron John Schlosser, PhD. */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createSearchWorkspace } from "../../src/domain/searchWorkspace";
import { createRuntimeState } from "../../src/runtime/runtimeState";

// The Search workspace commands set fields on the runtime state, save preferences and sync the URL. The view-level
// behavior is covered by the legacy baseline's search scenarios; these pin the commands themselves.
function setup() {
  const state = createRuntimeState() as unknown as Record<string, any>;
  const calls: string[] = [];
  // Every helper the workspace destructures is a spy; the three that matter here also record their order.
  const deps = new Proxy(
    { state },
    {
      get: (target, name: string) => {
        if (name in target) return (target as Record<string, unknown>)[name];
        return vi.fn(() => {
          if (name === "persistPrefs" || name === "syncUrl" || name === "shell") calls.push(name);
        });
      },
    },
  );
  const workspace = createSearchWorkspace(deps as never) as Record<
    string,
    (...args: unknown[]) => unknown
  >;
  return { state, calls, workspace };
}

describe("search workspace commands", () => {
  let ctx: ReturnType<typeof setup>;
  beforeEach(() => {
    ctx = setup();
  });

  it("sets the query, returns to page one, saves and syncs the URL", () => {
    ctx.state.globalPage = 4;
    expect(ctx.workspace.updateSearchQuery("  hospitality")).toBe("  hospitality");
    expect(ctx.state.globalSearch).toBe("  hospitality");
    expect(ctx.state.globalPage).toBe(1);
    expect(ctx.calls).toEqual(["persistPrefs", "syncUrl"]);
  });

  it("never sets a page below one", () => {
    ctx.workspace.setSearchPage(-3);
    expect(ctx.state.globalPage).toBe(1);
    ctx.workspace.setSearchPage("7");
    expect(ctx.state.globalPage).toBe(7);
  });

  it("toggles a facet value on and off", () => {
    ctx.workspace.toggleSearchFacet("topics", "text");
    expect(ctx.state.searchFacetFilters).toEqual({ topics: ["text"] });
    ctx.workspace.toggleSearchFacet("topics", "sign");
    expect(ctx.state.searchFacetFilters).toEqual({ topics: ["text", "sign"] });
    ctx.workspace.toggleSearchFacet("topics", "text");
    ctx.workspace.toggleSearchFacet("topics", "sign");
    expect(ctx.state.searchFacetFilters).toEqual({});
  });

  it("clears every filter and any database results", () => {
    ctx.state.searchFacetFilters = { topics: ["a"] };
    ctx.state.globalFilters = [{ id: "1" }];
    ctx.state.dbSearchWhere = { speaker: "x" };
    ctx.state.storeSearchResults = [{ id: "r" }];
    ctx.workspace.clearSearchAllFilters();
    expect(ctx.state.searchFacetFilters).toEqual({});
    expect(ctx.state.globalFilters).toEqual([]);
    expect(ctx.state.dbSearchWhere).toEqual({});
    expect(ctx.state.storeSearchResults).toEqual([]);
    expect(ctx.state.globalPage).toBe(1);
  });
});
