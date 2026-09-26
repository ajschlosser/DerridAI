/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, ref, type ComputedRef, type Ref } from "vue";
import {
  corpusBuilderApi,
  type CorpusBuild,
  type CorpusRecord,
  type SourceBlock,
} from "../../../api/corpus";
import type { ReviewViewport } from "./useCorpusReviewWorkspace";

type MessageTone = "error" | "notice";

interface CorpusBoundaryReviewOptions {
  currentBuild: Ref<CorpusBuild | null>;
  selectedRecord: Ref<CorpusRecord | null>;
  selectedRecordId: Ref<string>;
  records: Ref<CorpusRecord[]>;
  recordTotal: Ref<number>;
  recordOffset: Ref<number>;
  selectedRecordIndex: ComputedRef<number>;
  visibleBlocks: ComputedRef<SourceBlock[]>;
  busy: Ref<string>;
  structuralReviewLocked: ComputedRef<boolean>;
  editingText: Ref<boolean>;
  metadataEditorDirty: Ref<boolean>;
  llmActionProviderId: Ref<string>;
  llmActionModel: Ref<string>;
  selectedProviderId: Ref<string>;
  directProfilePayloadWithModel: (
    profileId: string,
    modelOverride?: string,
  ) => Record<string, unknown> | null;
  captureReviewViewport: () => ReviewViewport;
  restoreReviewViewport: (
    snapshot: ReviewViewport,
    options?: { record?: boolean; inspector?: boolean },
  ) => Promise<void>;
  queueRecordRequest: (
    recordId: string | readonly string[],
    fields: string[],
    request: (rebase: boolean) => Promise<unknown>,
    onFailure?: () => void | Promise<void>,
    retryOnFailure?: boolean,
  ) => void;
  refreshBuild: () => Promise<void>;
  refreshRecords: (reset?: boolean, preferredId?: string) => Promise<void>;
  setMessage: (message: string, tone?: MessageTone) => void;
  t: (key: string, fallback?: string) => string;
  tf: (key: string, values: Record<string, string | number>) => string;
}

export function useCorpusBoundaryReview(options: CorpusBoundaryReviewOptions) {
  const boundarySliceOpen = ref(false);

  const canMergePrevious = computed(() => {
    const topologyIndex = Number(options.selectedRecord.value?.topology_index ?? -1);
    return topologyIndex >= 0
      ? topologyIndex > 0
      : options.recordOffset.value + Math.max(0, options.selectedRecordIndex.value) > 0;
  });

  const canMergeNext = computed(() => {
    const topologyIndex = Number(options.selectedRecord.value?.topology_index ?? -1);
    const topologyCount = Number(
      options.selectedRecord.value?.topology_count ?? options.recordTotal.value,
    );
    if (topologyIndex >= 0 && topologyCount > 0) return topologyIndex < topologyCount - 1;
    const globalIndex = options.recordOffset.value + options.selectedRecordIndex.value;
    return globalIndex >= 0 && globalIndex < options.recordTotal.value - 1;
  });

  function mergeUnavailable(direction: "previous" | "next"): string | undefined {
    if (options.busy.value !== "") return options.t("pdf_corpus.reason.busy");
    if (options.structuralReviewLocked.value) {
      return options.t("pdf_corpus.reason.structure_locked");
    }
    if (direction === "previous" && !canMergePrevious.value) {
      return options.t("pdf_corpus.reason.no_previous");
    }
    if (direction === "next" && !canMergeNext.value) {
      return options.t("pdf_corpus.reason.no_next");
    }
    return undefined;
  }

  function sliceUnavailable(): string | undefined {
    if (options.busy.value !== "") return options.t("pdf_corpus.reason.busy");
    if (options.editingText.value) return options.t("pdf_corpus.reason.finish_text_edit");
    if (options.metadataEditorDirty.value) {
      return options.t("pdf_corpus.reason.finish_metadata_edit");
    }
    if (!canMergePrevious.value && !canMergeNext.value) {
      return options.t("pdf_corpus.reason.no_neighbour");
    }
    return undefined;
  }

  interface StructuralResult {
    record: CorpusRecord;
    records: CorpusRecord[];
    retired_record_ids: string[];
  }

  /**
   * Split, merge and create-from-selection retire the affected records and mint
   * new ones with new IDs, so nothing can be applied optimistically: the server
   * decides the resulting IDs and the client reloads them.
   */
  function restructure(
    involvedIds: string[],
    run: () => Promise<StructuralResult>,
    done: (result: StructuralResult) => string,
  ) {
    if (!options.currentBuild.value) return;
    const viewport = options.captureReviewViewport();
    options.queueRecordRequest(
      involvedIds,
      ["record boundary"],
      async () => {
        const result = await run();
        boundarySliceOpen.value = false;
        await options.refreshBuild();
        await options.refreshRecords(false, result.record.record_id);
        await options.restoreReviewViewport(viewport, { record: true });
        options.setMessage(done(result));
      },
      undefined,
      false,
    );
  }

  function neighborId(direction: "previous" | "next"): string | undefined {
    const id = options.selectedRecord.value?.record_id;
    const index = options.records.value.findIndex((row) => row.record_id === id);
    return options.records.value[direction === "previous" ? index - 1 : index + 1]?.record_id;
  }

  async function merge(direction: "previous" | "next") {
    const target = options.selectedRecord.value;
    const buildId = options.currentBuild.value?.build_id;
    if (!buildId || !target) return;
    const other = neighborId(direction);
    if (!other) return;
    restructure(
      [target.record_id, other],
      () =>
        corpusBuilderApi.merge(
          buildId,
          target.record_id,
          direction,
          Number(target.record_revision || 1),
        ),
      () =>
        options.tf("pdf_corpus.merged", {
          direction: options.t(`pdf_corpus.${direction}`, direction),
        }),
    );
  }

  /** Split after a source block (`afterBlockId`) or at a character offset in the record text. */
  async function split(at: string | number) {
    const target = options.selectedRecord.value;
    const buildId = options.currentBuild.value?.build_id;
    if (!buildId || !target) return;
    if (typeof at === "string" && !(target.source_block_ids || []).includes(at)) return;
    restructure(
      [target.record_id],
      () =>
        corpusBuilderApi.split(buildId, target.record_id, at, Number(target.record_revision || 1)),
      () => options.t("pdf_corpus.split_done"),
    );
  }

  /**
   * Make a new record from `text[start:end]`. The text before and after joins the
   * previous / next record, or becomes a record of its own.
   */
  async function createFromSelection(
    start: number,
    end: number,
    left: "distinct" | "merge_prior" = "distinct",
    right: "distinct" | "merge_next" = "distinct",
  ) {
    const target = options.selectedRecord.value;
    const buildId = options.currentBuild.value?.build_id;
    if (!buildId || !target) return;
    const involved = [target.record_id];
    if (left === "merge_prior") {
      const id = neighborId("previous");
      if (!id) return;
      involved.push(id);
    }
    if (right === "merge_next") {
      const id = neighborId("next");
      if (!id) return;
      involved.push(id);
    }
    restructure(
      involved,
      () =>
        corpusBuilderApi.createFromSelection(buildId, target.record_id, {
          start,
          end,
          left,
          right,
          expectedRevision: Number(target.record_revision || 1),
        }),
      () => options.t("pdf_corpus.slice_done"),
    );
  }

  async function adjudicateBoundary(
    direction: "previous" | "next",
    profileId = options.llmActionProviderId.value || options.selectedProviderId.value,
    model = options.llmActionModel.value,
  ) {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    const id = options.selectedRecord.value.record_id;
    const viewport = options.captureReviewViewport();
    options.busy.value = "boundary";
    try {
      const actionPayload = options.directProfilePayloadWithModel(profileId, model) || {
        provider_profile_id: profileId,
        model: model || undefined,
      };
      const result = await corpusBuilderApi.adjudicateBoundary(
        options.currentBuild.value.build_id,
        id,
        direction,
        actionPayload,
      );
      await options.refreshBuild();
      await options.refreshRecords(false, id);
      await options.restoreReviewViewport(viewport, { record: true });
      const decision = String(result.decision?.decision || "uncertain");
      options.setMessage(
        options.tf("pdf_corpus.boundary_check_done", {
          decision: options.t(`pdf_corpus.boundary_llm.${decision}`, decision),
        }),
      );
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  return {
    boundarySliceOpen,
    canMergePrevious,
    canMergeNext,
    mergeUnavailable,
    sliceUnavailable,
    merge,
    split,
    createFromSelection,
    adjudicateBoundary,
  };
}
