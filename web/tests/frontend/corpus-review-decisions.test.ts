/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

const corpusBuilderApi = vi.hoisted(() => ({
  disposition: vi.fn(),
  reviewDecision: vi.fn(),
  bulkDisposition: vi.fn(),
  undoReview: vi.fn(),
  redoReview: vi.fn(),
}));

vi.mock("../../src/api/corpus", async () => {
  const actual =
    await vi.importActual<typeof import("../../src/api/corpus")>("../../src/api/corpus");
  return { ...actual, corpusBuilderApi };
});

import { useCorpusReviewDecisions } from "../../src/features/corpus-builder/composables/useCorpusReviewDecisions";

function record(overrides: Record<string, unknown> = {}) {
  return {
    record_id: "r1",
    record_revision: 1,
    review_disposition: "pending",
    needs_review: true,
    accepted: false,
    rejected: false,
    ...overrides,
  } as any;
}

function setup() {
  const currentBuild = ref<any | null>({
    build_id: "b1",
    review_queue_counts: {},
  });
  const selectedRecord = ref<any | null>(record());
  const selectedRecordId = ref("r1");
  const records = ref<any[]>([selectedRecord.value]);
  const recordTotal = ref(1);
  const reviewQueue = ref<any>("all");
  const recordQuery = ref("");
  const selectedReviewIds = ref(new Set<string>());
  const justProcessedRecordId = ref("");
  const bulkActionFeedback = ref("");
  const busy = ref("");
  const focusView = ref(true);
  const reviewInspectorTab = ref<"metadata" | "evidence" | "source">("metadata");
  const reviewLocked = computed(() => false);
  const selectedMetadataBlocked = computed(() => false);
  const readyCount = computed(() => 1);
  const issueCount = computed(() => 0);
  const captureReviewViewport = vi.fn(() => ({
    windowY: 0,
    queueTop: 0,
    recordTop: 0,
    inspectorTop: 0,
  }));
  const restoreReviewViewport = vi.fn(async () => undefined);
  const queued: Array<{
    request: (rebase: boolean) => Promise<unknown>;
    onFailure?: () => void | Promise<void>;
  }> = [];
  const queueRecordRequest = vi.fn(
    (
      _recordId: string | readonly string[],
      _fields: string[],
      request: (rebase: boolean) => Promise<unknown>,
      onFailure?: () => void | Promise<void>,
    ) => {
      queued.push({ request, onFailure });
    },
  );
  const applyAuthoritativeRecord = vi.fn((row: any, build?: any) => {
    selectedRecord.value = row;
    if (build) currentBuild.value = build;
  });
  const syncBuildInRail = vi.fn();
  const selectRecord = vi.fn((row: any) => {
    selectedRecord.value = row;
    selectedRecordId.value = row.record_id;
  });
  const advanceFrom = vi.fn(async () => undefined);
  const refreshBuild = vi.fn(async () => undefined);
  const refreshRecords = vi.fn(async () => undefined);
  const focusFirstMetadataBlocker = vi.fn();
  const setMessage = vi.fn();

  const decisions = useCorpusReviewDecisions({
    currentBuild,
    selectedRecord,
    selectedRecordId,
    records,
    recordTotal,
    reviewQueue,
    recordQuery,
    selectedReviewIds,
    justProcessedRecordId,
    bulkActionFeedback,
    busy,
    focusView,
    reviewInspectorTab,
    reviewLocked,
    selectedMetadataBlocked,
    readyCount,
    issueCount,
    captureReviewViewport,
    restoreReviewViewport,
    queueRecordRequest,
    applyAuthoritativeRecord,
    syncBuildInRail,
    selectRecord,
    advanceFrom,
    refreshBuild,
    refreshRecords,
    focusFirstMetadataBlocker,
    setMessage,
    t: (key) => key,
    tf: (key) => key,
  });

  return {
    decisions,
    currentBuild,
    selectedRecord,
    selectedRecordId,
    records,
    recordTotal,
    reviewQueue,
    focusView,
    justProcessedRecordId,
    reviewInspectorTab,
    queued,
    applyAuthoritativeRecord,
    syncBuildInRail,
    selectRecord,
    advanceFrom,
    setMessage,
    focusFirstMetadataBlocker,
  };
}

describe("Corpus Builder review decisions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("applies a pending/rejected disposition optimistically before persistence settles", async () => {
    const state = setup();
    corpusBuilderApi.disposition.mockResolvedValue(record({ record_revision: 3 }));

    await state.decisions.setDisposition("pending");

    expect(state.selectedRecord.value?.review_disposition).toBe("pending");
    expect(state.selectedRecord.value?.record_revision).toBe(2);
    expect(state.queued).toHaveLength(1);

    await state.queued[0].request(false);
    expect(corpusBuilderApi.disposition).toHaveBeenCalledWith("b1", "r1", "pending", "", 1);
    expect(state.applyAuthoritativeRecord).toHaveBeenCalled();
  });

  it("routes an acceptance blocker to metadata review without losing the authoritative record", async () => {
    const state = setup();
    const authoritative = record({
      record_revision: 2,
      metadata_review_fields: ["speaker"],
    });
    corpusBuilderApi.reviewDecision.mockResolvedValue({
      blocked: true,
      blocker: "metadata",
      blocking_fields: ["speaker"],
      record: authoritative,
      build: { build_id: "b1", review_queue_counts: {} },
    });

    await state.decisions.setDisposition("accepted");
    expect(state.justProcessedRecordId.value).toBe("r1");
    expect(state.queued).toHaveLength(1);

    await state.queued[0].request(false);

    expect(state.selectedRecord.value).toEqual(authoritative);
    expect(state.reviewInspectorTab.value).toBe("metadata");
    expect(state.focusFirstMetadataBlocker).toHaveBeenCalled();
    expect(state.setMessage).toHaveBeenCalledWith("pdf_corpus.accept_blocked_metadata");
  });

  it("routes source blockers to the source review queue", async () => {
    const state = setup();
    corpusBuilderApi.reviewDecision.mockResolvedValue({
      blocked: true,
      blocker: "source_problem",
      blocking_fields: [],
      record: record({ record_revision: 2 }),
      build: { build_id: "b1", review_queue_counts: {} },
    });

    await state.decisions.setDisposition("accepted");
    await state.queued[0].request(false);

    expect(state.reviewInspectorTab.value).toBe("source");
    expect(state.reviewQueue.value).toBe("source");
    expect(state.setMessage).toHaveBeenCalledWith("pdf_corpus.accept_blocked_source", "error");
  });

  it("advances to the next local record immediately after Accept & next", async () => {
    const state = setup();
    const second = record({ record_id: "r2", record_revision: 1 });
    state.records.value = [state.selectedRecord.value, second];
    state.recordTotal.value = 2;
    corpusBuilderApi.reviewDecision.mockResolvedValue({
      blocked: false,
      record: record({ record_revision: 2, accepted: true, review_disposition: "accepted" }),
      build: { build_id: "b1", review_queue_counts: {} },
      next_record: second,
    });

    await state.decisions.setDisposition("accepted");

    expect(state.selectedRecord.value?.record_id).toBe("r2");
    expect(state.selectRecord).toHaveBeenCalledWith(second);
    expect(state.queued).toHaveLength(1);

    await state.queued[0].request(false);

    expect(corpusBuilderApi.reviewDecision).toHaveBeenCalledWith(
      "b1",
      "r1",
      "accepted",
      "",
      1,
      "all",
    );
    expect(state.selectedRecord.value?.record_id).toBe("r2");
    // There was somewhere to go, so Focus View stays open.
    expect(state.focusView.value).toBe(true);
  });

  it("falls back to queue navigation when the server has no explicit next record", async () => {
    const state = setup();
    corpusBuilderApi.reviewDecision.mockResolvedValue({
      blocked: false,
      record: record({ record_revision: 2, accepted: true, review_disposition: "accepted" }),
      build: { build_id: "b1", review_queue_counts: {} },
    });

    await state.decisions.setDisposition("accepted");
    await state.queued[0].request(false);

    expect(state.advanceFrom).toHaveBeenCalledWith("r1");
  });

  it("closes Focus View when the accepted record was the last one in the queue", async () => {
    const state = setup();
    corpusBuilderApi.reviewDecision.mockResolvedValue({
      blocked: false,
      record: record({ record_revision: 2, accepted: true, review_disposition: "accepted" }),
      build: { build_id: "b1", review_queue_counts: {} },
    });
    expect(state.focusView.value).toBe(true);

    await state.decisions.setDisposition("accepted");
    await state.queued[0].request(false);

    expect(state.focusView.value).toBe(false);
  });
});
