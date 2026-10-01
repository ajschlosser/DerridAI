/* Copyright 2026 Aaron John Schlosser, PhD. */
import { ref } from "vue";
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
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(graphqlClient, "clearGraphQLReadCache").mockImplementation(() => undefined);
    corpusReviewReads.metadataFacets.mockResolvedValue({});
    corpusReviewReads.records.mockResolvedValue([]);
    corpusReviewReads.rows.mockResolvedValue([]);
    corpusReviewReads.texts.mockResolvedValue([]);
  });

  it("loads the selected Record before starting the build-wide metadata facet scan", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1")]));
    corpusReviewReads.records.mockResolvedValue([record("r1")]);
    corpusReviewReads.metadataFacets.mockResolvedValue({ speaker: ["Author"] });

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
        speaker: "Author",
        metadata_evidence: { speaker: { block_ids: ["b1"] } },
      }),
    ]);
    await state.reviewRecords.refreshRecord("r1");

    expect(corpusReviewReads.records).toHaveBeenCalledTimes(2);
    expect(state.selectedRecord.value?.record_revision).toBe(1);
    expect(state.selectedRecord.value?.speaker).toBe("Author");
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
      .mockResolvedValueOnce([record("r1", 1, { speaker: "Jane Author" })]);

    await state.reviewRecords.refreshRecords(true);
    expect(state.selectedRecord.value?.speaker).toBeNull();

    await state.reviewRecords.refreshRecords(true, "r1");

    expect(corpusReviewReads.records).toHaveBeenCalledTimes(2);
    expect(state.selectedRecord.value?.speaker).toBe("Jane Author");
  });

  it("invalidates read projections before a mutation-triggered queue reset", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1")]));

    await state.reviewRecords.refreshRecords(true);

    expect(graphqlClient.clearGraphQLReadCache).toHaveBeenCalledTimes(1);
    expect(corpusReviewReads.queuePage).toHaveBeenCalledTimes(1);
  });

  it("invalidates read projections when applying an authoritative record", () => {
    const state = setup();
    const updated = record("r1", 2, { review_disposition: "rejected" });

    state.reviewRecords.applyRecord(updated);

    expect(graphqlClient.clearGraphQLReadCache).toHaveBeenCalledTimes(1);
  });
});
