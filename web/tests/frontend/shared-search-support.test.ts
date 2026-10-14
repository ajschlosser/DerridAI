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
import "../../src/domain/appBootstrap";
import { evidenceSelection, searchFacets } from "../../src/domain/sharedSearchSupport";
import { dbSearchWhere, display, pages, recordFields } from "../../src/domain/sharedRecordHelpers";
import { annotationsWorkspace } from "../../src/domain/sharedAnnotations";
import { recordPresenters } from "../../src/domain/sharedRecordPresenters";
import { applyRecordChanges } from "../../src/domain/sharedRecordEditing";
import { recordDialogs } from "../../src/domain/sharedRecordDialogs";
import {
  activeFile,
  bulkEditRowsForScope,
  fileJsonl,
  needsReviewItems,
} from "../../src/domain/sharedRecordScopes";
import { decorateDisabledControls } from "../../src/domain/disabledControls";
import { canUse } from "../../src/domain/sharedSession";
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

describe("shared annotations, record editing and presenters", () => {
  it("build over the shared state without the runtime", () => {
    expect(typeof annotationsWorkspace.allAnnotations).toBe("function");
    expect(annotationsWorkspace.allAnnotations()).toEqual([]);
    expect(typeof recordPresenters.pager).toBe("function");
    expect(applyRecordChanges({ records: [] }, 0, { a: 1 })).toBe(0);
  });
  it("reports capabilities as false without a signed-in user", () => {
    expect(canUse("manageCorpus")).toBe(false);
    expect(canUse("unknown")).toBe(false);
  });
});

describe("shared record dialogs and scopes", () => {
  it("build over the shared state without the runtime", () => {
    expect(typeof recordDialogs.openBulkFieldEditor).toBe("function");
    expect(typeof recordDialogs.openStoreRecordEditor).toBe("function");
    expect(activeFile()).toBeNull();
    expect(needsReviewItems()).toEqual([]);
    expect(bulkEditRowsForScope("selected")).toEqual([]);
    expect(fileJsonl({ records: [{ a: 1 }, { b: 2 }] })).toBe('{"a":1}\n{"b":2}\n');
  });
  it("explains a disabled control with its explicit reason", () => {
    const root = document.createElement("div");
    root.innerHTML = '<button disabled data-disabled-reason="Because">Go</button>';
    decorateDisabledControls(root);
    expect(root.querySelector("button")?.title).toBe("Because");
  });
});
