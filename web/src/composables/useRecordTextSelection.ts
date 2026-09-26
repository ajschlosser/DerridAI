// Copyright 2026 Aaron John Schlosser, PhD.
import { onBeforeUnmount, ref, watch, type Ref } from "vue";

/** Marks the element that holds the record's own text; only selections inside it can be cited as evidence. */
export const RECORD_TEXT_ATTRIBUTE = "data-record-text";

function readRecordSelection(): string {
  const selection = window.getSelection();
  const text = String(selection?.toString() || "").trim();
  const anchor = selection?.anchorNode;
  if (!text || !anchor) return "";
  // The anchor is often a text node; climb to its element before matching.
  const element = anchor instanceof Element ? anchor : anchor.parentElement;
  return element?.closest(`[${RECORD_TEXT_ATTRIBUTE}]`) ? text : "";
}

/**
 * Track the text the reviewer selects in the record while `active` is true.
 *
 * The selection is kept after it collapses (a click elsewhere would otherwise lose it) until it is used or cleared,
 * and is dropped when `active` turns off. `capture()` returns the tracked text, falling back to whatever is selected
 * right now so a selection made before tracking began still counts.
 */
export function useRecordTextSelection(active: Ref<boolean>) {
  const selection = ref("");
  function track() {
    const text = readRecordSelection();
    if (text) selection.value = text;
  }
  watch(
    active,
    (on) => {
      if (on) document.addEventListener("selectionchange", track);
      else {
        document.removeEventListener("selectionchange", track);
        selection.value = "";
      }
    },
    { immediate: true },
  );
  onBeforeUnmount(() => document.removeEventListener("selectionchange", track));
  const capture = () => selection.value || String(window.getSelection()?.toString() || "").trim();
  return { selection, capture };
}
