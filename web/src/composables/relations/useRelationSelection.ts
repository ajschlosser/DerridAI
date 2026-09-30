/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, ref } from "vue";

export function useRelationSelection(initialId = "") {
  const selectedId = ref(initialId);
  const hasSelection = computed(() => Boolean(selectedId.value));

  function select(id: string) {
    selectedId.value = id;
  }

  function clear() {
    selectedId.value = "";
  }

  function toggle(id: string) {
    selectedId.value = selectedId.value === id ? "" : id;
  }

  function isSelected(id: string) {
    return selectedId.value === id;
  }

  return { selectedId, hasSelection, select, clear, toggle, isSelected };
}
