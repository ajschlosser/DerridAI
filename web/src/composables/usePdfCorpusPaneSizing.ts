// Copyright 2026 Aaron John Schlosser, PhD.
import { ref } from "vue";
import { useSplitter } from "./useSplitter";

/**
 * Owns the persistent review workspace pane sizes used by PdfCorpusBuilder.
 *
 * The splitters share one grid container because their pointer measurements
 * must use the same writing direction and outer bounds.
 */
export function usePdfCorpusPaneSizing() {
  const reviewGridEl = ref<HTMLElement | null>(null);
  const container = () => reviewGridEl.value;

  const queueSplitter = useSplitter({
    key: "derridai.review.queueWidth",
    min: 224,
    max: 420,
    initial: 256,
    edge: "start",
    container,
  });
  const inspectorSplitter = useSplitter({
    key: "derridai.review.inspectorWidth",
    min: 320,
    max: 640,
    initial: 368,
    edge: "end",
    container,
  });
  const reviewHeightSplitter = useSplitter({
    key: "derridai.review.height",
    min: 420,
    max: 1200,
    initial: 680,
    edge: "start",
    axis: "vertical",
    container,
  });

  return {
    reviewGridEl,
    queueSplitter,
    inspectorSplitter,
    reviewHeightSplitter,
  };
}
