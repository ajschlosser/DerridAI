/* Copyright 2026 Aaron John Schlosser, PhD. */
import { ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
    corpusReviewReads.metadataFacets.mockResolvedValue({});
    corpusReviewReads.records.mockResolvedValue([]);
    corpusReviewReads.rows.mockResolvedValue([]);
    corpusReviewReads.texts.mockResolvedValue([]);
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
});
