/* Copyright 2026 Aaron John Schlosser, PhD. */
import { ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

const corpusBuilderApi = vi.hoisted(() => ({
  metadataDecision: vi.fn(),
  metadataDecisionBatch: vi.fn(),
  patchMetadata: vi.fn(),
  patchEvidence: vi.fn(),
  clearAllMetadataCache: vi.fn(),
  requeueMetadata: vi.fn(),
  rerunMetadataEnrichment: vi.fn(),
  editorialMemory: vi.fn(),
  resetEditorialMemory: vi.fn(),
  rerunMetadata: vi.fn(),
  bulkMetadata: vi.fn(),
}));

vi.mock("../../src/api/corpus", async () => {
  const actual =
    await vi.importActual<typeof import("../../src/api/corpus")>("../../src/api/corpus");
  return { ...actual, corpusBuilderApi };
});

import { useCorpusMetadataReview } from "../../src/features/corpus-builder/composables/useCorpusMetadataReview";

function row(overrides: Record<string, unknown> = {}) {
  return {
    record_id: "r1",
    record_revision: 1,
    speaker: "Derrida",
    metadata_evidence: {},
    ...overrides,
  } as any;
}

function setup() {
  const currentBuild = ref<any | null>({ build_id: "b1" });
  const selectedRecord = ref<any | null>(row());
  const selectedRecordId = ref("r1");
  const records = ref<any[]>([selectedRecord.value]);
  const busy = ref("");
  const selectedEvidenceField = ref("");
  const reviewInspectorTab = ref<"metadata" | "evidence" | "source">("metadata");
  const selectedPdfPage = ref(1);
  const sourceBlocks = ref<any[]>([{ block_id: "block-1", page: 4, text: "Evidence" }]);
  const selectedReviewIds = ref(new Set<string>());
  const reviewQueue = ref<any>("all");
  const recordQuery = ref("");
  const llmActionProviderId = ref("local");
  const llmActionModel = ref("qwen");
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
  const applyAuthoritativeRecord = vi.fn((record: any, build?: any) => {
    selectedRecord.value = record;
    if (build) currentBuild.value = build;
  });
  const restoreReviewViewport = vi.fn(async () => undefined);
  const setMessage = vi.fn();

  const review = useCorpusMetadataReview({
    currentBuild,
    selectedRecord,
    selectedRecordId,
    records,
    busy,
    selectedEvidenceField,
    reviewInspectorTab,
    selectedPdfPage,
    sourceBlocks,
    selectedReviewIds,
    reviewQueue,
    recordQuery,
    llmActionProviderId,
    llmActionModel,
    selectedProviderId,
    providerProfiles,
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
    applyAuthoritativeRecord,
    syncBuildInRail: vi.fn(),
    registerBuildOperation: vi.fn(),
    startPolling: vi.fn(),
    refreshBuild: vi.fn(async () => undefined),
    refreshRecords: vi.fn(async () => undefined),
    recordMetadata: (record) => ({
      speaker: (record as any).speaker,
      target: (record as any).target,
    }),
    metadataDraftKey: (buildId, recordId) => `metadata.${buildId}.${recordId}`,
    setMessage,
    t: (key, fallback) => fallback || key,
    tf: (key, fallbackOrValues, values) => {
      const vars =
        fallbackOrValues && typeof fallbackOrValues === "object" ? fallbackOrValues : values || {};
      return Object.entries(vars).reduce(
        (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
        typeof fallbackOrValues === "string" ? fallbackOrValues : key,
      );
    },
  });

  return {
    review,
    currentBuild,
    selectedRecord,
    records,
    selectedEvidenceField,
    reviewInspectorTab,
    selectedPdfPage,
    queued,
    applyAuthoritativeRecord,
  };
}

describe("Corpus Builder metadata review", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("applies a metadata decision optimistically and preserves canonical persistence", async () => {
    const state = setup();
    corpusBuilderApi.metadataDecision.mockResolvedValue({
      record: row({ target: "Kant", record_revision: 2 }),
      build: { build_id: "b1" },
    });

    await state.review.resolveMetadataField("target", "Kant");

    expect(state.selectedRecord.value?.target).toBe("Kant");
    expect(state.selectedRecord.value?.record_revision).toBe(2);
    expect(state.review.metadataKnownValues.value.target).toContain("Kant");
    expect(state.queued).toHaveLength(1);

    await state.queued[0](false);
    expect(corpusBuilderApi.metadataDecision).toHaveBeenCalledWith("b1", "r1", "target", "Kant", 1);
    expect(state.applyAuthoritativeRecord).toHaveBeenCalled();
  });

  it("adds evidence through the shared metadata evidence path", async () => {
    const state = setup();

    await state.review.assignEvidenceBlock("speaker", "block-1");

    expect(state.selectedEvidenceField.value).toBe("speaker");
    expect(state.selectedRecord.value?.metadata_evidence?.speaker?.block_ids).toEqual(["block-1"]);
    expect(state.queued).toHaveLength(1);

    corpusBuilderApi.patchEvidence.mockResolvedValue(state.selectedRecord.value);
    await state.queued[0](false);
    expect(corpusBuilderApi.patchEvidence).toHaveBeenCalledWith(
      "b1",
      "r1",
      "speaker",
      ["block-1"],
      1,
      expect.any(String),
      1,
    );
  });

  it("routes metadata source inspection to the matching source block", () => {
    const state = setup();
    state.selectedRecord.value = row({
      metadata_evidence: {
        speaker: { block_ids: ["block-1"], confidence: 0.8 },
      },
    });

    state.review.showMetadataSource("speaker");

    expect(state.reviewInspectorTab.value).toBe("source");
    expect(state.selectedPdfPage.value).toBe(4);
  });
});
