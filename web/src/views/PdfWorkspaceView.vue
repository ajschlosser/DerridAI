<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import PdfExplorerSurface from "../components/PdfExplorerSurface.vue";
import PdfCorpusBuilder from "../components/PdfCorpusBuilder.vue";
import { useI18nStore } from "../stores/i18n";
import * as runtime from "../runtime/runtime.js";

const i18n = useI18nStore();
const route = useRoute();
const router = useRouter();
const requestedMode = () => (route.query.mode === "explorer" ? "explorer" : "builder");
const mode = ref<"explorer" | "builder">(requestedMode());
async function setMode(next: "explorer" | "builder") {
  // Switch the URL first: the Explorer's runtime surface syncs the URL as soon as it mounts, and if the mode is not in
  // the URL yet it writes the old one back and the tab appears not to work.
  const query = { ...route.query, mode: next };
  await router.replace({ query });
  mode.value = next;
  if (next === "explorer") {
    await nextTick();
    await runtime.renderView();
  }
}
function openBuilder() {
  void setMode("builder");
}
watch(
  () => [route.query.mode, route.query.build],
  () => {
    const next = requestedMode();
    if (next !== mode.value) void setMode(next);
  },
);
onMounted(() => window.addEventListener("derridai:pdf-builder", openBuilder));
onBeforeUnmount(() => window.removeEventListener("derridai:pdf-builder", openBuilder));
</script>

<template>
  <div class="pdf-workspace-native" data-page-width="full">
    <nav class="pdf-mode-tabs" :aria-label="i18n.t('pdf_workspace.modes', 'Corpus Builder modes')">
      <button
        type="button"
        :class="{ active: mode === 'builder' }"
        :aria-current="mode === 'builder' ? 'page' : undefined"
        @click="setMode('builder')"
      >
        {{ i18n.t("pdf_workspace.builder", "Corpus Builder") }}
      </button>
      <button
        type="button"
        :class="{ active: mode === 'explorer' }"
        :aria-current="mode === 'explorer' ? 'page' : undefined"
        @click="setMode('explorer')"
      >
        {{ i18n.t("pdf_workspace.explorer", "PDF Explorer") }}
      </button>
      <span>{{
        i18n.t(
          "pdf_workspace.help",
          "Build auditable record sets, with source reading available in PDF Explorer",
        )
      }}</span>
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
