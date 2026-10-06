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
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import PdfExplorerSurface from "../components/PdfExplorerSurface.vue";
import PdfCorpusBuilder from "../components/PdfCorpusBuilder.vue";
import { useI18nStore } from "../stores/i18n";
import {
  queryForPdfWorkspace,
  queryForPdfWorkspaceTransition,
  type PdfWorkspaceDestination,
} from "../domain/pdfWorkspaceNavigation";

const i18n = useI18nStore();
const route = useRoute();
const router = useRouter();
const mode = computed<PdfWorkspaceDestination>(() =>
  route.meta.pdfMode === "explorer" ? "explorer" : "builder",
);
const rememberedBuilderQuery = ref<Record<string, unknown>>({});
const rememberedExplorerQuery = ref<Record<string, unknown>>({});

// Each sibling keeps its own addressable state. Capturing it before leaving
// means the tabs can restore the previous Builder/Explorer context without
// leaking one workspace's query semantics into the other workspace's URL.
watch(
  [mode, () => route.query] as const,
  ([currentMode, query]) => {
    const snapshot = queryForPdfWorkspace(currentMode, query);
    if (currentMode === "builder") rememberedBuilderQuery.value = snapshot;
    else rememberedExplorerQuery.value = snapshot;
  },
  { immediate: true },
);

async function setMode(next: PdfWorkspaceDestination) {
  if (next === mode.value) return;
  const remembered =
    next === "builder" ? rememberedBuilderQuery.value : rememberedExplorerQuery.value;
  const query = Object.keys(remembered).length
    ? remembered
    : queryForPdfWorkspaceTransition(mode.value, next, route.query);
  await router.push({
    name: next === "explorer" ? "source-explorer" : "corpus-builder",
    query,
  });
}

function openBuilder() {
  void setMode("builder");
}

onMounted(() => window.addEventListener("derridai:pdf-builder", openBuilder));
onBeforeUnmount(() => window.removeEventListener("derridai:pdf-builder", openBuilder));
</script>

<template>
  <div class="pdf-workspace-native" data-page-width="full">
    <nav class="pdf-mode-tabs" :aria-label="i18n.t('pdf_workspace.modes')">
      <button
        type="button"
        :class="{ active: mode === 'builder' }"
        :aria-current="mode === 'builder' ? 'page' : undefined"
        @click="setMode('builder')"
      >
        {{ i18n.t("pdf_workspace.builder") }}
      </button>
      <button
        type="button"
        :class="{ active: mode === 'explorer' }"
        :aria-current="mode === 'explorer' ? 'page' : undefined"
        @click="setMode('explorer')"
      >
        {{ i18n.t("pdf_workspace.explorer") }}
      </button>
      <span>{{ i18n.t("pdf_workspace.help") }}</span>
    </nav>
    <PdfCorpusBuilder v-if="mode === 'builder'" />
    <PdfExplorerSurface v-else />
  </div>
</template>

<style scoped>
.pdf-mode-tabs {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 9px 20px;
  border-bottom: 1px solid var(--line);
  background: color-mix(in srgb, var(--card) 97%, transparent);
  position: sticky;
  top: 0;
  z-index: 20;
  backdrop-filter: blur(12px);
}
.pdf-mode-tabs button {
  border: 1px solid transparent;
  background: transparent;
  padding: 8px 12px;
  border-radius: 9px;
  font-size: 0.8125rem;
  font-weight: 750;
  color: var(--muted);
  cursor: pointer;
}
.pdf-mode-tabs button:hover {
  background: var(--soft);
  color: var(--text);
}
.pdf-mode-tabs button.active {
  background: var(--accent-soft, #eef6f2);
  border-color: var(--accent-soft-2, #dce9e3);
  color: var(--accent-fg);
  box-shadow: inset 0 -2px 0 var(--accent);
}
.pdf-mode-tabs button:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.pdf-mode-tabs span {
  margin-inline-start: auto;
  color: var(--muted);
  font-size: 0.8125rem;
}
@media (max-width: 700px) {
  .pdf-mode-tabs span {
    display: none;
  }
}
</style>
