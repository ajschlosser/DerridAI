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

  async function merge(direction: "previous" | "next") {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    const id = options.selectedRecord.value.record_id;
    const index = options.records.value.findIndex((row) => row.record_id === id);
    const neighborIndex = direction === "previous" ? index - 1 : index + 1;
    if (index < 0 || neighborIndex < 0 || neighborIndex >= options.records.value.length) return;

    const before = options.records.value.slice();
    const beforeTotal = options.recordTotal.value;
    const beforeSelected = options.selectedRecord.value;
    const firstIndex = Math.min(index, neighborIndex);
    const first = options.records.value[firstIndex];
    const second = options.records.value[Math.max(index, neighborIndex)];
    const mergedText = [first.text, second.text].filter(Boolean).join("\n\n");
    const merged: CorpusRecord = {
      ...first,
      text: mergedText,
      text_length: mergedText.length,
      source_block_ids: [...(first.source_block_ids || []), ...(second.source_block_ids || [])],
      source_unit_ids: [...(first.source_unit_ids || []), ...(second.source_unit_ids || [])],
      source_spans: [...(first.source_spans || []), ...(second.source_spans || [])],
      review_disposition: "pending",
      accepted: false,
      rejected: false,
      needs_review: true,
      record_revision:
        Math.max(Number(first.record_revision || 1), Number(second.record_revision || 1)) + 1,
    };

    const viewport = options.captureReviewViewport();
    options.records.value.splice(firstIndex, 2, merged);
    options.recordTotal.value = Math.max(0, options.recordTotal.value - 1);
    options.selectedRecord.value = merged;
    options.selectedRecordId.value = merged.record_id;
    await options.restoreReviewViewport(viewport, { record: true });

    options.queueRecordRequest(
      [id, second.record_id],
      ["record boundary"],
      async () => {
        const row = await corpusBuilderApi.merge(
          options.currentBuild.value!.build_id,
          id,
          direction,
          Number(before.find((item) => item.record_id === id)?.record_revision || 1),
        );
        await options.refreshBuild();
        await options.refreshRecords(false, row.record_id);
        await options.restoreReviewViewport(viewport, { record: true });
        options.setMessage(
          options.tf("pdf_corpus.merged", {
            direction: options.t(`pdf_corpus.${direction}`, direction),
          }),
        );
      },
      () => {
        options.records.value = before;
        options.recordTotal.value = beforeTotal;
        options.selectedRecord.value = beforeSelected;
        options.selectedRecordId.value = beforeSelected.record_id;
      },
      false,
    );
  }

  async function split(afterBlockId: string) {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    const id = options.selectedRecord.value.record_id;
    const targetIndex = options.records.value.findIndex((row) => row.record_id === id);
    const blockIds = [...(options.selectedRecord.value.source_block_ids || [])];
    const cut = blockIds.indexOf(afterBlockId) + 1;
    if (targetIndex < 0 || cut <= 0 || cut >= blockIds.length) return;

    const before = options.records.value.slice();
    const beforeTotal = options.recordTotal.value;
    const beforeSelected = options.selectedRecord.value;
    const blockText = new Map(
      options.visibleBlocks.value.map((block) => [block.block_id, block.text]),
    );
    const textFor = (ids: string[]) =>
      ids
        .map((blockId) => blockText.get(blockId) || "")
        .filter(Boolean)
        .join("\n\n");
    const leftIds = blockIds.slice(0, cut);
    const rightIds = blockIds.slice(cut);
    const leftText = textFor(leftIds);
    const rightText = textFor(rightIds);
    if (!leftText || !rightText) return;

    const nextId = `${id}-split-pending`;
    const left: CorpusRecord = {
      ...options.selectedRecord.value,
      source_block_ids: leftIds,
      source_unit_ids: leftIds,
      source_spans: (options.selectedRecord.value.source_spans || []).filter((span) =>
        leftIds.includes(String(span.block_id || "")),
      ),
      text: leftText,
      text_length: leftText.length,
      record_revision: Number(options.selectedRecord.value.record_revision || 1) + 1,
      review_disposition: "pending",
      accepted: false,
      rejected: false,
      needs_review: true,
    };
    const right: CorpusRecord = {
      ...options.selectedRecord.value,
      record_id: nextId,
      source_block_ids: rightIds,
      source_unit_ids: rightIds,
      source_spans: (options.selectedRecord.value.source_spans || []).filter((span) =>
        rightIds.includes(String(span.block_id || "")),
      ),
      text: rightText,
      text_length: rightText.length,
      record_revision: 1,
      review_disposition: "pending",
      accepted: false,
      rejected: false,
      needs_review: true,
    };

    const viewport = options.captureReviewViewport();
    options.records.value.splice(targetIndex, 1, left, right);
    options.recordTotal.value += 1;
    options.selectedRecord.value = left;
    options.selectedRecordId.value = left.record_id;
    await options.restoreReviewViewport(viewport, { record: true });

    options.queueRecordRequest(
      [id, nextId],
      ["record boundary"],
      async () => {
        const result = await corpusBuilderApi.split(
          options.currentBuild.value!.build_id,
          id,
          afterBlockId,
          Number(beforeSelected.record_revision || 1),
        );
        await options.refreshBuild();
        await options.refreshRecords(false, result.records[0]?.record_id || id);
        await options.restoreReviewViewport(viewport, { record: true });
        options.setMessage(options.t("pdf_corpus.split_done"));
      },
      () => {
        options.records.value = before;
        options.recordTotal.value = beforeTotal;
        options.selectedRecord.value = beforeSelected;
        options.selectedRecordId.value = beforeSelected.record_id;
      },
      false,
    );
  }

  async function sliceRecord(
    direction: "previous" | "next" | "keep" | "new",
    offset: number,
    keepEnd?: number,
  ) {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    const id = options.selectedRecord.value.record_id;

    if (direction === "keep") {
      const index = options.records.value.findIndex((row) => row.record_id === id);
      const targetText = String(options.selectedRecord.value.text || "");
      const previous = options.records.value[index - 1];
      const following = options.records.value[index + 1];
      if (
        index <= 0 ||
        index >= options.records.value.length - 1 ||
        keepEnd === undefined ||
        offset <= 0 ||
        offset >= keepEnd ||
        keepEnd > targetText.length
      ) {
        return;
      }

      const prefix = targetText.slice(0, offset).trim();
      const retained = targetText.slice(offset, keepEnd).trim();
      const suffix = targetText.slice(keepEnd).trim();
      if (!prefix || !retained || !suffix) return;

      const before = options.records.value.slice();
      const beforeSelected = options.selectedRecord.value;
      const previousText = `${String(previous.text || "").trim()}\n\n${prefix}`.trim();
      const followingText = `${suffix}\n\n${String(following.text || "").trim()}`.trim();
      const nextRecord = (row: CorpusRecord, text: string): CorpusRecord => ({
        ...row,
        text,
        text_length: text.length,
        record_revision: Number(row.record_revision || 1) + 1,
        review_disposition: "pending",
        accepted: false,
        rejected: false,
        needs_review: true,
      });
      const updatedPrevious = nextRecord(previous, previousText);
      const updatedTarget = nextRecord(options.selectedRecord.value, retained);
      const updatedFollowing = nextRecord(following, followingText);
      const viewport = options.captureReviewViewport();

      options.records.value.splice(index - 1, 3, updatedPrevious, updatedTarget, updatedFollowing);
      options.selectedRecord.value = updatedTarget;
      options.selectedRecordId.value = id;
      await options.restoreReviewViewport(viewport, { record: true });

      options.queueRecordRequest(
        [previous.record_id, id, following.record_id],
        ["record boundary"],
        async () => {
          const result = await corpusBuilderApi.sliceRecord(
            options.currentBuild.value!.build_id,
            id,
            direction,
            offset,
            Number(beforeSelected.record_revision || 1),
            keepEnd,
          );
          boundarySliceOpen.value = false;
          await options.refreshBuild();
          await options.refreshRecords(false, result.record.record_id);
          await options.restoreReviewViewport(viewport, { record: true });
          options.setMessage(options.t("pdf_corpus.slice_done"));
        },
        () => {
          options.records.value = before;
          options.selectedRecord.value = beforeSelected;
          options.selectedRecordId.value = beforeSelected.record_id;
        },
        false,
      );
      return;
    }

    if (direction === "previous" || direction === "next") {
      const index = options.records.value.findIndex((row) => row.record_id === id);
      const neighborIndex = direction === "previous" ? index - 1 : index + 1;
      const targetText = String(options.selectedRecord.value.text || "");
      if (
        index < 0 ||
        neighborIndex < 0 ||
        neighborIndex >= options.records.value.length ||
        offset <= 0 ||
        offset >= targetText.length
      ) {
        return;
      }

      const before = options.records.value.slice();
      const beforeSelected = options.selectedRecord.value;
      const neighbor = options.records.value[neighborIndex];
      const moved = targetText
        .slice(
          direction === "previous" ? 0 : offset,
          direction === "previous" ? offset : undefined,
        )
        .trim();
      const retained = targetText.slice(direction === "previous" ? offset : 0).trim();
      if (!moved || !retained) return;

      const target: CorpusRecord = {
        ...options.selectedRecord.value,
        text: retained,
        text_length: retained.length,
        record_revision: Number(options.selectedRecord.value.record_revision || 1) + 1,
        review_disposition: "pending",
        accepted: false,
        rejected: false,
        needs_review: true,
      };
      const neighborText =
        direction === "previous"
          ? `${String(neighbor.text || "").trim()}\n\n${moved}`.trim()
          : `${moved}\n\n${String(neighbor.text || "").trim()}`.trim();
      const updatedNeighbor: CorpusRecord = {
        ...neighbor,
        text: neighborText,
        text_length: neighborText.length,
        record_revision: Number(neighbor.record_revision || 1) + 1,
        review_disposition: "pending",
        accepted: false,
        rejected: false,
        needs_review: true,
      };
      const viewport = options.captureReviewViewport();

      options.records.value.splice(
        Math.min(index, neighborIndex),
        2,
        ...(direction === "previous" ? [updatedNeighbor, target] : [target, updatedNeighbor]),
      );
      options.selectedRecord.value = target;
      options.selectedRecordId.value = id;
      await options.restoreReviewViewport(viewport, { record: true });

      options.queueRecordRequest(
        [id, neighbor.record_id],
        ["record boundary"],
        async () => {
          const result = await corpusBuilderApi.sliceRecord(
            options.currentBuild.value!.build_id,
            id,
            direction,
            offset,
            Number(beforeSelected.record_revision || 1),
            keepEnd,
          );
          boundarySliceOpen.value = false;
          await options.refreshBuild();
          await options.refreshRecords(false, result.record.record_id);
          await options.restoreReviewViewport(viewport, { record: true });
          options.setMessage(options.t("pdf_corpus.slice_done"));
        },
        () => {
          options.records.value = before;
          options.selectedRecord.value = beforeSelected;
          options.selectedRecordId.value = beforeSelected.record_id;
        },
        false,
      );
      return;
    }

    if (direction !== "new" || keepEnd === undefined) return;
    const index = options.records.value.findIndex((row) => row.record_id === id);
    const following = options.records.value[index + 1];
    const targetText = String(options.selectedRecord.value.text || "");
    if (
      index < 0 ||
      !following ||
      offset <= 0 ||
      offset >= keepEnd ||
      keepEnd > targetText.length
    ) {
      return;
    }

    const prefix = targetText.slice(0, offset).trim();
    const retained = targetText.slice(offset, keepEnd).trim();
    const suffix = targetText.slice(keepEnd).trim();
    if (!prefix || !retained || !suffix) return;

    const before = options.records.value.slice();
    const beforeTotal = options.recordTotal.value;
    const beforeSelected = options.selectedRecord.value;
    const provisionalId = `${id}-slice-pending`;
    const revised = (row: CorpusRecord, text: string, revision: number): CorpusRecord => ({
      ...row,
      text,
      text_length: text.length,
      record_revision: revision,
      review_disposition: "pending",
      accepted: false,
      rejected: false,
      needs_review: true,
    });
    const target = revised(
      options.selectedRecord.value,
      prefix,
      Number(options.selectedRecord.value.record_revision || 1) + 1,
    );
    const created = revised(
      { ...options.selectedRecord.value, record_id: provisionalId },
      retained,
      1,
    );
    const updatedFollowing = revised(
      following,
      `${suffix}\n\n${String(following.text || "").trim()}`.trim(),
      Number(following.record_revision || 1) + 1,
    );
    const viewport = options.captureReviewViewport();

    options.records.value.splice(index, 2, target, created, updatedFollowing);
    options.recordTotal.value = beforeTotal + 1;
    options.selectedRecord.value = created;
    options.selectedRecordId.value = provisionalId;
    await options.restoreReviewViewport(viewport, { record: true });

    options.queueRecordRequest(
      [id, provisionalId, following.record_id],
      ["record boundary"],
      async () => {
        const result = await corpusBuilderApi.sliceRecord(
          options.currentBuild.value!.build_id,
          id,
          "new",
          offset,
          Number(beforeSelected.record_revision || 1),
          keepEnd,
        );
        boundarySliceOpen.value = false;
        await options.refreshBuild();
        await options.refreshRecords(
          false,
          result.new_record?.record_id || result.record.record_id,
        );
        await options.restoreReviewViewport(viewport, { record: true });
        options.setMessage(options.t("pdf_corpus.slice_done"));
      },
      () => {
        options.records.value = before;
        options.recordTotal.value = beforeTotal;
        options.selectedRecord.value = beforeSelected;
        options.selectedRecordId.value = beforeSelected.record_id;
      },
      false,
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
    sliceRecord,
    adjudicateBoundary,
  };
}
