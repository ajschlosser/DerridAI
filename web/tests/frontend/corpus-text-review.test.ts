/* Copyright 2026 Aaron John Schlosser, PhD. */
import { ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

const corpusBuilderApi = vi.hoisted(() => ({
  patchText: vi.fn(),
  touchupText: vi.fn(),
  setTouchupProposalStatus: vi.fn(),
}));

vi.mock("../../src/api/corpus", async () => {
  const actual =
    await vi.importActual<typeof import("../../src/api/corpus")>("../../src/api/corpus");
  return { ...actual, corpusBuilderApi };
});

import { useCorpusTextReview } from "../../src/features/corpus-builder/composables/useCorpusTextReview";

function setup() {
  const currentBuild = ref<any | null>({ build_id: "b1" });
  const selectedBuildId = ref("b1");
  const selectedRecord = ref<any | null>({
    record_id: "r1",
    record_revision: 1,
    text: "Original text",
    text_length: 13,
  });
  const records = ref<any[]>([selectedRecord.value]);
  const busy = ref("");
  const sourceTranscriptionOpen = ref(true);
  const llmActionProviderId = ref("");
  const llmActionModel = ref("");
  const selectedProviderId = ref("local");
  const providerProfiles = ref<any[]>([{ id: "local", model: "qwen" }]);
  const queued: Array<(rebase: boolean) => Promise<unknown>> = [];
  const queueRecordRequest = vi.fn(
    (
      _recordId: string | readonly string[],
      _fields: string[],
      request: (rebase: boolean) => Promise<unknown>,
    ) => queued.push(request),
  );
  const restoreReviewViewport = vi.fn(async () => undefined);
  const setMessage = vi.fn();

  const review = useCorpusTextReview({
    currentBuild,
    selectedBuildId,
    selectedRecord,
    records,
    busy,
    sourceTranscriptionOpen,
    llmActionProviderId,
    llmActionModel,
    selectedProviderId,
    providerProfiles,
    directProfilePayloadWithModel: (profileId, model) => ({
      provider_profile_id: profileId,
      model: model || "qwen",
    }),
    captureReviewViewport: () => ({
      windowY: 0,
      queueTop: 0,
      recordTop: 0,
      inspectorTop: 0,
    }),
    restoreReviewViewport,
    queueRecordRequest,
    textDraftKey: (buildId, recordId) => `draft.${buildId}.${recordId}`,
    setMessage,
    t: (key) => key,
  });

  return {
    review,
    selectedRecord,
    sourceTranscriptionOpen,
    llmActionProviderId,
    llmActionModel,
    queued,
  };
}

describe("Corpus Builder text review", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("applies reviewed text optimistically and queues persistence with the expected revision", async () => {
    const state = setup();
    state.review.beginTextEdit();
    state.review.textDraft.value = "Edited text";

    await state.review.saveReviewedText(false);

    expect(state.selectedRecord.value?.text).toBe("Edited text");
    expect(state.selectedRecord.value?.record_revision).toBe(2);
    expect(state.review.editingText.value).toBe(false);
    expect(state.queued).toHaveLength(1);

    corpusBuilderApi.patchText.mockResolvedValue(state.selectedRecord.value);
    await state.queued[0](false);
    expect(corpusBuilderApi.patchText).toHaveBeenCalledWith("b1", "r1", "Edited text", 1, false);
  });

  it("opens touch-up with the shared provider/model defaults", () => {
    const state = setup();

    state.review.openLlmTouchup("Original text");

    expect(state.review.llmTouchupOpen.value).toBe(true);
    expect(state.llmActionProviderId.value).toBe("local");
    expect(state.llmActionModel.value).toBe("qwen");
    expect(state.review.textDraft.value).toBe("Original text");
  });

  it("persists source transcription through the same reviewed-text path", async () => {
    const state = setup();

    await state.review.saveSourceTranscription("Corrected transcription");

    expect(state.selectedRecord.value?.text).toBe("Corrected transcription");
    expect(state.sourceTranscriptionOpen.value).toBe(false);
    expect(state.queued).toHaveLength(1);
  });
});
