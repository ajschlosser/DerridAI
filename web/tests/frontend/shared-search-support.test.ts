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
import { evidenceSelection, searchFacets } from "../../src/domain/sharedSearchSupport";
import { dbSearchWhere, display, pages, recordFields } from "../../src/domain/sharedRecordHelpers";
import { state } from "../../src/domain/sharedUrlState";

describe("shared record helpers", () => {
  it("formats page ranges and empty pages", () => {
    expect(pages({})).toBe("—");
    expect(pages({ page_start: 3, page_end: 3 })).toBe(display(3));
    expect(pages({ page_start: 3, page_end: 5 })).toContain("–");
  });
  it("drops blank search clauses and reads the shared state", () => {
    state.dbSearchWhere = { work: "Grammatology", author: "  " };
    expect(dbSearchWhere()).toEqual({ work: "Grammatology" });
    state.dbSearchWhere = {};
  });
  it("lists record fields from the loaded corpus without the runtime", () => {
    expect(Array.isArray(recordFields())).toBe(true);
  });
});

describe("shared search support", () => {
  it("builds facets and evidence selection over the shared state", () => {
    expect(typeof searchFacets.buildSearchFacets).toBe("function");
    expect(typeof evidenceSelection.toggleDbEvidence).toBe("function");
    expect(typeof evidenceSelection.clearSelectedEvidence).toBe("function");
  });
});
