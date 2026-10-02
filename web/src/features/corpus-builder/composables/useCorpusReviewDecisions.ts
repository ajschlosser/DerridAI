/* Copyright 2026 Aaron John Schlosser, PhD. */
import { nextTick, type ComputedRef, type Ref } from "vue";
import { corpusBuilderApi, type CorpusBuild, type CorpusRecord } from "../../../api/corpus";
import type { ReviewQueue } from "../../../types/corpus";
import type { CorpusQueueRow } from "../api/reviewReads";
import { queueRowFromRecord } from "../domain/queueRows";
import type { ReviewTarget } from "./useCorpusReviewRecords";
import type { ReviewViewport } from "./useCorpusReviewWorkspace";

type MessageTone = "error" | "notice";

interface CorpusReviewDecisionsOptions {
  currentBuild: Ref<CorpusBuild | null>;
  selectedRecord: Ref<CorpusRecord | null>;
  selectedRecordId: Ref<string>;
  queueRows: Ref<CorpusQueueRow[]>;
  recordTotal: Ref<number>;
  reviewQueue: Ref<ReviewQueue>;
  recordQuery: Ref<string>;
  recordOffset?: Ref<number>;
  beforeDecision?: () => Promise<boolean>;
  getSelectionVersion?: () => number;
  selectedReviewIds: Ref<Set<string>>;
  justProcessedRecordId: Ref<string>;
  bulkActionFeedback: Ref<string>;
  busy: Ref<string>;
  focusView: Ref<boolean>;
  reviewInspectorTab: Ref<"metadata" | "evidence" | "source" | "semantic">;
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
  selectRecord: (target: ReviewTarget) => Promise<void> | void;
  advanceFrom: (recordId: string, removedIndex?: number) => Promise<void>;
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
    if (options.beforeDecision && !(await options.beforeDecision())) return;
    if (!options.currentBuild.value || !options.selectedRecord.value) return;

    const id = options.selectedRecord.value.record_id;
    if (disposition !== "pending") options.justProcessedRecordId.value = id;
    const viewport = options.captureReviewViewport();

    if (disposition === "pending") {
      const buildId = options.currentBuild.value.build_id;
      const expectedRevision = Number(options.selectedRecord.value.record_revision || 1);
      const row: CorpusRecord = {
        ...options.selectedRecord.value,
        review_disposition: disposition,
        accepted: false,
        rejected: false,
        needs_review: disposition === "pending",
        record_revision: expectedRevision + 1,
      } as CorpusRecord;
      const index = options.queueRows.value.findIndex((item) => item.record_id === id);

      if (index >= 0) {
        options.queueRows.value.splice(index, 1, queueRowFromRecord(row));
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
    const beforeSelected = options.selectedRecord.value;
    const beforeSelectedId = options.selectedRecordId.value;
    const decisionQueue = options.reviewQueue.value;
    const decisionQuery = options.recordQuery.value;
    const decisionOffset = options.recordOffset?.value;
    const expectedRevision = Number(options.selectedRecord.value.record_revision || 1);
    const optimistic: CorpusRecord = {
      ...options.selectedRecord.value,
      review_disposition: disposition,
      accepted: disposition === "accepted",
      rejected: disposition === "rejected",
      needs_review: false,
      review_reason: "",
      record_revision: expectedRevision + 1,
    };
    const optimisticIndex = options.queueRows.value.findIndex((row) => row.record_id === id);
    const hasMorePages =
      options.recordOffset != null &&
      options.recordOffset.value + options.queueRows.value.length < options.recordTotal.value;

    const currentRemainsVisible =
      options.reviewQueue.value === "all" || options.reviewQueue.value === disposition;
    if (currentRemainsVisible) {
      if (optimisticIndex >= 0)
        options.queueRows.value.splice(optimisticIndex, 1, queueRowFromRecord(optimistic));
    } else if (optimisticIndex >= 0) {
      options.queueRows.value.splice(optimisticIndex, 1);
      options.recordTotal.value = Math.max(0, options.recordTotal.value - 1);
    }

    options.selectedRecord.value = optimistic;
    const nextLocal = currentRemainsVisible
      ? options.queueRows.value[optimisticIndex + 1] ||
        (!hasMorePages ? options.queueRows.value[optimisticIndex - 1] : undefined)
      : options.queueRows.value[optimisticIndex] ||
        (!hasMorePages ? options.queueRows.value[optimisticIndex - 1] : undefined);
    if (nextLocal && nextLocal.record_id !== id) void options.selectRecord(nextLocal);
    await options.restoreReviewViewport(viewport, { record: true, inspector: true });
    const expectedSelection = nextLocal?.record_id || id;
    const expectedSelectionVersion = options.getSelectionVersion?.();

    function sameContext() {
      return (
        options.currentBuild.value?.build_id === buildId &&
        options.reviewQueue.value === decisionQueue &&
        options.recordQuery.value === decisionQuery &&
        options.recordOffset?.value === decisionOffset
      );
    }
    function stillFollowingDecision() {
      return (
        sameContext() &&
        options.getSelectionVersion?.() === expectedSelectionVersion &&
        [id, expectedSelection].includes(options.selectedRecordId.value)
      );
    }
    function restoreAffectedRow(record: CorpusRecord) {
      if (!sameContext()) return;
      const index = options.queueRows.value.findIndex((row) => row.record_id === id);
      if (index >= 0) options.queueRows.value.splice(index, 1, queueRowFromRecord(record));
      else {
        options.queueRows.value.splice(Math.max(0, optimisticIndex), 0, queueRowFromRecord(record));
        options.recordTotal.value += 1;
      }
    }

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
          decisionQueue,
        );
        if (options.currentBuild.value?.build_id !== buildId) return;
        options.currentBuild.value = result.build;
        options.syncBuildInRail(result.build);
        const followingDecision = stillFollowingDecision();

        if (result.blocked) {
          restoreAffectedRow(result.record);
          if (!stillFollowingDecision()) {
            options.setMessage(options.t("pdf_corpus.accept_blocked_metadata"));
            return;
          }
          options.selectedRecord.value = result.record;
          options.selectedRecordId.value = id;
          const idx = options.queueRows.value.findIndex((row) => row.record_id === id);
          if (idx >= 0) options.queueRows.value.splice(idx, 1, queueRowFromRecord(result.record));

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
          const idx = options.queueRows.value.findIndex((row) => row.record_id === id);
          if (options.reviewQueue.value === "all" || options.reviewQueue.value === disposition) {
            if (idx >= 0) options.queueRows.value.splice(idx, 1, queueRowFromRecord(result.record));
          }
          if (hasMorePages && !nextLocal && followingDecision) {
            await options.advanceFrom(id, currentRemainsVisible ? undefined : optimisticIndex);
          } else if (
            result.next_record &&
            stillFollowingDecision() &&
            options.selectedRecordId.value === id
          ) {
            // The server returns the next Record in full: open it without another read.
            await options.selectRecord(result.next_record);
          } else if (stillFollowingDecision() && options.selectedRecordId.value === id) {
            await options.advanceFrom(id);
          }
          // Nothing left to advance to (the last record in the queue): leave
          // Focus View rather than sitting on an already-decided record.
          if (
            followingDecision &&
            (options.selectedRecordId.value === id || !options.selectedRecordId.value)
          ) {
            options.focusView.value = false;
          }
          options.setMessage(
            options.t(
              disposition === "accepted"
                ? "pdf_corpus.accepted_notice"
                : "pdf_corpus.rejected_notice",
            ),
          );
        }

        if (followingDecision)
          await options.restoreReviewViewport(viewport, { record: true, inspector: true });
      },
      async () => {
        restoreAffectedRow(beforeSelected);
        if (stillFollowingDecision()) {
          options.selectedRecord.value = beforeSelected;
          options.selectedRecordId.value = beforeSelectedId;
          await options.restoreReviewViewport(viewport);
        }
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
    rejectRecord,
    skipRecord,
    acceptCleanRecords,
    bulkDisposition,
    restoreAllRejected,
    undoReview,
    redoReview,
  };
}
