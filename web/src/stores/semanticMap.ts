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

import { ref } from "vue";
import { defineStore } from "pinia";
import { SEMANTIC_MAP_PLACEMENTS, type SemanticMapPlacement } from "../domain/semanticMap";

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
