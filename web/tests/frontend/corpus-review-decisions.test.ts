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

import { computed, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

const corpusBuilderApi = vi.hoisted(() => ({
  disposition: vi.fn(),
  reviewDecision: vi.fn(),
  reviewStatus: vi.fn(),
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

function setup(beforeDecision?: () => Promise<boolean>) {
  const getSelectionVersion = vi.fn(() => 0);
  const currentBuild = ref<any | null>({
    build_id: "b1",
    review_queue_counts: {},
  });
  const selectedRecord = ref<any | null>(record());
  const selectedRecordId = ref("r1");
  const queueRows = ref<any[]>([selectedRecord.value]);
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
  const recordOffset = ref(0);
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
  const reconcileRecords = vi.fn(async () => undefined);
  const focusSourceBlocker = vi.fn(async () => undefined);
  const focusFirstMetadataBlocker = vi.fn();
  const setMessage = vi.fn();

  const decisions = useCorpusReviewDecisions({
    currentBuild,
    selectedRecord,
    selectedRecordId,
    queueRows,
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
    recordOffset,
    beforeDecision,
    getSelectionVersion,
    refreshBuild,
    refreshRecords,
    reconcileRecords,
    focusSourceBlocker,
    focusFirstMetadataBlocker,
    setMessage,
    t: (key) => key,
    tf: (key, values) =>
      key === "pdf_corpus.accept_blocked_metadata"
        ? `Confirm the required metadata before accepting this record: ${values.fields}.`
        : key,
  });

  return {
    restoreReviewViewport,
    getSelectionVersion,
    decisions,
    currentBuild,
    selectedRecord,
    selectedRecordId,
    queueRows,
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
    refreshBuild,
    reconcileRecords,
    focusSourceBlocker,
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
    expect(state.setMessage).toHaveBeenCalledWith(
      "Confirm the required metadata before accepting this record: record.speaker.",
      "error",
    );
  });

  it("interpolates metadata blockers even if the reviewer navigates away before the save returns", async () => {
    const state = setup();
    corpusBuilderApi.reviewDecision.mockResolvedValue({
      blocked: true,
      blocker: "metadata",
      blocking_fields: ["speaker", "position_holder"],
      record: record({ record_revision: 2 }),
      build: { build_id: "b1", review_queue_counts: {} },
    });

    await state.decisions.setDisposition("accepted");
    state.getSelectionVersion.mockReturnValue(1);
    await state.queued[0].request(false);

    expect(state.setMessage).toHaveBeenCalledWith(
      "Confirm the required metadata before accepting this record: record.speaker, record.position_holder.",
      "error",
    );
    expect(state.setMessage).not.toHaveBeenCalledWith(
      expect.stringContaining("{fields}"),
      expect.anything(),
    );
  });

  it("uses generic metadata blocker copy when the server returns no field list", async () => {
    const state = setup();
    corpusBuilderApi.reviewDecision.mockResolvedValue({
      blocked: true,
      blocker: "metadata",
      blocking_fields: [],
      record: record({ record_revision: 2 }),
      build: { build_id: "b1", review_queue_counts: {} },
    });

    await state.decisions.setDisposition("accepted");
    await state.queued[0].request(false);

    expect(state.setMessage).toHaveBeenCalledWith(
      "pdf_corpus.accept_blocked_metadata_generic",
      "error",
    );
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
    expect(state.focusSourceBlocker).toHaveBeenCalledTimes(1);
    expect(state.setMessage).toHaveBeenCalledWith("pdf_corpus.accept_blocked_source", "error");
  });

  it("advances to the next local record immediately after Accept & next", async () => {
    const state = setup();
    const second = record({ record_id: "r2", record_revision: 1 });
    state.queueRows.value = [state.selectedRecord.value, second];
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

  it("advances Reject & next and does not steal a later manual selection", async () => {
    const state = setup();
    const second = record({ record_id: "r2" });
    const third = record({ record_id: "r3" });
    state.queueRows.value = [state.selectedRecord.value, second, third];
    state.recordTotal.value = 3;
    await state.decisions.rejectRecord();
    expect(state.queueRows.value[0].review_disposition).toBe("rejected");
    expect(state.selectedRecordId.value).toBe("r2");
    state.selectedRecordId.value = "r3";
    state.selectedRecord.value = third;
    corpusBuilderApi.reviewDecision.mockResolvedValue({
      blocked: false,
      record: record({ rejected: true, review_disposition: "rejected" }),
      build: { build_id: "b1" },
      next_record: second,
    });
    state.restoreReviewViewport.mockClear();
    await state.queued[0].request(false);
    expect(state.selectedRecordId.value).toBe("r3");
    expect(state.restoreReviewViewport).not.toHaveBeenCalled();
    expect(corpusBuilderApi.reviewDecision).toHaveBeenCalledWith(
      "b1",
      "r1",
      "rejected",
      "",
      1,
      "all",
    );
  });

  it("does not advance after manual navigation returns to the same Record ID", async () => {
    const state = setup();
    state.queueRows.value.push(record({ record_id: "r2" }));
    state.recordTotal.value = 2;
    await state.decisions.rejectRecord();
    state.selectedRecordId.value = "r1";
    state.selectedRecord.value = state.queueRows.value[0];
    state.getSelectionVersion.mockReturnValue(2);
    state.selectRecord.mockClear();
    corpusBuilderApi.reviewDecision.mockResolvedValue({
      blocked: false,
      record: record({ rejected: true, review_disposition: "rejected" }),
      build: { build_id: "b1" },
      next_record: record({ record_id: "r2" }),
    });
    await state.queued[0].request(false);
    expect(state.selectedRecordId.value).toBe("r1");
    expect(state.selectRecord).not.toHaveBeenCalled();
  });

  it("keeps an accepted decision when the response times out after the server committed it", async () => {
    const state = setup();
    corpusBuilderApi.reviewDecision.mockRejectedValue(
      new Error("Network error · timed out after 30s"),
    );
    corpusBuilderApi.reviewStatus.mockResolvedValue({
      record_id: "r1",
      record_revision: 2,
      review_disposition: "accepted",
      accepted: true,
      rejected: false,
      needs_review: false,
    });

    await state.decisions.attemptAccept();
    expect(state.selectedRecord.value?.review_disposition).toBe("accepted");

    await expect(state.queued[0].request(false)).resolves.toBeUndefined();

    expect(corpusBuilderApi.reviewStatus).toHaveBeenCalledWith("b1", "r1");
    expect(state.refreshBuild).toHaveBeenCalled();
    expect(state.reconcileRecords).toHaveBeenCalledWith(["r1"]);
    expect(state.selectedRecord.value?.review_disposition).toBe("accepted");
  });

  it("treats a timeout as a failure when authoritative state did not advance", async () => {
    const state = setup();
    const timeout = new Error("Network error · timed out after 30s");
    corpusBuilderApi.reviewDecision.mockRejectedValue(timeout);
    corpusBuilderApi.reviewStatus.mockResolvedValue({
      record_id: "r1",
      record_revision: 1,
      review_disposition: "pending",
      accepted: false,
      rejected: false,
      needs_review: true,
    });

    await state.decisions.attemptAccept();

    await expect(state.queued[0].request(false)).rejects.toBe(timeout);
    expect(state.refreshBuild).not.toHaveBeenCalled();
    expect(state.reconcileRecords).not.toHaveBeenCalled();
  });

  it("rolls back only the failed decision without replacing a later selection", async () => {
    const state = setup();
    state.queueRows.value.push(record({ record_id: "r2" }), record({ record_id: "r3" }));
    state.recordTotal.value = 3;
    await state.decisions.attemptAccept();
    state.selectedRecordId.value = "r3";
    state.selectedRecord.value = state.queueRows.value[2];
    state.queueRows.value[1] = record({ record_id: "r2", record_revision: 9 });
    await state.queued[0].onFailure?.();
    expect(state.selectedRecordId.value).toBe("r3");
    expect(state.queueRows.value[1].record_revision).toBe(9);
    expect(state.queueRows.value[0].review_disposition).toBe("pending");
  });

  it("does not decide or advance while draft navigation is declined", async () => {
    const state = setup(vi.fn().mockResolvedValue(false));
    await state.decisions.rejectRecord();
    expect(state.queued).toHaveLength(0);
    expect(state.selectedRecordId.value).toBe("r1");
    expect(state.selectedRecord.value?.review_disposition).toBe("pending");
  });

  it("uses filtered queue backfill at the page boundary instead of moving backward", async () => {
    const state = setup();
    state.queueRows.value = [record({ record_id: "r0" }), state.selectedRecord.value];
    state.recordTotal.value = 3;
    state.reviewQueue.value = "ready";
    corpusBuilderApi.reviewDecision.mockResolvedValue({
      blocked: false,
      record: record({ rejected: true, review_disposition: "rejected" }),
      build: { build_id: "b1" },
      next_record: record({ record_id: "r2" }),
    });
    await state.decisions.rejectRecord();
    expect(state.selectedRecordId.value).toBe("r1");
    await state.queued[0].request(false);
    expect(state.advanceFrom).toHaveBeenCalledWith("r1", 1);
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
