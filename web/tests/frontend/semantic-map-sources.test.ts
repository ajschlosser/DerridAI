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

const nav = vi.hoisted(() => ({ navigateTo: vi.fn() }));
vi.mock("../../src/domain/sharedNavigation", async (importOriginal) => ({
  ...(await importOriginal<object>()),
  ...nav,
}));
vi.mock("../../src/domain/sharedSession", async (importOriginal) => ({
  ...(await importOriginal<object>()),
  isResearcher: () => false,
}));

import { listSemanticMapSources, openSemanticRecord } from "../../src/domain/semanticMapSources";
import { state } from "../../src/domain/sharedUrlState";

const record = (id: string, work: string) => ({ record_id: id, work, concepts: ["trace"] });

describe("semantic map sources", () => {
  beforeEach(() => {
    nav.navigateTo.mockReset();
    Object.assign(state, { files: [], storeRecords: [], activeFileId: "", dbRecords: [] });
  });

  it("deduplicates records across local files and the store", () => {
    Object.assign(state, {
      files: [{ id: "f1", records: [record("r1", "Glas")] }],
      storeRecords: [record("r1", "Glas"), record("r2", "Of Grammatology")],
    });
    const { records } = listSemanticMapSources();
    expect(records.map((item: { id: string }) => item.id).sort()).toEqual(["r1", "r2"]);
  });

  it("opens a local record and falls back to Search for an unknown one", () => {
    Object.assign(state, { files: [{ id: "f1", records: [record("r1", "Glas")] }] });
    expect(openSemanticRecord("r1")).toBe(true);
    expect(nav.navigateTo).toHaveBeenCalledWith("record", { fileId: "f1", index: 0 });
    expect(openSemanticRecord("nope")).toBe(false);
    expect(nav.navigateTo).toHaveBeenLastCalledWith("global");
    expect(openSemanticRecord("")).toBe(false);
  });
});
