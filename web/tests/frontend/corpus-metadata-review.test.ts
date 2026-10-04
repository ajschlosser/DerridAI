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
  const failures: Array<() => void | Promise<void>> = [];
  const queueRecordRequest = vi.fn(
    (
      _recordId: string | readonly string[],
      _fields: string[],
      request: (rebase: boolean) => Promise<unknown>,
      onFailure?: () => void | Promise<void>,
    ) => {
      queued.push(request);
      if (onFailure) failures.push(onFailure);
    },
  );
  const applyAuthoritativeRecord = vi.fn((record: any, build?: any) => {
    selectedRecord.value = record;
    if (build) currentBuild.value = build;
  });
  const applyRecordToQueue = vi.fn();
  const restoreReviewViewport = vi.fn(async () => undefined);
  const setMessage = vi.fn();

  const review = useCorpusMetadataReview({
    currentBuild,
    selectedRecord,
    selectedRecordId,
    applyRecordToQueue,
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
    selectedEvidenceField,
    reviewInspectorTab,
    selectedPdfPage,
    queued,
    failures,
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

    // The optimistic value releases the editor before the request runs. A slow
    // persistence round trip must not leave the field in "Saving…".
    expect(state.review.metadataSavingField.value).toBe("");
    expect(state.review.metadataSavedField.value).toBe("target");
    expect(state.selectedRecord.value?.target).toBe("Kant");
    expect(state.selectedRecord.value?.record_revision).toBe(2);
    expect(state.review.metadataKnownValues.value.target).toContain("Kant");
    expect(state.queued).toHaveLength(1);

    await state.queued[0](false);
    expect(corpusBuilderApi.metadataDecision).toHaveBeenCalledWith(
      "b1",
      "r1",
      "target",
      "Kant",
      1,
      false,
      undefined,
      undefined,
    );
    expect(state.applyAuthoritativeRecord).toHaveBeenCalled();
  });

  it("optimistically settles review state before persistence completes", async () => {
    const state = setup();
    state.selectedRecord.value = row({
      target: "Kant",
      metadata_incomplete_fields: ["target"],
      metadata_review_fields: ["speaker", "target"],
      acceptance_blocking_fields: ["target"],
      review_issue_codes: ["metadata"],
      review_state: "metadata",
      metadata_complete: false,
      metadata_field_status: {
        target: { status: "unresolved", method: "llm" },
        speaker: { status: "unresolved", method: "llm" },
      },
    });

    await state.review.resolveMetadataField("target", "hospitality");

    expect(state.selectedRecord.value?.metadata_incomplete_fields).toEqual([]);
    expect(state.selectedRecord.value?.metadata_review_fields).toEqual(["speaker"]);
    expect(state.selectedRecord.value?.acceptance_blocking_fields).toEqual([]);
    expect(state.selectedRecord.value?.metadata_complete).toBe(false);
    expect(state.selectedRecord.value?.metadata_field_status?.target).toMatchObject({
      status: "human_confirmed",
      authority_status: "human_confirmed",
      evaluation_status: "value_supported",
      value_status: "present",
      optimistic_review: true,
    });
    // Persistence has not run yet; this state is deliberately local and immediate.
    expect(state.queued).toHaveLength(1);
  });

  it("saves a value and its selected-text evidence in one optimistic request", async () => {
    const state = setup();
    corpusBuilderApi.metadataDecision.mockResolvedValue({
      record: row({ speaker: "Derrida", record_revision: 2 }),
      build: { build_id: "b1" },
    });

    await state.review.resolveMetadataField("speaker", "Derrida", "block-9");

    expect(state.selectedRecord.value?.speaker).toBe("Derrida");
    expect(state.selectedRecord.value?.metadata_evidence?.speaker?.block_ids).toEqual(["block-9"]);
    expect(state.queued).toHaveLength(1);
    await state.queued[0](false);
    expect(corpusBuilderApi.metadataDecision).toHaveBeenCalledWith(
      "b1",
      "r1",
      "speaker",
      "Derrida",
      1,
      false,
      ["block-9"],
      undefined,
    );
    // No separate evidence round trip.
    expect(corpusBuilderApi.patchEvidence).not.toHaveBeenCalled();
  });

  it("releases the editor immediately and rolls optimistic feedback back after failure", async () => {
    const state = setup();
    await state.review.resolveMetadataField("target", "Kant");

    expect(state.selectedRecord.value?.target).toBe("Kant");
    expect(state.review.metadataSavingField.value).toBe("");
    expect(state.review.metadataSavedField.value).toBe("target");
    expect(state.failures).toHaveLength(1);

    await state.failures[0]();

    expect(state.review.metadataSavingField.value).toBe("");
    expect(state.review.metadataSavedField.value).toBe("");
  });

  it("does not let an older failed save clear feedback from a newer queued decision", async () => {
    const state = setup();

    await state.review.resolveMetadataField("target", "Kant");
    await state.review.resolveMetadataField("speaker", "Jacques Derrida");

    expect(state.review.metadataSavingField.value).toBe("");
    expect(state.review.metadataSavedField.value).toBe("speaker");
    expect(state.failures).toHaveLength(2);

    await state.failures[0]();

    expect(state.review.metadataSavingField.value).toBe("");
    expect(state.review.metadataSavedField.value).toBe("speaker");
  });

  it("releases a confirmed-no-value decision before persistence completes", async () => {
    const state = setup();
    state.selectedRecord.value = row({
      target: "Kant",
      metadata_incomplete_fields: ["target"],
      metadata_review_fields: ["target"],
      acceptance_blocking_fields: ["target"],
      review_issue_codes: ["metadata"],
      review_state: "metadata",
      metadata_complete: false,
      metadata_field_status: { target: { status: "unresolved", method: "llm" } },
    });

    await state.review.resolveMetadataNoValue("target");

    expect(state.review.metadataSavingField.value).toBe("");
    expect(state.review.metadataSavedField.value).toBe("target");
    expect(state.selectedRecord.value?.target).toBeNull();
    expect(state.selectedRecord.value?.metadata_incomplete_fields).toEqual([]);
    expect(state.selectedRecord.value?.metadata_review_fields).toEqual([]);
    expect(state.selectedRecord.value?.metadata_complete).toBe(true);
    expect(state.selectedRecord.value?.review_issue_codes).toEqual([]);
    expect(state.selectedRecord.value?.review_state).toBe("ready");
    expect(state.selectedRecord.value?.metadata_field_status?.target).toMatchObject({
      status: "confirmed_absent",
      evaluation_status: "no_supported_value",
      value_status: "confirmed_absent",
      optimistic_review: true,
    });
    expect(state.queued).toHaveLength(1);
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
      [],
    );
  });

  it("keeps spans cited from other records when the record's own evidence changes", async () => {
    const state = setup();
    state.selectedRecord.value = row({
      metadata_evidence: {
        speaker: { block_ids: ["block-1"], external_block_ids: ["other-9"], confidence: 1 },
      },
    });
    state.selectedEvidenceField.value = "speaker";

    await state.review.toggleEvidenceBlock("block-2");

    expect(state.selectedRecord.value?.metadata_evidence?.speaker?.external_block_ids).toEqual([
      "other-9",
    ]);
    await state.queued[0](false);
    expect(corpusBuilderApi.patchEvidence).toHaveBeenLastCalledWith(
      "b1",
      "r1",
      "speaker",
      ["block-1", "block-2"],
      1,
      expect.any(String),
      expect.any(Number),
      ["other-9"],
    );
  });

  it("replaces only a field's other-record spans from the Evidence tab", async () => {
    const state = setup();
    state.selectedRecord.value = row({
      speaker: "Levinas",
      metadata_evidence: {
        speaker: { block_ids: ["block-1"], external_block_ids: ["other-9"], confidence: 1 },
      },
    });

    await state.review.setExternalEvidenceBlocks("speaker", ["other-3", "other-4"]);

    const evidence = state.selectedRecord.value?.metadata_evidence?.speaker;
    expect(evidence?.block_ids).toEqual(["block-1"]);
    expect(evidence?.external_block_ids).toEqual(["other-3", "other-4"]);
    expect(state.selectedRecord.value?.speaker).toBe("Levinas");
    await state.queued[0](false);
    expect(corpusBuilderApi.patchEvidence).toHaveBeenLastCalledWith(
      "b1",
      "r1",
      "speaker",
      ["block-1"],
      1,
      expect.any(String),
      expect.any(Number),
      ["other-3", "other-4"],
    );
    expect(corpusBuilderApi.patchMetadata).not.toHaveBeenCalled();
  });

  it("opens the Evidence tab and the matching source page", () => {
    const state = setup();
    state.selectedRecord.value = row({
      metadata_evidence: {
        speaker: { block_ids: ["block-1"], confidence: 0.8 },
      },
    });

    state.review.showMetadataSource("speaker");

    expect(state.reviewInspectorTab.value).toBe("evidence");
    expect(state.selectedPdfPage.value).toBe(4);
  });

  it("persists Save all suggestions through the batch decision endpoint", async () => {
    const state = setup();
    corpusBuilderApi.metadataDecisionBatch.mockResolvedValue({
      record: row({ speaker: "Jacques Derrida", target: "hospitality", record_revision: 2 }),
      build: { build_id: "b1" },
      changed_fields: ["speaker", "target"],
    });

    state.selectedRecord.value = row({
      metadata_review_fields: ["speaker", "target"],
      metadata_incomplete_fields: [],
      review_issue_codes: ["metadata"],
      review_state: "metadata",
      metadata_complete: false,
      metadata_field_status: {
        speaker: { status: "unresolved", method: "llm" },
        target: { status: "unresolved", method: "llm" },
      },
    });

    await state.review.resolveMetadataSuggestions({
      speaker: "Jacques Derrida",
      target: "hospitality",
    });

    // The optimistic batch does not lock the panel while persistence runs.
    expect(state.review.metadataSavingField.value).toBe("");
    expect(state.selectedRecord.value?.target).toBe("hospitality");
    expect(state.selectedRecord.value?.metadata_review_fields).toEqual([]);
    expect(state.selectedRecord.value?.metadata_complete).toBe(true);
    expect(state.selectedRecord.value?.review_state).toBe("ready");
    expect(state.queued).toHaveLength(1);

    await state.queued[0](false);

    expect(corpusBuilderApi.metadataDecisionBatch).toHaveBeenCalledWith(
      "b1",
      "r1",
      { speaker: "Jacques Derrida", target: "hospitality" },
      1,
      [],
    );
    expect(state.review.metadataSavingField.value).toBe("");
    expect(state.applyAuthoritativeRecord).toHaveBeenCalled();
  });

  it("persists model-suggested absences as confirmed absence in a mixed batch", async () => {
    const state = setup();
    corpusBuilderApi.metadataDecisionBatch.mockResolvedValue({
      record: row({
        speaker: "Jacques Derrida",
        target: null,
        record_revision: 2,
        metadata_field_status: {
          target: {
            status: "confirmed_absent",
            authority_status: "human_confirmed",
            evaluation_status: "no_supported_value",
            value_status: "confirmed_absent",
          },
        },
      }),
      build: { build_id: "b1" },
      changed_fields: ["speaker", "target"],
    });

    state.selectedRecord.value = row({
      target: null,
      metadata_review_fields: ["speaker", "target"],
      metadata_incomplete_fields: ["target"],
      review_issue_codes: ["metadata"],
      review_state: "metadata",
      metadata_complete: false,
      metadata_field_status: {
        speaker: { status: "unresolved", method: "llm" },
        target: {
          status: "unresolved",
          method: "llm",
          evaluation_status: "no_supported_value",
          suggested_absence: true,
        },
      },
    });

    const changes = { speaker: "Jacques Derrida", target: null };
    await state.review.resolveMetadataSuggestions(changes, ["target"]);

    expect(state.selectedRecord.value?.metadata_field_status?.target).toMatchObject({
      status: "confirmed_absent",
      authority_status: "human_confirmed",
      evaluation_status: "no_supported_value",
      value_status: "confirmed_absent",
      optimistic_review: true,
    });
    expect(state.selectedRecord.value?.metadata_review_fields).toEqual([]);
    expect(state.selectedRecord.value?.metadata_incomplete_fields).toEqual([]);
    expect(state.queued).toHaveLength(1);

    await state.queued[0](false);

    expect(corpusBuilderApi.metadataDecisionBatch).toHaveBeenCalledWith("b1", "r1", changes, 1, [
      "target",
    ]);
  });
});
