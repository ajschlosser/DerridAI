/* Copyright 2026 Aaron John Schlosser, PhD. */
import { nextTick, type ComputedRef, type Ref } from "vue";
import type { CorpusBuild, CorpusRecord } from "../../../api/corpus";
import type { ReviewQueue } from "../../../types/corpus";
import { firstValidationRecordId } from "../domain/publicationReadiness";

interface CorpusReviewNavigationOptions {
  currentBuild: Ref<CorpusBuild | null>;
  records: Ref<CorpusRecord[]>;
  recordTotal: Ref<number>;
  recordOffset: Ref<number>;
  selectedRecord: Ref<CorpusRecord | null>;
  selectedRecordIndex: ComputedRef<number>;
  reviewQueue: Ref<ReviewQueue>;
  recordQuery: Ref<string>;
  focusView: Ref<boolean>;
  focusHistory: Ref<string[]>;
  focusHistoryOffsets: Ref<number[]>;
  focusHistoryIndex: Ref<number>;
  recordListEl: Ref<HTMLElement | null>;
  pageSize: number;
  refreshRecords: (reset?: boolean, preferredId?: string) => Promise<void>;
  selectRecord: (record: CorpusRecord) => void;
}

export function useCorpusReviewNavigation(options: CorpusReviewNavigationOptions) {
  function pushFocusHistory(id: string) {
    if (!id || options.focusHistory.value[options.focusHistoryIndex.value] === id) return;
    options.focusHistory.value = options.focusHistory.value.slice(
      0,
      options.focusHistoryIndex.value + 1,
    );
    options.focusHistoryOffsets.value = options.focusHistoryOffsets.value.slice(
      0,
      options.focusHistoryIndex.value + 1,
    );
    options.focusHistory.value.push(id);
    options.focusHistoryOffsets.value.push(options.recordOffset.value);
    options.focusHistoryIndex.value = options.focusHistory.value.length - 1;
  }

  function openFocusView() {
    if (!options.selectedRecord.value) return;
    options.focusView.value = true;
    pushFocusHistory(options.selectedRecord.value.record_id);
  }

  async function focusHistoryMove(delta: number) {
    const next = options.focusHistoryIndex.value + delta;
    if (next < 0 || next >= options.focusHistory.value.length) return;
    options.focusHistoryIndex.value = next;
    const id = options.focusHistory.value[next];
    const targetOffset = options.focusHistoryOffsets.value[next] ?? options.recordOffset.value;
    const local =
      targetOffset === options.recordOffset.value
        ? options.records.value.find((row) => row.record_id === id)
        : undefined;
    if (local) {
      options.selectRecord(local);
      return;
    }
    options.recordOffset.value = targetOffset;
    await options.refreshRecords(false, id);
  }

  async function focusQueueMove(delta: number) {
    const index = options.selectedRecordIndex.value;
    if (index >= 0) {
      const next = options.records.value[index + delta];
      if (next) {
        options.selectRecord(next);
        pushFocusHistory(next.record_id);
        return;
      }
    }

    if (delta > 0 && options.recordOffset.value + options.pageSize < options.recordTotal.value) {
      options.recordOffset.value += options.pageSize;
      await options.refreshRecords(false);
      const next = options.records.value[0];
      if (next) {
        options.selectRecord(next);
        pushFocusHistory(next.record_id);
      }
      return;
    }

    if (delta < 0 && options.recordOffset.value > 0) {
      options.recordOffset.value = Math.max(0, options.recordOffset.value - options.pageSize);
      await options.refreshRecords(false);
      const next = options.records.value[options.records.value.length - 1];
      if (next) {
        options.selectRecord(next);
        pushFocusHistory(next.record_id);
      }
    }
  }

  async function navigateToQueueRecord(recordId: string) {
    const existing = options.records.value.find((row) => row.record_id === recordId);
    if (existing) {
      options.selectRecord(existing);
      return;
    }
    await options.refreshRecords(true, recordId);
  }

  async function advanceFrom(recordId: string) {
    const index = options.records.value.findIndex((row) => row.record_id === recordId);
    const next = options.records.value[index + 1] || options.records.value[index - 1];
    if (next) {
      options.selectRecord(next);
      return;
    }
    if (options.recordOffset.value + options.pageSize < options.recordTotal.value) {
      options.recordOffset.value += options.pageSize;
      await options.refreshRecords();
      return;
    }
    await options.refreshRecords();
  }

  async function openQueue(queue: ReviewQueue, preferredId = "") {
    options.reviewQueue.value = queue;
    options.recordQuery.value = "";
    await nextTick();
    await options.refreshRecords(true, preferredId);
    await nextTick();
    options.recordListEl.value?.focus({ preventScroll: true });
  }

  async function reviewMetadataRecord(recordId: string) {
    options.reviewQueue.value = "metadata";
    options.recordQuery.value = recordId;
    await nextTick();
    await options.refreshRecords(true, recordId);
    if (options.selectedRecord.value?.record_id === recordId) {
      options.focusView.value = false;
    }
  }

  async function openMetadataIssueQueue() {
    const first = options.currentBuild.value?.metadata_issue_summary?.records?.[0]?.record_id;
    await openQueue("metadata", first ? String(first) : "");
  }

  async function openValidationIssueQueue() {
    await openQueue("issues", firstValidationRecordId(options.currentBuild.value));
  }

  async function openRejectedQueue() {
    await openQueue("rejected");
  }

  async function openAllReviewQueue() {
    await openQueue("all");
  }

  async function openSourceIssueQueue() {
    await openQueue("source");
  }

  async function previousPage() {
    if (options.recordOffset.value <= 0) return;
    options.recordOffset.value = Math.max(0, options.recordOffset.value - options.pageSize);
    await options.refreshRecords();
  }

  async function nextPage() {
    if (options.recordOffset.value + options.pageSize >= options.recordTotal.value) {
      return;
    }
    options.recordOffset.value += options.pageSize;
    await options.refreshRecords();
  }

  return {
    openFocusView,
    pushFocusHistory,
    focusHistoryMove,
    focusQueueMove,
    navigateToQueueRecord,
    advanceFrom,
    reviewMetadataRecord,
    openMetadataIssueQueue,
    openValidationIssueQueue,
    openRejectedQueue,
    openAllReviewQueue,
    openSourceIssueQueue,
    previousPage,
    nextPage,
  };
}
