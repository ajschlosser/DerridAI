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

  it("refreshes an open same-revision Record after enrichment", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1", 1)]));
    corpusReviewReads.records
      .mockResolvedValueOnce([
        record("r1", 1, {
          speaker: null,
          metadata_evidence: {},
          metadata_field_status: {},
        }),
      ])
      .mockResolvedValueOnce([
        record("r1", 1, {
          speaker: "Jacques Derrida",
          metadata_evidence: {
            speaker: {
              block_ids: ["b1"],
              confidence: null,
              reason: "Suggested after enrichment.",
            },
          },
          metadata_field_status: {
            speaker: {
              status: "unresolved",
              method: "llm",
              proposed_value: "Jacques Derrida",
              verification_status: "pending_review",
            },
          },
        }),
      ]);
    corpusReviewReads.rows.mockResolvedValue([
      row("r1", 1, { metadata_llm_processed: true, needs_review: true }),
    ]);

    await state.reviewRecords.refreshRecords(true);
    expect(state.selectedRecord.value?.speaker).toBeNull();

    // Backend enrichment persists reviewer-facing suggestions but leaves the
    // documentary Record revision unchanged. The normal realtime row invalidation
    // must refresh the full open Record without navigation or a browser reload.
    await state.reviewRecords.refreshRows(["r1"]);

    expect(corpusReviewReads.records).toHaveBeenCalledTimes(2);
    expect(state.selectedRecord.value?.record_revision).toBe(1);
    expect(state.selectedRecord.value?.speaker).toBe("Jacques Derrida");
    const speakerEvidence = state.selectedRecord.value?.metadata_evidence?.speaker;
    expect(speakerEvidence?.block_ids).toEqual(["b1"]);
  });

  it("force-refreshes a same-revision Record on reset", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1", 1)]));
    corpusReviewReads.records
      .mockResolvedValueOnce([record("r1", 1, { speaker: null })])
      .mockResolvedValueOnce([record("r1", 1, { speaker: "Jacques Derrida" })]);

    await state.reviewRecords.refreshRecords(true);
    expect(state.selectedRecord.value?.speaker).toBeNull();

    // Build polling uses reset refreshes when metadata_enriched_count advances.
    // Same-revision cached projections must not suppress newly persisted metadata.
    await state.reviewRecords.refreshRecords(true, "r1");

    expect(corpusReviewReads.records).toHaveBeenCalledTimes(2);
    expect(state.selectedRecord.value?.speaker).toBe("Jacques Derrida");
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

  it("does not let an old-Record event supersede a selection in flight", async () => {
    const state = setup();
    corpusReviewReads.queuePage.mockResolvedValue(page([row("r1"), row("r2")]));
    corpusReviewReads.records.mockResolvedValueOnce([record("r1")]);
    corpusReviewReads.rows.mockResolvedValueOnce([row("r1", 1, { metadata_llm_processed: true })]);

    await state.reviewRecords.refreshRecords(true);
    expect(state.selectedRecord.value?.record_id).toBe("r1");

    let resolveR2: (records: unknown[]) => void = () => undefined;
    corpusReviewReads.records.mockImplementationOnce(
      () => new Promise((resolve) => (resolveR2 = resolve)),
    );
    const selecting = state.reviewRecords.selectRecord(row("r2"));

    expect(state.selectedRecord.value).toBeNull();
    await state.reviewRecords.refreshRows(["r1"]);
    expect(corpusReviewReads.records).toHaveBeenCalledTimes(2);

    resolveR2([record("r2")]);
    await selecting;
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
