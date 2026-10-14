<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useI18nStore } from "../../stores/i18n";
import { useSemanticMapStore } from "../../stores/semanticMap";
import type { SemanticMapSource } from "../../domain/semanticMap";
import { listSemanticMapSources } from "../../domain/semanticMapSources";
import { corpusState, vectorState } from "../../state/workspaceState";
import SemanticMapFrame from "./SemanticMapFrame.vue";

const i18n = useI18nStore();
const map = useSemanticMapStore();
const route = useRoute();
const dialog = ref<HTMLDialogElement | null>(null);
const sources = ref<SemanticMapSource[]>([]);
const focusId = ref("");
let closingForMove = false;

const showSidebar = computed(
  () => map.enabled && map.placement === "sidebar" && route.name !== "semanticmap",
);
const showModal = computed(() => map.enabled && map.placement === "modal");

function load() {
  try {
    const data = listSemanticMapSources();
    sources.value = data?.records || [];
    focusId.value = data?.focusId || "";
  } catch {
    sources.value = [];
    focusId.value = "";
  }
}

watch(
  () => [
    map.enabled,
    map.placement,
    route.query.file,
    route.query.record,
    corpusState.version,
    corpusState.activeFileId,
    vectorState.version,
    vectorState.storeRecords,
    vectorState.storeSearchResults,
  ],
  async () => {
    if (map.enabled) load();
    await nextTick();
    const element = dialog.value;
    if (!element) return;
    if (showModal.value) {
      if (!element.open) element.showModal();
      return;
    }
    if (element.open) {
      closingForMove = true;
      element.close();
    }
  },
  { immediate: true },
);

function onDialogClose() {
  if (closingForMove) {
    closingForMove = false;
    return;
  }
  if (map.placement === "modal") map.disable();
}

onMounted(load);
</script>

<template>
  <aside
    v-if="showSidebar"
    class="semantic-map-sidebar"
    :aria-label="i18n.t('semantic_map.sidebar_label', 'Semantic map sidebar')"
  >
    <SemanticMapFrame variant="sidebar" :sources="sources" :focus-id="focusId" />
  </aside>
  <dialog
    ref="dialog"
    class="semantic-map-dialog"
    :aria-label="i18n.t('semantic_map.modal_label', 'Semantic map dialog')"
    @close="onDialogClose"
    @cancel.prevent="map.disable()"
  >
    <SemanticMapFrame v-if="showModal" variant="modal" :sources="sources" :focus-id="focusId" />
  </dialog>
</template>

<style scoped>
.semantic-map-sidebar {
  display: flex;
  flex-direction: column;
  width: min(100%, 400px);
  min-width: 280px;
  min-height: 0;
  padding: 12px;
  border-left: 1px solid var(--border-subtle);
  background: var(--surface-card);
}
.semantic-map-dialog {
  width: min(92vw, 1100px);
  height: min(88vh, 820px);
  max-width: none;
  margin: auto;
  padding: 16px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-overlay);
  background: var(--surface-overlay);
  color: var(--text-primary);
  box-shadow: var(--shadow-overlay);
}
.semantic-map-dialog::backdrop {
  background: var(--scrim);
}
</style>
