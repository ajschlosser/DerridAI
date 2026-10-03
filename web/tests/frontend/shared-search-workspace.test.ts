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

import { describe, expect, it } from "vitest";
// The app enters through the runtime; sharedNavigation reaches it through the operations panel, so import it first.
import "../../src/runtime/runtimeBridge";
import { searchWorkspace } from "../../src/domain/sharedSearchWorkspace";
import { getTableColumns, tableAvailableFields } from "../../src/domain/tableColumns";
import { state } from "../../src/domain/sharedUrlState";

describe("shared search workspace", () => {
  it("is built over the shared state without the runtime's wiring", () => {
    expect(searchWorkspace.searchScope()).toBe("loaded");
    state.globalSearchMode = "database";
    expect(searchWorkspace.searchScope()).toBe("database");
    state.globalSearchMode = "loaded";
  });
  it("exposes every command the Search view calls", () => {
    for (const name of [
      "getSearchWorkspaceSnapshot",
      "runSearchWorkspace",
      "setSearchScope",
      "setSearchColumns",
      "toggleSearchFacet",
      "searchResultAction",
      "runSearchSelectionAction",
      "restoreSearchViewFromHref",
    ])
      expect(typeof (searchWorkspace as Record<string, unknown>)[name]).toBe("function");
  });
});

describe("table columns", () => {
  it("lists the fields of the given rows, sorted, without updates", () => {
    const rows = [{ record: { text: "a", updates: [], page_start: 1 } }];
    expect(tableAvailableFields(rows, ["zz"])).toEqual(
      expect.arrayContaining(["page_start", "text", "zz"]),
    );
    expect(tableAvailableFields(rows)).not.toContain("updates");
  });
  it("keeps stored columns that exist and falls back to the first available", () => {
    state.tableColumns = { custom: ["gone"] };
    expect(getTableColumns("custom", ["a", "b", "c"])).toEqual(["a", "b", "c"]);
    state.tableColumns = { custom: ["b", "gone"] };
    expect(getTableColumns("custom", ["a", "b"])).toEqual(["b"]);
  });
});
