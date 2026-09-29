/* Copyright 2026 Aaron John Schlosser, PhD. */
import { ref } from "vue";
import { defineStore } from "pinia";
import {
  SEMANTIC_MAP_PLACEMENTS,
  type SemanticMapPlacement,
} from "../domain/semanticMap";

const PLACEMENT_KEY = "derridai.semanticMap.placement";
const ENABLED_KEY = "derridai.semanticMap.enabled";

function readPlacement(): SemanticMapPlacement {
  try {
    const saved = localStorage.getItem(PLACEMENT_KEY);
    if (SEMANTIC_MAP_PLACEMENTS.includes(saved as SemanticMapPlacement))
      return saved as SemanticMapPlacement;
  } catch {
    /* preference is optional */
  }
  return "record";
}

function readEnabled(): boolean {
  try {
    return localStorage.getItem(ENABLED_KEY) === "1";
  } catch {
    return false;
  }
}

export const useSemanticMapStore = defineStore("semanticMap", () => {
  const placement = ref<SemanticMapPlacement>(readPlacement());
  const enabled = ref(readEnabled());

  function persist() {
    try {
      localStorage.setItem(PLACEMENT_KEY, placement.value);
      localStorage.setItem(ENABLED_KEY, enabled.value ? "1" : "0");
    } catch {
      /* preference is optional */
    }
  }

  function enable(next?: SemanticMapPlacement) {
    if (next) placement.value = next;
    enabled.value = true;
    persist();
  }

  function setPlacement(next: SemanticMapPlacement) {
    placement.value = next;
    enabled.value = true;
    persist();
  }

  function disable() {
    enabled.value = false;
    persist();
  }

  return { placement, enabled, enable, setPlacement, disable };
});
