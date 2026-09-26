/* Copyright 2026 Aaron John Schlosser, PhD. */
import { nextTick, type ComputedRef, type Ref } from "vue";
import { corpusBuilderApi, type CorpusBuild, type CorpusRecord } from "../../../api/corpus";
import type { ReviewQueue } from "../../../types/corpus";
import type { ReviewViewport } from "./useCorpusReviewWorkspace";

type MessageTone = "error" | "notice";

interface CorpusReviewDecisionsOptions {
  currentBuild: Ref<CorpusBuild | null>;
  selectedRecord: Ref<CorpusRecord | null>;
  selectedRecordId: Ref<string>;
  records: Ref<CorpusRecord[]>;
  recordTotal: Ref<number>;
  reviewQueue: Ref<ReviewQueue>;
  recordQuery: Ref<string>;
  selectedReviewIds: Ref<Set<string>>;
  justProcessedRecordId: Ref<string>;
  bulkActionFeedback: Ref<string>;
  busy: Ref<string>;
  focusView: Ref<boolean>;
  reviewInspectorTab: Ref<"metadata" | "evidence" | "source">;
  reviewLocked: ComputedRef<boolean>;
  selectedMetadataBlocked: ComputedRef<boolean>;
  readyCount: ComputedRef<number>;
  issueCount: ComputedRef<number>;
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
  applyAuthoritativeRecord: (record: CorpusRecord, build?: CorpusBuild | null) => void;
  syncBuildInRail: (build: CorpusBuild) => void;
  selectRecord: (record: CorpusRecord) => void;
  advanceFrom: (recordId: string) => Promise<void>;
  refreshBuild: () => Promise<void>;
  refreshRecords: (reset?: boolean, preferredId?: string) => Promise<void>;
  focusFirstMetadataBlocker: () => void;
  setMessage: (message: string, tone?: MessageTone) => void;
  t: (key: string, fallback?: string) => string;
  tf: (key: string, values: Record<string, string | number>) => string;
}

export function useCorpusReviewDecisions(options: CorpusReviewDecisionsOptions) {
  async function setDisposition(disposition: "pending" | "accepted" | "rejected") {
    if (options.reviewLocked.value) {
      options.setMessage(options.t("pdf_corpus.review_preparing_help"));
      return;
    }
    if (!options.currentBuild.value || !options.selectedRecord.value) return;

    const id = options.selectedRecord.value.record_id;
    if (disposition !== "pending") options.justProcessedRecordId.value = id;
    const viewport = options.captureReviewViewport();

    if (disposition !== "accepted") {
      const buildId = options.currentBuild.value.build_id;
      const expectedRevision = Number(options.selectedRecord.value.record_revision || 1);
      const row: CorpusRecord = {
        ...options.selectedRecord.value,
        review_disposition: disposition,
        accepted: false,
        rejected: disposition === "rejected",
        needs_review: disposition === "pending",
        record_revision: expectedRevision + 1,
      } as CorpusRecord;
      const index = options.records.value.findIndex((item) => item.record_id === id);

      if (options.reviewQueue.value !== "all" && disposition === "rejected") {
        if (index >= 0) options.records.value.splice(index, 1);
        options.recordTotal.value = Math.max(0, options.recordTotal.value - 1);
      } else if (index >= 0) {
        options.records.value.splice(index, 1, row);
      }

      options.selectedRecord.value = row;
      await options.restoreReviewViewport(viewport, { record: true, inspector: true });
      options.queueRecordRequest(id, ["review disposition"], async (rebase) => {
        if (disposition === "pending") {
          const result = await corpusBuilderApi.disposition(
            buildId,
            id,
            "pending",
            "",
            rebase ? undefined : expectedRevision,
          );
          options.applyAuthoritativeRecord(result);
          return result;
        }
        const result = await corpusBuilderApi.reviewDecision(
          buildId,
          id,
          "rejected",
          "",
          rebase ? undefined : expectedRevision,
          options.reviewQueue.value,
        );
        options.applyAuthoritativeRecord(result.record, result.build);
        return result;
      });
      return;
    }

    const buildId = options.currentBuild.value.build_id;
    const beforeRecords = options.records.value.slice();
    const beforeTotal = options.recordTotal.value;
    const beforeSelected = options.selectedRecord.value;
    const beforeSelectedId = options.selectedRecordId.value;
    const expectedRevision = Number(options.selectedRecord.value.record_revision || 1);
    const optimistic: CorpusRecord = {
      ...options.selectedRecord.value,
      review_disposition: "accepted",
      accepted: true,
      rejected: false,
      needs_review: false,
      review_reason: "",
      record_revision: expectedRevision + 1,
    };
    const optimisticIndex = options.records.value.findIndex((row) => row.record_id === id);

    const currentRemainsVisible =
      options.reviewQueue.value === "all" || options.reviewQueue.value === disposition;
    if (currentRemainsVisible) {
      if (optimisticIndex >= 0) options.records.value.splice(optimisticIndex, 1, optimistic);
    } else if (optimisticIndex >= 0) {
      options.records.value.splice(optimisticIndex, 1);
      options.recordTotal.value = Math.max(0, options.recordTotal.value - 1);
    }

    options.selectedRecord.value = optimistic;
    const nextLocal = currentRemainsVisible
      ? options.records.value[optimisticIndex + 1] || options.records.value[optimisticIndex - 1]
      : options.records.value[optimisticIndex] || options.records.value[optimisticIndex - 1];
    if (nextLocal && nextLocal.record_id !== id) options.selectRecord(nextLocal);
    await options.restoreReviewViewport(viewport, { record: true, inspector: true });

    options.queueRecordRequest(
      id,
      ["review disposition"],
      async (rebase) => {
        const result = await corpusBuilderApi.reviewDecision(
          buildId,
          id,
          disposition,
          "",
          rebase ? undefined : expectedRevision,
          options.reviewQueue.value,
        );
        options.currentBuild.value = result.build;
        options.syncBuildInRail(result.build);

        if (result.blocked) {
          options.records.value = beforeRecords;
          options.recordTotal.value = beforeTotal;
          options.selectedRecord.value = result.record;
          options.selectedRecordId.value = id;
          const idx = options.records.value.findIndex((row) => row.record_id === id);
          if (idx >= 0) options.records.value.splice(idx, 1, result.record);

          if (result.blocker === "source_problem") {
            options.reviewInspectorTab.value = "source";
            options.reviewQueue.value = "source";
            options.setMessage(options.t("pdf_corpus.accept_blocked_source"), "error");
          } else {
            options.reviewInspectorTab.value = "metadata";
            const fields = (result.blocking_fields || [])
              .map((field) => options.t(`record.${field}`, field.replace(/_/g, " ")))
              .join(", ");
            options.setMessage(options.tf("pdf_corpus.accept_blocked_metadata", { fields }));
            await nextTick();
            options.focusFirstMetadataBlocker();
          }
        } else {
          const idx = options.records.value.findIndex((row) => row.record_id === id);
          if (options.reviewQueue.value === "all" || options.reviewQueue.value === disposition) {
            if (idx >= 0) options.records.value.splice(idx, 1, result.record);
          }
          if (result.next_record) {
            const existing = options.records.value.find(
              (row) => row.record_id === result.next_record?.record_id,
            );
            options.selectRecord(existing || result.next_record);
          } else if (options.selectedRecordId.value === id) {
            await options.advanceFrom(id);
          }
          // Nothing left to advance to (the last record in the queue): leave
          // Focus View rather than sitting on an already-decided record.
          if (options.selectedRecordId.value === id || !options.selectedRecordId.value) {
            options.focusView.value = false;
          }
          options.setMessage(options.t("pdf_corpus.accepted_notice"));
        }

        await options.restoreReviewViewport(viewport, { record: true, inspector: true });
      },
      async () => {
        options.records.value = beforeRecords;
        options.recordTotal.value = beforeTotal;
        options.selectedRecord.value = beforeSelected;
        options.selectedRecordId.value = beforeSelectedId;
        await options.restoreReviewViewport(viewport);
      },
      false,
    );
  }

  async function attemptAccept() {
    if (options.reviewLocked.value) {
      options.setMessage(options.t("pdf_corpus.review_preparing_help"));
      return;
    }
    if (!options.selectedRecord.value) return;
    if (options.selectedRecord.value.accepted) {
      await setDisposition("pending");
      return;
    }
    await setDisposition("accepted");
  }

  async function toggleAccept() {
    await attemptAccept();
  }

  async function acceptFromFocus() {
    if (options.selectedMetadataBlocked.value) {
      options.focusView.value = false;
      await nextTick();
    }
    await attemptAccept();
  }

  async function rejectRecord() {
    await setDisposition("rejected");
  }

  async function skipRecord() {
    if (!options.selectedRecord.value) return;
    await options.advanceFrom(options.selectedRecord.value.record_id);
  }

  async function acceptCleanRecords() {
    if (options.reviewLocked.value) {
      options.setMessage(options.t("pdf_corpus.review_preparing_help"));
      return;
    }
    if (!options.currentBuild.value) return;
    const clean = options.readyCount.value;
    if (clean < 1) {
      options.setMessage(options.t("pdf_corpus.no_clean_records"));
      return;
    }

    const viewport = options.captureReviewViewport();
    if (!window.confirm(options.tf("pdf_corpus.accept_clean_confirm", { count: clean }))) return;
    options.busy.value = "bulk";
    try {
      const result = await corpusBuilderApi.bulkDisposition(
        options.currentBuild.value.build_id,
        "accepted",
        "ready",
        "",
      );
      await options.refreshBuild();
      options.reviewQueue.value = options.issueCount.value > 0 ? "issues" : "all";
      await nextTick();
      await options.refreshRecords(true);
      await options.restoreReviewViewport(viewport, { record: true, inspector: true });
      options.bulkActionFeedback.value =
        result.changed > 0
          ? options.tf("pdf_corpus.accept_clean_done", { count: result.changed })
          : options.t("pdf_corpus.accept_clean_none_changed");
      options.setMessage(options.bulkActionFeedback.value);
    } catch (exc) {
      await options.restoreReviewViewport(viewport);
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function bulkDisposition(disposition: "accepted" | "rejected") {
    if (!options.currentBuild.value) return;
    const recordIds = Array.from(options.selectedReviewIds.value);
    const count = recordIds.length;
    if (!count) {
      options.setMessage(options.t("pdf_corpus.select_records_first"));
      return;
    }

    const viewport = options.captureReviewViewport();
    const verb =
      disposition === "accepted"
        ? options.t("pdf_corpus.accept_selected")
        : options.t("pdf_corpus.reject_selected");
    if (
      !window.confirm(
        options.tf("pdf_corpus.bulk_confirm", {
          action: verb,
          count,
        }),
      )
    ) {
      return;
    }

    options.busy.value = "bulk";
    try {
      const result = await corpusBuilderApi.bulkDisposition(
        options.currentBuild.value.build_id,
        disposition,
        options.reviewQueue.value,
        options.recordQuery.value,
        "",
        recordIds,
      );
      options.selectedReviewIds.value = new Set();
      await options.refreshBuild();

      if (disposition === "accepted" && Number(result.blocked_metadata || 0) > 0) {
        options.reviewQueue.value = "metadata";
        options.recordQuery.value = "";
        await nextTick();
        await options.refreshRecords(true, result.blocked_record_ids?.[0] || "");
        options.reviewInspectorTab.value = "metadata";
      } else {
        await options.refreshRecords(true);
      }

      await options.restoreReviewViewport(viewport, { record: true, inspector: true });
      options.bulkActionFeedback.value = result.blocked_metadata
        ? options.tf("pdf_corpus.bulk_done_metadata_blocked", {
            count: result.changed,
            blocked: result.blocked_metadata,
          })
        : options.tf("pdf_corpus.bulk_done", { count: result.changed });
      options.setMessage(options.bulkActionFeedback.value);
    } catch (exc) {
      await options.restoreReviewViewport(viewport);
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function restoreAllRejected() {
    if (!options.currentBuild.value) return;
    options.busy.value = "bulk-restore";
    try {
      const result = await corpusBuilderApi.bulkDisposition(
        options.currentBuild.value.build_id,
        "pending",
        "rejected",
        "",
      );
      await options.refreshBuild();
      options.reviewQueue.value = "all";
      options.recordQuery.value = "";
      options.selectedRecordId.value = "";
      options.selectedRecord.value = null;
      await nextTick();
      await options.refreshRecords(true);
      options.setMessage(
        options.tf("pdf_corpus.restored_rejected_count", { count: result.changed }),
      );
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function undoReview() {
    if (!options.currentBuild.value) return;
    const viewport = options.captureReviewViewport();
    options.busy.value = "record";
    try {
      const result = await corpusBuilderApi.undoReview(options.currentBuild.value.build_id);
      await options.refreshBuild();
      await options.refreshRecords(true, result.selected_record_id || "");
      await options.restoreReviewViewport(viewport, { record: true });
      options.setMessage(options.t("pdf_corpus.undo_done"));
    } catch (exc) {
      await options.restoreReviewViewport(viewport);
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function redoReview() {
    if (!options.currentBuild.value) return;
    const viewport = options.captureReviewViewport();
    options.busy.value = "record";
    try {
      const result = await corpusBuilderApi.redoReview(options.currentBuild.value.build_id);
      await options.refreshBuild();
      await options.refreshRecords(true, result.selected_record_id || "");
      await options.restoreReviewViewport(viewport, { record: true });
      options.setMessage(options.t("pdf_corpus.redo_done"));
    } catch (exc) {
      await options.restoreReviewViewport(viewport);
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  return {
    setDisposition,
    attemptAccept,
    toggleAccept,
    acceptFromFocus,
    rejectRecord,
    skipRecord,
    acceptCleanRecords,
    bulkDisposition,
    restoreAllRejected,
    undoReview,
    redoReview,
  };
}
