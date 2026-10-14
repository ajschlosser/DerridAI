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

vi.mock("../../src/domain/sharedWorkspaceStorage", async (importOriginal) => ({
  ...(await importOriginal<object>()),
  persistPrefs: vi.fn(),
}));
vi.mock("../../src/domain/sharedNavigation", async (importOriginal) => ({
  ...(await importOriginal<object>()),
  syncUrl: vi.fn(),
}));

import "../../src/domain/appBootstrap";
import { pageInfo, setActiveStore, setListFilterValue } from "../../src/domain/listPaging";
import { recordsWorkspace } from "../../src/domain/sharedRecordsWorkspace";
import { searchByMetadata } from "../../src/domain/workspaceActions";
import { state } from "../../src/domain/sharedUrlState";

describe("list paging helpers", () => {
  beforeEach(() => {
    Object.assign(state, { pageSize: 10, listFilters: {}, activeStore: "", storePresence: {} });
  });

  it("clamps the page into range", () => {
    expect(pageInfo(25, 99)).toEqual({ page: 3, pages: 3, start: 20, end: 25 });
    expect(pageInfo(0, 0)).toEqual({ page: 1, pages: 1, start: 0, end: 0 });
  });

  it("sets and clears a list filter", () => {
    setListFilterValue("f1", "work", "Glas");
    expect(state.listFilters.f1).toEqual({ work: "Glas" });
    setListFilterValue("f1", "work", "");
    expect(state.listFilters.f1).toEqual({});
  });

  it("keeps only the selected store's presence when switching", () => {
    Object.assign(state, {
      activeStore: "a",
      storePresence: { a: { x: 1 }, b: { y: 2 } },
    });
    setActiveStore("b");
    expect(state.activeStore).toBe("b");
    expect(state.storePresence).toEqual({ b: { y: 2 } });
  });
});

describe("shared Records workspace", () => {
  it("builds a list snapshot from the shared state without the runtime", () => {
    const snapshot = recordsWorkspace.getRecordsListSnapshot();
    expect(snapshot).toBeTruthy();
    expect(Array.isArray(snapshot.files)).toBe(true);
  });

  it("jumps to Search on a metadata value", () => {
    searchByMetadata("work", "Glas", { contains: false });
    expect(state.globalPage).toBe(1);
  });
});
