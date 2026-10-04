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

import { nextTick, type ComputedRef, type Ref } from "vue";
import { activeValueEditor } from "../../../domain/focus";
import type { CorpusBuild, CorpusRecord } from "../../../api/corpus";
import type { ReviewQueue } from "../../../types/corpus";
import type { CorpusQueueRow } from "../api/reviewReads";
import { firstValidationRecordId } from "../domain/publicationReadiness";
import type { ReviewTarget } from "./useCorpusReviewRecords";

interface CorpusReviewNavigationOptions {
  reviewRequested: Ref<boolean>;
  currentBuild: Ref<CorpusBuild | null>;
  queueRows: Ref<CorpusQueueRow[]>;
  recordTotal: Ref<number>;
  recordOffset: Ref<number>;
  selectedRecord: Ref<CorpusRecord | null>;
  selectedRecordId: Ref<string>;
  selectedRecordIndex: ComputedRef<number>;
  reviewQueue: Ref<ReviewQueue>;
  recordQuery: Ref<string>;
  focusView: Ref<boolean>;
  focusHistory: Ref<string[]>;
  focusHistoryOffsets: Ref<number[]>;
  focusHistoryIndex: Ref<number>;
  recordListEl: Ref<HTMLElement | null>;
  pageSize: number;
  movePage?: (direction: "forward" | "backward") => Promise<void>;
  hasNextPage?: Ref<boolean>;
  hasPreviousPage?: Ref<boolean>;
  refreshRecords: (reset?: boolean, preferredId?: string) => Promise<void>;
  selectRecord: (target: ReviewTarget) => Promise<void> | void;
  setFilters?: (queue: ReviewQueue, query: string) => void;
  beforeNavigate?: () => Promise<boolean>;
}

export function useCorpusReviewNavigation(options: CorpusReviewNavigationOptions) {
  async function loadAdjacentPage(delta: number) {
    options.recordOffset.value = Math.max(
      0,
      options.recordOffset.value + (delta > 0 ? options.pageSize : -options.pageSize),
    );
    if (options.movePage) await options.movePage(delta > 0 ? "forward" : "backward");
    else await options.refreshRecords();
  }

  function canMovePage(delta: number) {
    return delta > 0
      ? (options.hasNextPage?.value ??
          options.recordOffset.value + options.pageSize < options.recordTotal.value)
      : (options.hasPreviousPage?.value ?? options.recordOffset.value > 0);
  }
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
    if (options.beforeNavigate && !(await options.beforeNavigate())) return;
    const next = options.focusHistoryIndex.value + delta;
    if (next < 0 || next >= options.focusHistory.value.length) return;
    options.focusHistoryIndex.value = next;
    const id = options.focusHistory.value[next];
    const targetOffset = options.focusHistoryOffsets.value[next] ?? options.recordOffset.value;
    const local =
      targetOffset === options.recordOffset.value
        ? options.queueRows.value.find((row) => row.record_id === id)
        : undefined;
    if (local) {
      await options.selectRecord(local);
      return;
    }
    options.recordOffset.value = targetOffset;
    await options.refreshRecords(false, id);
  }

  async function focusQueueMove(delta: number) {
    if (options.beforeNavigate && !(await options.beforeNavigate())) return;
    const index = options.selectedRecordIndex.value;
    if (index >= 0) {
      const next = options.queueRows.value[index + delta];
      if (next) {
        void options.selectRecord(next);
        pushFocusHistory(next.record_id);
        return;
      }
    }

    if (delta > 0 && canMovePage(delta)) {
      await loadAdjacentPage(delta);
      const next = options.queueRows.value[0];
      if (next) {
        void options.selectRecord(next);
        pushFocusHistory(next.record_id);
      }
      return;
    }

    if (delta < 0 && canMovePage(delta)) {
      await loadAdjacentPage(delta);
      const next = options.queueRows.value[options.queueRows.value.length - 1];
      if (next) {
        void options.selectRecord(next);
        pushFocusHistory(next.record_id);
      }
    }
  }

  async function navigateToQueueRecord(recordId: string) {
    const existing = options.queueRows.value.find((row) => row.record_id === recordId);
    if (existing) {
      await options.selectRecord(existing);
      return;
    }
    await options.refreshRecords(true, recordId);
  }

  async function advanceFrom(recordId: string, removedIndex?: number) {
    if (options.beforeNavigate && !(await options.beforeNavigate())) return;
    const index = options.queueRows.value.findIndex((row) => row.record_id === recordId);
    const next = options.queueRows.value[index >= 0 ? index + 1 : (removedIndex ?? 0)];
    if (next) {
      await options.selectRecord(next);
      return;
    }
    if (
      index < 0 &&
      removedIndex != null &&
      options.recordOffset.value + options.queueRows.value.length < options.recordTotal.value
    ) {
      await options.refreshRecords();
      const backfilled = options.queueRows.value[removedIndex];
      if (backfilled) await options.selectRecord(backfilled);
      return;
    }
    if (canMovePage(1)) {
      await loadAdjacentPage(1);
      return;
    }
    const previous = options.queueRows.value[index - 1];
    if (previous) {
      await options.selectRecord(previous);
      return;
    }
    await options.refreshRecords();
  }

  async function openQueue(queue: ReviewQueue, preferredId = "", recordQuery = "") {
    if (options.beforeNavigate && !(await options.beforeNavigate())) return;
    // Queue navigation is an explicit context change. Clear the previous
    // selection before refreshing so refreshRecords can select the first row
    // in the destination queue instead of preserving a stale record that no
    // longer belongs to the visible result set.
    options.selectedRecordId.value = "";
    options.selectedRecord.value = null;
    options.focusView.value = false;
    options.reviewRequested.value = true;
    if (options.setFilters) options.setFilters(queue, recordQuery);
    else {
      options.reviewQueue.value = queue;
      options.recordQuery.value = recordQuery;
    }
    await nextTick();
    await options.refreshRecords(true, preferredId);
    await nextTick();
    if (!activeValueEditor()) options.recordListEl.value?.focus({ preventScroll: true });
  }

  async function reviewMetadataRecord(recordId: string) {
    await openQueue("metadata", recordId, recordId);
    if (options.selectedRecord.value?.record_id === recordId) {
      options.focusView.value = false;
    }
  }

  async function openMetadataIssueQueue() {
    const first = options.currentBuild.value?.metadata_issue_summary?.records?.[0]?.record_id;
    const recordId = first ? String(first) : "";
    await openQueue("metadata", recordId, recordId);
  }

  async function openValidationIssueQueue(targetRecordId = "") {
    const recordId = targetRecordId || firstValidationRecordId(options.currentBuild.value);
    if (recordId) {
      // Validation findings are not necessarily review-queue findings. Target
      // the canonical record directly rather than assuming it also belongs to
      // the generic Issues queue, which can otherwise produce a blank view.
      await openQueue("all", recordId, recordId);
      return;
    }
    await openQueue("issues");
  }

  async function openTopologyIssueQueue() {
    await openQueue("topology");
  }

  async function openIssueQueue() {
    await openQueue("issues");
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

  async function changePage(offset: number) {
    if (options.beforeNavigate && !(await options.beforeNavigate())) return;
    // A page change is a visible queue-context change. Do not preserve the Record
    // selected on the previous page: refreshRecords would otherwise issue a second
    // full-Record request for an item that is no longer visible before the user can
    // interact with the destination page.
    options.selectedRecordId.value = "";
    options.selectedRecord.value = null;
    options.recordOffset.value = offset;
    await options.refreshRecords();
  }

  async function previousPage() {
    if (!canMovePage(-1)) return;
    if (options.beforeNavigate && !(await options.beforeNavigate())) return;
    options.selectedRecordId.value = "";
    options.selectedRecord.value = null;
    await loadAdjacentPage(-1);
  }

  async function nextPage() {
    if (!canMovePage(1)) return;
    if (options.beforeNavigate && !(await options.beforeNavigate())) return;
    options.selectedRecordId.value = "";
    options.selectedRecord.value = null;
    await loadAdjacentPage(1);
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
    openTopologyIssueQueue,
    openIssueQueue,
    openRejectedQueue,
    openAllReviewQueue,
    openSourceIssueQueue,
    previousPage,
    nextPage,
    changePage,
  };
}
