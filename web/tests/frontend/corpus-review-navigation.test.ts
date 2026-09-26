/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, nextTick, ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { useCorpusReviewNavigation } from "../../src/features/corpus-builder/composables/useCorpusReviewNavigation";

function record(id: string) {
  return { record_id: id } as any;
}

function setup() {
  const currentBuild = ref<any | null>({
    validation: {
      metadata_schema_errors: [{ record_id: "validation-record" }],
    },
    metadata_issue_summary: {
      records: [{ record_id: "metadata-record" }],
    },
  });
  const records = ref<any[]>([record("r1"), record("r2")]);
  const recordTotal = ref(4);
  const recordOffset = ref(0);
  const selectedRecord = ref<any | null>(records.value[0]);
  const selectedRecordId = ref("r1");
  const selectedRecordIndex = computed(() =>
    records.value.findIndex((item) => item.record_id === selectedRecord.value?.record_id),
  );
  const reviewQueue = ref<any>("all");
  const recordQuery = ref("");
  const focusView = ref(false);
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
    records,
    recordTotal,
    recordOffset,
    selectedRecord,
    selectedRecordId,
    selectedRecordIndex,
    reviewQueue,
    recordQuery,
    focusView,
    focusHistory,
    focusHistoryOffsets,
    focusHistoryIndex,
    recordListEl,
    pageSize: 2,
    refreshRecords,
    selectRecord,
  });

  return {
    navigation,
    currentBuild,
    records,
    recordOffset,
    selectedRecord,
    selectedRecordId,
    reviewQueue,
    recordQuery,
    focusView,
    focusHistory,
    focusHistoryOffsets,
    focusHistoryIndex,
    refreshRecords,
    selectRecord,
    recordListEl,
  };
}

describe("Corpus Builder review navigation", () => {
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

  it("moves across local records before requesting another page", async () => {
    const state = setup();

    await state.navigation.focusQueueMove(1);
    expect(state.selectRecord).toHaveBeenCalledWith(state.records.value[1]);
    expect(state.focusHistory.value).toEqual(["r2"]);
    expect(state.refreshRecords).not.toHaveBeenCalled();
  });
});
