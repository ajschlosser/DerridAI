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

const refreshStores = vi.hoisted(() => vi.fn(async () => []));
const session = vi.hoisted(() => ({ researcher: false }));
vi.mock("../../src/domain/sharedStores", () => ({ refreshStores }));
vi.mock("../../src/domain/sharedSession", () => ({ isResearcher: () => session.researcher }));
const api = vi.hoisted(() => vi.fn());
vi.mock("../../src/domain/legacyApi", () => ({ api }));

import { invalidateCorpusCache } from "../../src/domain/corpusCache";
import { recordOptionLabel } from "../../src/domain/recordOptionLabel";
import {
  ensureCompareLibrary,
  getCompareLibrary,
  getCompareRecord,
} from "../../src/domain/sharedCompareLibrary";
import { loadStorePage, researcherDbRecords } from "../../src/domain/sharedStoreRecords";
import { state } from "../../src/domain/sharedUrlState";

describe("shared Compare library", () => {
  beforeEach(() => {
    session.researcher = false;
    api.mockReset();
    refreshStores.mockClear();
    state.files = [
      {
        id: "f1",
        name: "a.jsonl",
        records: [{ record_id: "r1", work: "Glas", document_author: "Derrida" }],
      },
    ];
    state.activeStore = "";
    state.storeRecords = [];
    state.storeSearchResults = [];
    invalidateCorpusCache();
  });

  it("indexes workspace records and resolves a key to its record and label", () => {
    expect(recordOptionLabel({ name: "a.jsonl" }, { record_id: "r1", work: "Glas" }, 0)).toBe(
      "a.jsonl · r1 · Glas",
    );
    expect(getCompareLibrary()).toEqual([
      { value: "f1::0", label: "a.jsonl · r1 · Glas", search: "a.jsonl · r1 · glas derrida" },
    ]);
    expect(getCompareRecord("f1::0")?.label).toBe("a.jsonl · r1 · Glas");
    expect(getCompareRecord("nope::0")).toBeNull();
  });

  it("gives researchers store records without the Chroma id or text policy", async () => {
    session.researcher = true;
    state.activeStore = "s";
    state.storeRecords = [
      { _chroma_id: "c1", record_id: "r9", work: "Of Grammatology", _researcher_text_policy: "x" },
    ];
    expect(getCompareLibrary()[0].value).toBe("c1");
    const found = getCompareRecord("c1");
    expect(found?.record).toEqual({ record_id: "r9", work: "Of Grammatology" });
    await ensureCompareLibrary();
    expect(api).not.toHaveBeenCalled();
  });

  it("merges search hits ahead of browsed records by id", () => {
    state.storeSearchResults = [{ id: "c1", record: { record_id: "hit" } }];
    state.storeRecords = [
      { _chroma_id: "c1", record_id: "page" },
      { _chroma_id: "c2", record_id: "p2" },
    ];
    expect(researcherDbRecords().map((r) => r.record_id)).toEqual(["hit", "p2"]);
  });

  it("loads a store page and clamps an out-of-range page", async () => {
    state.activeStore = "s";
    state.storePage = 5;
    state.storePageSize = 10;
    api
      .mockResolvedValueOnce({ records: [], count: 12 })
      .mockResolvedValueOnce({ records: [{ record_id: "x" }], count: 12 });
    await loadStorePage();
    expect(state.storePage).toBe(2);
    expect(api.mock.calls[1][0]).toContain("offset=10");
    expect(state.storeRecords).toEqual([{ record_id: "x" }]);
  });
});
