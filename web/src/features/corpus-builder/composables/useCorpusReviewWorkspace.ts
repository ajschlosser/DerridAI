/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, nextTick, ref, watch } from "vue";

export type ReviewInspectorTab = "metadata" | "evidence" | "source";
export type ReviewWorkspaceMode = "record" | "metadata" | "source";

export type ReviewViewport = {
  windowY: number;
  queueTop: number;
  recordTop: number;
  inspectorTop: number;
};

const QUEUE_KEY = "derridai.reviewQueueCollapsed";

function initialQueueCollapsed(): boolean {
  try {
    const stored = localStorage.getItem(QUEUE_KEY);
    if (stored === "1") return true;
    if (stored === "0") return false;
  } catch {
    // Private browsing or disabled storage: the queue simply starts open.
  }
  return false;
}

/**
 * Owns review-only presentation state and DOM coordination.
 *
 * Record data, mutations, and API state deliberately stay outside this
 * composable. This keeps one canonical Record source of truth while allowing
 * normal review and focus review to share navigation/layout state.
 */
export function useCorpusReviewWorkspace() {
  const reviewQueueCollapsed = ref(initialQueueCollapsed());
  const reviewInspectorTab = ref<ReviewInspectorTab>("metadata");
  const reviewWorkspaceMode = ref<ReviewWorkspaceMode>("record");
  const recordQuery = ref("");
  const selectedReviewIds = ref<Set<string>>(new Set());
  const selectedReviewCount = computed(() => selectedReviewIds.value.size);
  const focusView = ref(false);
  const focusHistory = ref<string[]>([]);
  const focusHistoryOffsets = ref<number[]>([]);
  const focusHistoryIndex = ref(-1);

  const recordListEl = ref<HTMLElement | null>(null);
  const reviewPaneEl = ref<HTMLElement | null>(null);
  const reviewInspectorEl = ref<HTMLElement | null>(null);

  watch(reviewQueueCollapsed, (value) => {
    try {
      localStorage.setItem(QUEUE_KEY, value ? "1" : "0");
    } catch {
      // Remembering layout is optional and must never block review.
    }
  });

  function captureReviewViewport(): ReviewViewport {
    return {
      windowY: window.scrollY,
      queueTop: recordListEl.value?.scrollTop || 0,
      recordTop: reviewPaneEl.value?.scrollTop || 0,
      inspectorTop: reviewInspectorEl.value?.scrollTop || 0,
    };
  }

  async function restoreReviewViewport(
    snapshot: ReviewViewport,
    { record = false, inspector = false }: { record?: boolean; inspector?: boolean } = {},
  ) {
    await nextTick();
    window.scrollTo({ top: snapshot.windowY, left: window.scrollX, behavior: "auto" });
    if (recordListEl.value) recordListEl.value.scrollTop = snapshot.queueTop;
    if (reviewPaneEl.value && !record) reviewPaneEl.value.scrollTop = snapshot.recordTop;
    if (reviewInspectorEl.value && !inspector)
      reviewInspectorEl.value.scrollTop = snapshot.inspectorTop;
  }

  function focusFirstMetadataBlocker() {
    reviewInspectorTab.value = "metadata";
    void nextTick(() => {
      const root = reviewInspectorEl.value;
      const field = root?.querySelector<HTMLElement>('[data-unresolved-field="true"]');
      // The field's Confirm button first, so Enter confirms the proposed value; otherwise its value control.
      const control =
        field?.querySelector<HTMLElement>("[data-primary-action]:not([disabled])") ||
        field?.querySelector<HTMLElement>(
          "input:not([disabled]),select:not([disabled]),button:not([disabled]),textarea:not([disabled])",
        );
      if (field && root) {
        const top = Math.max(0, field.offsetTop - root.offsetTop - 56);
        root.scrollTo({ top, behavior: "smooth" });
      }
      control?.focus({ preventScroll: true });
    });
  }

  function setReviewWorkspaceMode(mode: ReviewWorkspaceMode) {
    reviewWorkspaceMode.value = mode;
    if (mode !== "record") reviewInspectorTab.value = mode;
    void nextTick(() => {
      if (mode === "record") reviewPaneEl.value?.focus?.({ preventScroll: true });
      else reviewInspectorEl.value?.focus?.({ preventScroll: true });
    });
  }

  function reviewInspectorKeydown(event: KeyboardEvent) {
    const tabs: ReviewInspectorTab[] = ["metadata", "evidence", "source"];
    const current = tabs.indexOf(reviewInspectorTab.value);
    let next = current;
    if (event.key === "ArrowRight") next = (current + 1) % tabs.length;
    else if (event.key === "ArrowLeft") next = (current - 1 + tabs.length) % tabs.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tabs.length - 1;
    else return;
    event.preventDefault();
    reviewInspectorTab.value = tabs[next];
    void nextTick(() =>
      reviewInspectorEl.value
        ?.querySelector<HTMLElement>(`[data-review-tab="${tabs[next]}"]`)
        ?.focus({ preventScroll: true }),
    );
  }

  return {
    reviewQueueCollapsed,
    reviewInspectorTab,
    reviewWorkspaceMode,
    recordQuery,
    selectedReviewIds,
    selectedReviewCount,
    focusView,
    focusHistory,
    focusHistoryOffsets,
    focusHistoryIndex,
    recordListEl,
    reviewPaneEl,
    reviewInspectorEl,
    captureReviewViewport,
    restoreReviewViewport,
    focusFirstMetadataBlocker,
    setReviewWorkspaceMode,
    reviewInspectorKeydown,
  };
}
