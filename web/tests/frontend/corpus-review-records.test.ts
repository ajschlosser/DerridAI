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

import { ref, watch } from "vue";
import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as graphqlClient from "../../src/api/graphql/client";

const corpusReviewReads = vi.hoisted(() => ({
  queuePage: vi.fn(),
  records: vi.fn(),
  rows: vi.fn(),
  texts: vi.fn(),
  metadataFacets: vi.fn(),
}));

vi.mock("../../src/features/corpus-builder/api/reviewReads", async () => {
  const actual = await vi.importActual<
    typeof import("../../src/features/corpus-builder/api/reviewReads")
  >("../../src/features/corpus-builder/api/reviewReads");
  return { ...actual, corpusReviewReads };
});

import { useCorpusReviewRecords } from "../../src/features/corpus-builder/composables/useCorpusReviewRecords";

function row(id: string, revision = 1, overrides: Record<string, unknown> = {}) {
  return {
    record_id: id,
    record_revision: revision,
    state_version: null,
    page_start: null,
    page_end: null,
    text_length: 10,
    text_preview: `Preview of ${id}`,
    review_state: "ready",
    review_disposition: "pending",
    review_issue_codes: [],
    metadata_llm_processed: false,
    needs_review: true,
    source_quality_issues: false,
    metadata_complete: true,
    ...overrides,
  };
}

function record(id: string, revision = 1, overrides: Record<string, unknown> = {}) {
  return {
    record_id: id,
    record_revision: revision,
    text: `Text for ${id}`,
    text_length: 10,
    source_block_ids: [],
    source_spans: [],
    ...overrides,
  } as any;
}

function page(rows: unknown[], overrides: Record<string, unknown> = {}) {
  return {
    rows,
    total: rows.length,
    offset: 0,
    limit: 50,
    hasNextPage: false,
    hasPreviousPage: false,
    nextCursor: null,
    previousCursor: null,
    dataGeneration: 1,
    topologyGeneration: 1,
    topologyCount: rows.length,
    counts: {},
    ...overrides,
  };
}

function setup(overrides: Record<string, unknown> = {}) {
  const selectedBuildId = ref("b1");
  const currentBuild = ref<any>({ build_id: "b1" });
  const recordOffset = ref(0);
  const reviewQueue = ref<any>("all");
  const recordQuery = ref("");
  const selectedRecordId = ref("");
  const selectedRecord = ref<any>(null);
  let activeDraft = false;
  const activateRecord = vi.fn((rec: any) => {
    selectedRecordId.value = rec.record_id;
    selectedRecord.value = rec;
  });
  const onSelectionCleared = vi.fn(() => {
    selectedRecordId.value = "";
    selectedRecord.value = null;
  });
  const onPageLoaded = vi.fn();
  const onFacets = vi.fn();
  const onError = vi.fn();

  const reviewRecords = useCorpusReviewRecords({
    selectedBuildId,
    currentBuild,
    recordOffset,
    pageSize: 50,
    reviewQueue,
    recordQuery,
    selectedRecordId,
    selectedRecord,
    hasActiveDraft: () => activeDraft,
    activateRecord,
    onSelectionCleared,
    onPageLoaded,
    onFacets,
    onError,
    ...overrides,
  } as any);

  return {
    reviewRecords,
    selectedBuildId,
    selectedRecordId,
    selectedRecord,
    recordOffset,
    reviewQueue,
    recordQuery,
    activateRecord,
    onSelectionCleared,
    onError,
    setActiveDraft: (value: boolean) => {
      activeDraft = value;
    },
  };
}

describe("useCorpusReviewRecords", () => {
  it("keeps the open Record mounted throughout a background refresh", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1")]));
    corpusReviewReads.records.mockResolvedValueOnce([record("r1")]);
    await state.reviewRecords.refreshRecords();
    const selections: Array<string | null> = [];
    const stop = watch(state.selectedRecord, (value) => selections.push(value?.record_id ?? null), {
      flush: "sync",
    });
    let release!: (records: unknown[]) => void;
    corpusReviewReads.records.mockImplementationOnce(
      () => new Promise((resolve) => (release = resolve)),
    );
    const refreshing = state.reviewRecords.refreshRecord("r1");
    await flushPromises();
    expect(state.selectedRecord.value?.record_id).toBe("r1");
    release([record("r1", 2)]);
    await refreshing;
    stop();
    expect(selections).not.toContain(null);
    expect(state.selectedRecord.value?.record_revision).toBe(2);
  });

  it("does not reactivate an unchanged selection on queue-only refresh", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1")]));
    corpusReviewReads.records.mockResolvedValueOnce([record("r1")]);
    await state.reviewRecords.refreshRecords();
    state.activateRecord.mockClear();
    await state.reviewRecords.refreshRecords();
    expect(state.activateRecord).not.toHaveBeenCalled();
  });

  it("preserves a draft begun while the same Record's refresh is in flight", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1")]));
    corpusReviewReads.records.mockResolvedValueOnce([record("r1")]);
    await state.reviewRecords.refreshRecords();
    let release!: (records: unknown[]) => void;
    corpusReviewReads.records.mockImplementationOnce(
      () => new Promise((resolve) => (release = resolve)),
    );
    const refreshing = state.reviewRecords.refreshRecord("r1");
    await flushPromises();
    state.selectedRecord.value = record("r1", 1, { text: "Draft started during refresh" });
    state.setActiveDraft(true);
    release([record("r1", 2, { text: "Server text" })]);
    await refreshing;
    expect(state.selectedRecord.value?.text).toBe("Draft started during refresh");
  });

  it("does not let a delayed queue response override a newer manual selection", async () => {
    const state = setup();
    let resolvePage!: (value: unknown) => void;
    corpusReviewReads.queuePage.mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePage = resolve;
      }),
    );
    const loading = state.reviewRecords.refreshRecords();
    await state.reviewRecords.selectRecord(record("r2"));
    resolvePage(page([row("r1"), row("r2")]));
    await loading;
    expect(state.selectedRecordId.value).toBe("r2");
    expect(state.activateRecord).toHaveBeenCalledTimes(1);
  });

  it("discards an ignored-abort Record response after switching builds", async () => {
    const state = setup();
    let resolveRecord!: (value: unknown) => void;
    corpusReviewReads.records.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveRecord = resolve;
      }),
    );
    const loading = state.reviewRecords.selectRecord(row("r1"));
    state.selectedBuildId.value = "b2";
    resolveRecord([record("r1")]);
    await loading;
    expect(state.selectedRecord.value).toBeNull();
    expect(state.reviewRecords.loadingRecordId.value).toBe("");
    expect(state.activateRecord).not.toHaveBeenCalled();
  });

  it("opens the newer authoritative revision when an older foreground read finishes", async () => {
    const state = setup();
    let release!: (records: ReturnType<typeof record>[]) => void;
    corpusReviewReads.records.mockImplementationOnce(
      () => new Promise<ReturnType<typeof record>[]>((resolve) => (release = resolve)),
    );
    const pending = state.reviewRecords.selectRecord(row("r1"));
    state.reviewRecords.applyRecord(record("r1", 2));
    release([record("r1", 1)]);
    await pending;
    expect(state.selectedRecord.value?.record_revision).toBe(2);
  });

  it("shows a retryable error and re-reads the requested Record", async () => {
    const state = setup();
    corpusReviewReads.records.mockRejectedValueOnce(new Error("Offline"));
    await state.reviewRecords.selectRecord(row("r1"));
    expect(state.reviewRecords.recordError.value).toBe("Offline");
    corpusReviewReads.records.mockResolvedValueOnce([record("r1")]);
    await state.reviewRecords.retryRecord();
    expect(state.selectedRecordId.value).toBe("r1");
    expect(state.reviewRecords.recordError.value).toBe("");
  });
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(graphqlClient, "clearGraphQLReadCache").mockImplementation(() => undefined);
    vi.spyOn(graphqlClient, "invalidateGraphQLReads").mockImplementation(() => undefined);
    corpusReviewReads.metadataFacets.mockResolvedValue({});
    corpusReviewReads.records.mockResolvedValue([]);
    corpusReviewReads.rows.mockResolvedValue([]);
    corpusReviewReads.texts.mockResolvedValue([]);
    corpusReviewReads.queuePage.mockResolvedValue(page([]));
  });

  it("loads the selected Record before starting the build-wide metadata facet scan", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1")]));
    corpusReviewReads.records.mockResolvedValue([record("r1")]);
    corpusReviewReads.metadataFacets.mockResolvedValue({ speaker: ["Derrida"] });

    await state.reviewRecords.refreshRecords(true);

    expect(corpusReviewReads.records).toHaveBeenCalledTimes(1);
    expect(corpusReviewReads.metadataFacets).toHaveBeenCalledTimes(1);
    expect(corpusReviewReads.records.mock.invocationCallOrder[0]).toBeLessThan(
      corpusReviewReads.metadataFacets.mock.invocationCallOrder[0],
    );
    expect(state.selectedRecord.value?.record_id).toBe("r1");
  });

  it("drops a stale cache entry and refetches when the row's revision has moved on", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1", 1)]));
    corpusReviewReads.records.mockResolvedValueOnce([record("r1", 1)]);

    await state.reviewRecords.refreshRecords(true);
    expect(state.selectedRecord.value?.record_revision).toBe(1);
    expect(corpusReviewReads.records).toHaveBeenCalledTimes(1);

    // The row now reports a newer revision (for example after a save elsewhere); selecting it
    // again must not reuse the stale cached copy.
    corpusReviewReads.records.mockResolvedValueOnce([record("r1", 2, { text: "Updated" })]);
    await state.reviewRecords.selectRecord(row("r1", 2));

    expect(corpusReviewReads.records).toHaveBeenCalledTimes(2);
    expect(state.selectedRecord.value?.record_revision).toBe(2);
    expect(state.selectedRecord.value?.text).toBe("Updated");
  });

  it("keeps only the latest selection when a slower one resolves after it", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1"), row("r2")]));
    await state.reviewRecords.refreshRecords(true);

    let resolveFirst: (records: unknown[]) => void = () => undefined;
    corpusReviewReads.records
      .mockImplementationOnce(() => new Promise((resolve) => (resolveFirst = resolve)))
      .mockResolvedValueOnce([record("r2")]);

    const first = state.reviewRecords.selectRecord(row("r1"));
    const second = state.reviewRecords.selectRecord(row("r2"));
    await second;
    resolveFirst([record("r1")]);
    await first;

    expect(state.selectedRecord.value?.record_id).toBe("r2");
  });

  it("advances to a valid filtered row when concurrent completion removes the selection", async () => {
    const state = setup();
    state.reviewQueue.value = "ready";
    corpusReviewReads.queuePage
      .mockResolvedValueOnce(page([row("r1"), row("r2")]))
      .mockResolvedValueOnce(page([row("r2")]));
    corpusReviewReads.records
      .mockResolvedValueOnce([record("r1")])
      .mockResolvedValueOnce([record("r2")]);

    await state.reviewRecords.refreshRecords(true);
    expect(state.selectedRecord.value?.record_id).toBe("r1");

    await state.reviewRecords.refreshRecords(false);
    expect(state.selectedRecord.value?.record_id).toBe("r2");
  });

  it("keeps an unsaved draft selected even if a concurrent update removes it from the filter", async () => {
    const state = setup();
    state.reviewQueue.value = "ready";
    corpusReviewReads.queuePage
      .mockResolvedValueOnce(page([row("r1"), row("r2")]))
      .mockResolvedValueOnce(page([row("r2")]));
    corpusReviewReads.records.mockResolvedValueOnce([record("r1")]);

    await state.reviewRecords.refreshRecords(true);
    state.setActiveDraft(true);
    state.selectedRecord.value = { ...state.selectedRecord.value, text: "Unsaved reviewer text" };

    await state.reviewRecords.refreshRecords(false);
    expect(state.selectedRecord.value?.record_id).toBe("r1");
    expect(state.selectedRecord.value?.text).toBe("Unsaved reviewer text");
  });

  it("backs up from an emptied last page after concurrent queue shrinkage", async () => {
    const state = setup();
    state.reviewQueue.value = "ready";
    state.recordOffset.value = 50;
    corpusReviewReads.queuePage
      .mockResolvedValueOnce(page([], { total: 1, offset: 50 }))
      .mockResolvedValueOnce(page([row("r1")], { total: 1, offset: 0 }));
    corpusReviewReads.records.mockResolvedValueOnce([record("r1")]);

    await state.reviewRecords.refreshRecords(false);

    expect(state.recordOffset.value).toBe(0);
    expect(state.selectedRecord.value?.record_id).toBe("r1");
    expect(corpusReviewReads.queuePage).toHaveBeenCalledTimes(2);
  });

  it("preserves an active draft across refreshRecords instead of re-reading the server", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1")]));
    corpusReviewReads.records.mockResolvedValueOnce([record("r1")]);
    await state.reviewRecords.refreshRecords(true);
    expect(corpusReviewReads.records).toHaveBeenCalledTimes(1);

    state.selectedRecord.value = { ...state.selectedRecord.value, text: "Local unsaved edit" };
    state.setActiveDraft(true);
    await state.reviewRecords.refreshRecords(false);

    expect(corpusReviewReads.records).toHaveBeenCalledTimes(1);
    expect(state.selectedRecord.value?.text).toBe("Local unsaved edit");
  });

  it("clears the previously-selected Record while a new selection loads, rather than leaving it stale", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1"), row("r2")]));
    corpusReviewReads.records.mockResolvedValueOnce([record("r1")]);
    await state.reviewRecords.refreshRecords(true);
    expect(state.selectedRecord.value?.record_id).toBe("r1");

    let resolveSecond: (records: unknown[]) => void = () => undefined;
    corpusReviewReads.records.mockImplementationOnce(
      () => new Promise((resolve) => (resolveSecond = resolve)),
    );
    const selecting = state.reviewRecords.selectRecord(row("r2"));

    expect(state.selectedRecord.value).toBeNull();
    expect(state.reviewRecords.loadingRecordId.value).toBe("r2");

    resolveSecond([record("r2")]);
    await selecting;

    expect(state.selectedRecord.value?.record_id).toBe("r2");
    expect(state.reviewRecords.loadingRecordId.value).toBe("");
  });

  it("refreshes the selected full Record when enrichment completes without a revision change", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1", 1)]));
    corpusReviewReads.records.mockResolvedValueOnce([record("r1", 1)]);
    await state.reviewRecords.refreshRecords(true);

    corpusReviewReads.records.mockResolvedValueOnce([
      record("r1", 1, {
        speaker: "Derrida",
        metadata_evidence: { speaker: { block_ids: ["b1"] } },
      }),
    ]);
    await state.reviewRecords.refreshRecord("r1");

    expect(corpusReviewReads.records).toHaveBeenCalledTimes(2);
    expect(state.selectedRecord.value?.record_revision).toBe(1);
    expect(state.selectedRecord.value?.speaker).toBe("Derrida");
    expect(state.selectedRecord.value?.metadata_evidence?.speaker?.block_ids).toEqual(["b1"]);
  });

  it("does not overwrite an active draft during a realtime full-record refresh", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1", 1)]));
    corpusReviewReads.records.mockResolvedValueOnce([record("r1", 1)]);
    await state.reviewRecords.refreshRecords(true);
    state.selectedRecord.value = { ...state.selectedRecord.value, text: "Local unsaved edit" };
    state.setActiveDraft(true);

    corpusReviewReads.records.mockResolvedValueOnce([record("r1", 2, { text: "Server update" })]);
    await state.reviewRecords.refreshRecord("r1");

    expect(state.selectedRecord.value?.text).toBe("Local unsaved edit");
  });

  it("does not reactivate an old Record while another selection is loading", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1", 1)]));
    corpusReviewReads.records.mockResolvedValueOnce([record("r1", 1)]);
    await state.reviewRecords.refreshRecords(true);

    let resolveR2: (records: unknown[]) => void = () => undefined;
    corpusReviewReads.records
      .mockImplementationOnce(() => new Promise((resolve) => (resolveR2 = resolve)))
      .mockResolvedValueOnce([record("r1", 1, { speaker: "Late refresh" })]);

    const selecting = state.reviewRecords.selectRecord(row("r2", 1));
    expect(state.selectedRecord.value).toBeNull();

    await state.reviewRecords.refreshRecord("r1");
    expect(state.selectedRecord.value).toBeNull();

    resolveR2([record("r2", 1)]);
    await selecting;
    expect(state.selectedRecord.value?.record_id).toBe("r2");
  });

  it("force-refreshes a same-revision Record on reset", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1", 1)]));
    corpusReviewReads.records
      .mockResolvedValueOnce([record("r1", 1, { speaker: null })])
      .mockResolvedValueOnce([record("r1", 1, { speaker: "Jacques Derrida" })]);

    await state.reviewRecords.refreshRecords(true);
    expect(state.selectedRecord.value?.speaker).toBeNull();

    await state.reviewRecords.refreshRecords(true, "r1");

    expect(corpusReviewReads.records).toHaveBeenCalledTimes(2);
    expect(state.selectedRecord.value?.speaker).toBe("Jacques Derrida");
  });

  it("invalidates read projections before a mutation-triggered queue reset", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1")]));

    await state.reviewRecords.refreshRecords(true);

    expect(graphqlClient.invalidateGraphQLReads).toHaveBeenCalledWith({ buildId: "b1" });
    expect(corpusReviewReads.queuePage).toHaveBeenCalledTimes(1);
  });

  it("invalidates read projections when applying an authoritative record", () => {
    const state = setup();
    const updated = record("r1", 2, { review_disposition: "rejected" });

    state.reviewRecords.applyRecord(updated);

    expect(graphqlClient.invalidateGraphQLReads).toHaveBeenCalledWith({
      buildId: "b1",
      recordIds: ["r1"],
    });
  });

  it("uses live cursors sequentially, actual offsets, and drops cursors on filter changes", async () => {
    const state = setup();
    corpusReviewReads.queuePage
      .mockResolvedValueOnce(page([row("r1")], { nextCursor: "next", hasNextPage: true }))
      .mockResolvedValueOnce(page([row("r2")], { offset: 49, previousCursor: "back" }))
      .mockResolvedValueOnce(page([row("r1")], { offset: 0 }));
    await state.reviewRecords.refreshRecords();
    await state.reviewRecords.movePage("forward");
    expect(corpusReviewReads.queuePage.mock.calls[1][5]).toEqual({
      cursor: "next",
      direction: "forward",
    });
    expect(state.recordOffset.value).toBe(49);
    state.reviewQueue.value = "ready";
    await state.reviewRecords.movePage("backward");
    expect(corpusReviewReads.queuePage.mock.calls[2][1]).toBe(0);
    expect(corpusReviewReads.queuePage.mock.calls[2][5]).toEqual({});
  });

  it("recovers a stale cursor once via offset and surfaces a failed recovery", async () => {
    const state = setup();
    const stale = new graphqlClient.GraphQLRequestError("CorpusReviewQueue", [
      { message: "Queue changed", extensions: { code: "STALE_QUEUE_CURSOR" } },
    ]);
    corpusReviewReads.queuePage
      .mockResolvedValueOnce(page([row("r1")], { nextCursor: "next", hasNextPage: true }))
      .mockRejectedValueOnce(stale)
      .mockRejectedValueOnce(stale);
    await state.reviewRecords.refreshRecords();
    await state.reviewRecords.movePage("forward");
    expect(corpusReviewReads.queuePage).toHaveBeenCalledTimes(3);
    expect(corpusReviewReads.queuePage.mock.calls[2][5]).toEqual({});
    expect(state.onError).toHaveBeenCalledWith("Queue changed");
  });

  it("does not retry a cursor with an invalid context", async () => {
    const state = setup();
    corpusReviewReads.queuePage
      .mockResolvedValueOnce(page([row("r1")], { nextCursor: "next", hasNextPage: true }))
      .mockRejectedValueOnce(
        new graphqlClient.GraphQLRequestError("CorpusReviewQueue", [
          { message: "Wrong reviewer", extensions: { code: "BAD_REQUEST" } },
        ]),
      );
    await state.reviewRecords.refreshRecords();
    await state.reviewRecords.movePage("forward");
    expect(corpusReviewReads.queuePage).toHaveBeenCalledTimes(2);
    expect(state.onError).toHaveBeenCalledWith("Wrong reviewer");
  });

  it("clears build-local caches/cursors on a topology-generation change", async () => {
    const state = setup();
    corpusReviewReads.queuePage
      .mockResolvedValueOnce(page([row("r1")], { nextCursor: "before", topologyGeneration: 1 }))
      .mockResolvedValueOnce(page([row("r1")], { nextCursor: "after", topologyGeneration: 2 }));
    corpusReviewReads.records
      .mockResolvedValueOnce([record("r1", 1, { text: "Before topology edit" })])
      .mockResolvedValueOnce([record("r1", 1, { text: "After topology edit" })]);
    await state.reviewRecords.refreshRecords();
    await state.reviewRecords.refreshRecords();
    expect(corpusReviewReads.records).toHaveBeenCalledTimes(2);
    expect(state.selectedRecord.value?.text).toBe("After topology edit");
    expect(state.reviewRecords.nextCursor.value).toBe("after");
    expect(state.reviewRecords.topologyGeneration.value).toBe(2);
  });

  it("discards reviewer-bound pending responses and cursor state after a reviewer change", async () => {
    const reviewerKey = ref("reviewer-1");
    const state = setup({ reviewerKey });
    let release!: (value: unknown) => void;
    corpusReviewReads.queuePage
      .mockReturnValueOnce(new Promise((resolve) => (release = resolve)))
      .mockResolvedValueOnce(page([], { nextCursor: null }));
    const loading = state.reviewRecords.refreshRecords();
    reviewerKey.value = "reviewer-2";
    release(page([row("sealed-for-first-reviewer")], { nextCursor: "old" }));
    await loading;
    await vi.waitFor(() => expect(state.reviewRecords.recordsLoading.value).toBe(false));
    expect(state.reviewRecords.queueRows.value).toEqual([]);
    expect(state.reviewRecords.nextCursor.value).toBeNull();
    expect(state.selectedRecord.value).toBeNull();
  });

  it("coalesces row hints and reconciles removal/backfill/counts rather than patching membership", async () => {
    const state = setup();
    state.reviewQueue.value = "ready";
    corpusReviewReads.queuePage.mockResolvedValueOnce(page([row("r1"), row("r2")]));
    corpusReviewReads.records.mockImplementation(async (_build, ids) =>
      ids.map((id: string) => record(id)),
    );
    await state.reviewRecords.refreshRecords();
    corpusReviewReads.queuePage.mockResolvedValueOnce(
      page([row("r2"), row("r3")], { total: 4, counts: { all: 5, ready: 4 } }),
    );
    await Promise.all([
      state.reviewRecords.refreshRows(["r1"]),
      state.reviewRecords.refreshRows(["r2"]),
    ]);
    expect(corpusReviewReads.queuePage).toHaveBeenCalledTimes(2);
    expect(corpusReviewReads.rows).not.toHaveBeenCalled();
    expect(state.reviewRecords.queueRows.value.map((item) => item.record_id)).toEqual(["r2", "r3"]);
    expect(state.reviewRecords.recordTotal.value).toBe(4);
    expect(state.selectedRecordId.value).toBe("r2");
    expect(corpusReviewReads.metadataFacets).toHaveBeenCalledTimes(2);
  });

  it("ignores a stale page already in flight when a record hint schedules reconciliation", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValueOnce(page([row("r1")]));
    corpusReviewReads.records.mockResolvedValueOnce([record("r1")]);
    await state.reviewRecords.refreshRecords();
    let release!: (value: unknown) => void;
    corpusReviewReads.queuePage
      .mockReturnValueOnce(new Promise((resolve) => (release = resolve)))
      .mockResolvedValueOnce(page([row("r2")]));
    const oldPage = state.reviewRecords.refreshRecords();
    const reconcile = state.reviewRecords.refreshRows(["r1"]);
    release(page([row("r1")], { total: 99 }));
    await Promise.all([oldPage, reconcile]);
    expect(state.reviewRecords.queueRows.value.map((item) => item.record_id)).toEqual(["r2"]);
    expect(state.reviewRecords.recordTotal.value).toBe(1);
  });

  it("detects enrichment via operational state_version without changing RecordRevision", async () => {
    const state = setup();
    corpusReviewReads.queuePage
      .mockResolvedValueOnce(page([row("r1", 1, { state_version: 1 })]))
      .mockResolvedValueOnce(page([row("r1", 1, { state_version: 2 })]));
    corpusReviewReads.records
      .mockResolvedValueOnce([record("r1", 1, { speaker: null })])
      .mockResolvedValueOnce([record("r1", 1, { speaker: "Derrida" })]);
    await state.reviewRecords.refreshRecords();
    await state.reviewRecords.refreshRecords();
    expect(state.selectedRecord.value?.speaker).toBe("Derrida");
    expect(corpusReviewReads.records).toHaveBeenCalledTimes(2);
  });

  it("preserves a draft and unrelated cached Records during a targeted membership refresh", async () => {
    const state = setup();
    await state.reviewRecords.selectRecord(record("r9"));
    corpusReviewReads.queuePage.mockResolvedValueOnce(page([row("r1")]));
    corpusReviewReads.records.mockResolvedValueOnce([record("r1")]);
    await state.reviewRecords.refreshRecords();
    state.setActiveDraft(true);
    state.selectedRecord.value = { ...state.selectedRecord.value, text: "Local draft" };
    corpusReviewReads.queuePage.mockResolvedValueOnce(page([row("r2")]));
    await state.reviewRecords.refreshRows(["r1"]);
    expect(state.selectedRecord.value?.text).toBe("Local draft");
    expect(state.selectedRecordId.value).toBe("r1");
    state.setActiveDraft(false);
    await state.reviewRecords.selectRecord(row("r9"));
    expect(state.selectedRecord.value?.record_id).toBe("r9");
    expect(corpusReviewReads.records).toHaveBeenCalledTimes(1);
  });
});
