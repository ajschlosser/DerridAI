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
import { createSearchWorkspace } from "../../src/domain/searchWorkspace";
import { createRuntimeState } from "../../src/state/runtimeState";

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
