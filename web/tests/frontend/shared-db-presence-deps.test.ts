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

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  notifyVectorStoresChanged,
  refreshOperationsPanelOnly,
  registerOperationHooks,
} from "../../src/domain/operationHooks";
import { reviewItemFromKey, selectedReviewItems } from "../../src/domain/reviewItems";
import {
  candidateChromaIds,
  corpusStoreExists,
  dbUnavailableReason,
  hasCorpusDb,
  recordStores,
  storeReceipt,
} from "../../src/domain/storeAvailability";
import { state } from "../../src/domain/sharedUrlState";

describe("review items", () => {
  const file = { id: "f1", name: "a.jsonl", records: [{ record_id: "r0" }, { record_id: "r1" }] };
  it("resolves keys against the loaded files and rejects stale ones", () => {
    const s = { files: [file], reviewSelection: new Set(["f1::1", "f1::9", "nope::0", "bad"]) };
    expect(reviewItemFromKey(s, "f1::1")).toMatchObject({ index: 1, record: { record_id: "r1" } });
    expect(reviewItemFromKey(s, "f1::9")).toBeNull();
    expect(reviewItemFromKey(s, "bad")).toBeNull();
    expect(selectedReviewItems(s)).toHaveLength(1);
  });
});

describe("store availability", () => {
  const saved = {
    stores: state.stores,
    health: state.health,
    activeStore: state.activeStore,
    upsertState: state.upsertState,
  };
  afterEach(() => Object.assign(state, saved));

  it("ignores the response cache and reports why the database is unavailable", () => {
    state.stores = [{ name: "corpus" }, { name: "_response_cache" }];
    state.health = { chroma: { available: false } };
    expect(recordStores().map((s: { name: string }) => s.name)).toEqual(["corpus"]);
    expect(corpusStoreExists("corpus")).toBe(true);
    expect(corpusStoreExists("_response_cache")).toBe(false);
    expect(hasCorpusDb()).toBe(false);
    expect(dbUnavailableReason()).toMatch(/ChromaDB/);
    state.health = { chroma: { available: true } };
    expect(hasCorpusDb()).toBe(true);
    expect(dbUnavailableReason()).toBe("");
    state.stores = [];
    expect(dbUnavailableReason()).toMatch(/corpus vector database/);
  });

  it("lists candidate Chroma ids from the receipt and the logical record id once each", () => {
    const file = { id: "f1", name: "a.jsonl" };
    state.activeStore = "corpus";
    state.upsertState = { corpus: { "f1::0": { chroma_id: "c-1" } } };
    expect(storeReceipt("corpus", file, 0)).toEqual({ chroma_id: "c-1" });
    expect(candidateChromaIds(file, 0, { record_id: "r9" })).toEqual(["c-1", "r9", "a.jsonl::r9"]);
    expect(candidateChromaIds(file, 1, {})).toEqual([]);
  });
});

describe("operation hooks", () => {
  afterEach(() => registerOperationHooks(null));
  it("are no-ops until registered, then forward", () => {
    expect(refreshOperationsPanelOnly()).toBeUndefined();
    const refresh = vi.fn(() => "r");
    const notify = vi.fn(() => "n");
    registerOperationHooks({
      refreshOperationsPanelOnly: refresh,
      notifyVectorStoresChanged: notify,
    });
    expect(refreshOperationsPanelOnly()).toBe("r");
    expect(notifyVectorStoresChanged()).toBe("n");
  });
});
