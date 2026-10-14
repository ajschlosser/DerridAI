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

import { computed, nextTick, ref, type Ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { useCorpusReviewNavigation } from "../../src/features/corpus-builder/composables/useCorpusReviewNavigation";

function record(id: string) {
  return { record_id: id } as any;
}

function setup(
  beforeNavigate?: () => Promise<boolean>,
  cursorNavigation?: {
    movePage: (direction: "forward" | "backward") => Promise<void>;
    hasNextPage: Ref<boolean>;
    hasPreviousPage: Ref<boolean>;
  },
) {
  const currentBuild = ref<any | null>({
    validation: {
      metadata_schema_errors: [{ record_id: "validation-record" }],
    },
    metadata_issue_summary: {
      records: [{ record_id: "metadata-record" }],
    },
  });
  const queueRows = ref<any[]>([record("r1"), record("r2")]);
  const recordTotal = ref(4);
  const recordOffset = ref(0);
  const selectedRecord = ref<any | null>(queueRows.value[0]);
  const selectedRecordId = ref("r1");
  const selectedRecordIndex = computed(() =>
    queueRows.value.findIndex((item) => item.record_id === selectedRecord.value?.record_id),
  );
  const reviewQueue = ref<any>("all");
  const recordQuery = ref("");
  const focusView = ref(false);
  const reviewRequested = ref(false);
  const focusHistory = ref<string[]>([]);
  const focusHistoryOffsets = ref<number[]>([]);
  const focusHistoryIndex = ref(-1);
  const recordListEl = ref<HTMLElement | null>(document.createElement("div"));
  recordListEl.value!.focus = vi.fn();
  const refreshRecords = vi.fn(async (_reset = false, preferredId = "") => {
    if (preferredId) selectedRecord.value = record(preferredId);
  });
  const selectRecord = vi.fn((item: any) => {
    selectedRecord.value = item;
  });

  const navigation = useCorpusReviewNavigation({
    currentBuild,
    queueRows,
    recordTotal,
    recordOffset,
    selectedRecord,
    selectedRecordId,
    selectedRecordIndex,
    reviewQueue,
    recordQuery,
    focusView,
    reviewRequested,
    focusHistory,
    focusHistoryOffsets,
    focusHistoryIndex,
    recordListEl,
    pageSize: 2,
    refreshRecords,
    selectRecord,
    beforeNavigate,
    ...cursorNavigation,
  });

  return {
    navigation,
    currentBuild,
    queueRows,
    recordOffset,
    selectedRecord,
    selectedRecordId,
    reviewQueue,
    recordQuery,
    focusView,
    reviewRequested,
    focusHistory,
    focusHistoryOffsets,
    focusHistoryIndex,
    refreshRecords,
    selectRecord,
    recordListEl,
  };
}

describe("Corpus Builder review navigation", () => {
  it("uses cursor movement for sequential pages but offsets for history and random jumps", async () => {
    const movePage = vi.fn(async (_direction: "forward" | "backward") => undefined);
    const state = setup(undefined, {
      movePage,
      hasNextPage: ref(true),
      hasPreviousPage: ref(true),
    });
    await state.navigation.nextPage();
    await state.navigation.previousPage();
    expect(movePage.mock.calls).toEqual([["forward"], ["backward"]]);
    expect(state.refreshRecords).not.toHaveBeenCalled();
    await state.navigation.changePage(100);
    expect(state.recordOffset.value).toBe(100);
    expect(state.refreshRecords).toHaveBeenCalledOnce();
    state.focusHistory.value = ["r1", "r9"];
    state.focusHistoryOffsets.value = [0, 100];
    state.focusHistoryIndex.value = 1;
    await state.navigation.focusHistoryMove(-1);
    expect(state.recordOffset.value).toBe(0);
    expect(state.refreshRecords).toHaveBeenLastCalledWith(false, "r1");
    expect(movePage).toHaveBeenCalledTimes(2);
  });
  it("leaves selection, page and filters unchanged when draft navigation is declined", async () => {
    const beforeNavigate = vi.fn().mockResolvedValue(false);
    const state = setup(beforeNavigate);
    await state.navigation.nextPage();
    await state.navigation.openMetadataIssueQueue();
    await state.navigation.focusQueueMove(1);
    await state.navigation.advanceFrom("r1");
    expect(state.recordOffset.value).toBe(0);
    expect(state.reviewQueue.value).toBe("all");
    expect(state.selectedRecordId.value).toBe("r1");
    expect(state.refreshRecords).not.toHaveBeenCalled();
    expect(state.selectRecord).not.toHaveBeenCalled();
    expect(beforeNavigate).toHaveBeenCalledTimes(4);
  });
  it("advances to the next page before considering a previous Record", async () => {
    const state = setup();
    await state.navigation.advanceFrom("r2");
    expect(state.recordOffset.value).toBe(2);
    expect(state.refreshRecords).toHaveBeenCalled();
    expect(state.selectRecord).not.toHaveBeenCalled();
  });

  it("backfills a removed last row without skipping the next matching Record", async () => {
    const state = setup();
    state.queueRows.value = [record("r1")];
    state.refreshRecords.mockImplementation(async () => {
      state.queueRows.value = [record("r1"), record("r3")];
    });
    await state.navigation.advanceFrom("r2", 1);
    expect(state.recordOffset.value).toBe(0);
    expect(state.selectRecord).toHaveBeenCalledWith(record("r3"));
  });

  it("records focus history with the page offset used to reach each record", async () => {
    const state = setup();

    state.navigation.openFocusView();
    expect(state.focusView.value).toBe(true);
    expect(state.focusHistory.value).toEqual(["r1"]);
    expect(state.focusHistoryOffsets.value).toEqual([0]);

    state.recordOffset.value = 2;
    state.selectedRecord.value = record("r3");
    state.navigation.pushFocusHistory("r3");

    expect(state.focusHistory.value).toEqual(["r1", "r3"]);
    expect(state.focusHistoryOffsets.value).toEqual([0, 2]);

    await state.navigation.focusHistoryMove(-1);
    expect(state.recordOffset.value).toBe(0);
    expect(state.refreshRecords).toHaveBeenCalledWith(false, "r1");
  });

  it("targets validation records directly without assuming they belong to Issues", async () => {
    const state = setup();

    await state.navigation.openValidationIssueQueue();
    await nextTick();

    expect(state.reviewQueue.value).toBe("all");
    // The "all" queue looks identical to Finish, so the review workspace is requested explicitly.
    expect(state.reviewRequested.value).toBe(true);
    expect(state.recordQuery.value).toBe("validation-record");
    expect(state.refreshRecords).toHaveBeenCalledWith(true, "validation-record");
    expect(state.selectedRecordId.value).toBe("");
    expect(state.recordListEl.value?.focus).toHaveBeenCalled();
  });

  it("clears stale record selection before changing review queues", async () => {
    const state = setup();
    state.selectedRecordId.value = "r1";
    state.selectedRecord.value = record("r1");

    await state.navigation.openRejectedQueue();

    expect(state.reviewQueue.value).toBe("rejected");
    expect(state.selectedRecordId.value).toBe("");
    expect(state.selectedRecord.value).toBeNull();
    expect(state.refreshRecords).toHaveBeenCalledWith(true, "");
  });

  it("opens structural repair work in the topology queue", async () => {
    const state = setup();

    await state.navigation.openTopologyIssueQueue();

    expect(state.reviewQueue.value).toBe("topology");
    expect(state.refreshRecords).toHaveBeenCalledWith(true, "");
  });

  it("clears the previous-page selection before loading the next page", async () => {
    const state = setup();
    state.selectedRecordId.value = "r1";
    state.selectedRecord.value = record("r1");

    await state.navigation.nextPage();

    expect(state.recordOffset.value).toBe(2);
    expect(state.selectedRecordId.value).toBe("");
    expect(state.selectedRecord.value).toBeNull();
    expect(state.refreshRecords).toHaveBeenCalledWith();
  });

  it("clears the previous-page selection before loading the previous page", async () => {
    const state = setup();
    state.recordOffset.value = 2;
    state.selectedRecordId.value = "r3";
    state.selectedRecord.value = record("r3");

    await state.navigation.previousPage();

    expect(state.recordOffset.value).toBe(0);
    expect(state.selectedRecordId.value).toBe("");
    expect(state.selectedRecord.value).toBeNull();
    expect(state.refreshRecords).toHaveBeenCalledWith();
  });

  it("moves across local records before requesting another page", async () => {
    const state = setup();

    await state.navigation.focusQueueMove(1);
    expect(state.selectRecord).toHaveBeenCalledWith(state.queueRows.value[1]);
    expect(state.focusHistory.value).toEqual(["r2"]);
    expect(state.refreshRecords).not.toHaveBeenCalled();
  });
});
