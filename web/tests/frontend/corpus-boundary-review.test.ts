/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

const corpusBuilderApi = vi.hoisted(() => ({
  merge: vi.fn(),
  split: vi.fn(),
  sliceRecord: vi.fn(),
  adjudicateBoundary: vi.fn(),
}));

vi.mock("../../src/api/corpus", async () => {
  const actual =
    await vi.importActual<typeof import("../../src/api/corpus")>("../../src/api/corpus");
  return { ...actual, corpusBuilderApi };
});

import { useCorpusBoundaryReview } from "../../src/features/corpus-builder/composables/useCorpusBoundaryReview";

function record(id: string, text: string, index: number) {
  return {
    record_id: id,
    record_revision: 1,
    text,
    text_length: text.length,
    topology_index: index,
    topology_count: 2,
    source_block_ids: [`block-${index + 1}`],
    source_unit_ids: [`block-${index + 1}`],
    source_spans: [{ block_id: `block-${index + 1}`, page: index + 1 }],
    review_disposition: "pending",
    accepted: false,
    rejected: false,
    needs_review: true,
  } as any;
}

function setup() {
  const records = ref<any[]>([record("r1", "First", 0), record("r2", "Second", 1)]);
  const currentBuild = ref<any | null>({ build_id: "b1" });
  const selectedRecord = ref<any | null>(records.value[0]);
  const selectedRecordId = ref("r1");
  const recordTotal = ref(2);
  const recordOffset = ref(0);
  const selectedRecordIndex = computed(() =>
    records.value.findIndex((item) => item.record_id === selectedRecordId.value),
  );
  const visibleBlocks = computed<any[]>(() => [
    { block_id: "block-1", text: "First" },
    { block_id: "block-2", text: "Second" },
  ]);
  const busy = ref("");
  const structuralReviewLocked = computed(() => false);
  const editingText = ref(false);
  const metadataEditorDirty = ref(false);
  const llmActionProviderId = ref("local");
  const llmActionModel = ref("qwen");
  const selectedProviderId = ref("local");
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
    ) => queued.push({ request, onFailure }),
  );
  const restoreReviewViewport = vi.fn(async () => undefined);
  const refreshBuild = vi.fn(async () => undefined);
  const refreshRecords = vi.fn(async () => undefined);
  const setMessage = vi.fn();

  const review = useCorpusBoundaryReview({
    currentBuild,
    selectedRecord,
    selectedRecordId,
    records,
    recordTotal,
    recordOffset,
    selectedRecordIndex,
    visibleBlocks,
    busy,
    structuralReviewLocked,
    editingText,
    metadataEditorDirty,
    llmActionProviderId,
    llmActionModel,
    selectedProviderId,
    directProfilePayloadWithModel: (profileId, model) => ({
      provider_profile_id: profileId,
      model,
    }),
    captureReviewViewport: () => ({
      windowY: 0,
      queueTop: 0,
      recordTop: 0,
      inspectorTop: 0,
    }),
    restoreReviewViewport,
    queueRecordRequest,
    refreshBuild,
    refreshRecords,
    setMessage,
    t: (key, fallback) => fallback || key,
    tf: (key) => key,
  });

  return {
    review,
    records,
    recordTotal,
    selectedRecord,
    selectedRecordId,
    editingText,
    metadataEditorDirty,
    queued,
    refreshBuild,
    refreshRecords,
  };
}

describe("Corpus Builder boundary review", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("derives neighbor availability from topology identity", () => {
    const state = setup();

    expect(state.review.canMergePrevious.value).toBe(false);
    expect(state.review.canMergeNext.value).toBe(true);
    expect(state.review.mergeUnavailable("previous")).toBe("pdf_corpus.reason.no_previous");

    state.selectedRecord.value = state.records.value[1];
    state.selectedRecordId.value = "r2";
    expect(state.review.canMergePrevious.value).toBe(true);
    expect(state.review.canMergeNext.value).toBe(false);
  });

  it("blocks slicing while text or metadata edits are active", () => {
    const state = setup();

    state.editingText.value = true;
    expect(state.review.sliceUnavailable()).toBe("pdf_corpus.reason.finish_text_edit");

    state.editingText.value = false;
    state.metadataEditorDirty.value = true;
    expect(state.review.sliceUnavailable()).toBe("pdf_corpus.reason.finish_metadata_edit");
  });

  it("merges records optimistically before the persistence request resolves", async () => {
    const state = setup();
    corpusBuilderApi.merge.mockResolvedValue(record("r1", "First\n\nSecond", 0));

    await state.review.merge("next");

    expect(state.records.value).toHaveLength(1);
    expect(state.recordTotal.value).toBe(1);
    expect(state.selectedRecord.value?.text).toBe("First\n\nSecond");
    expect(state.queued).toHaveLength(1);

    await state.queued[0].request(false);
    expect(corpusBuilderApi.merge).toHaveBeenCalledWith("b1", "r1", "next", 1);
    expect(state.refreshBuild).toHaveBeenCalled();
    expect(state.refreshRecords).toHaveBeenCalledWith(false, "r1");
  });
});
