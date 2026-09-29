<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import { useSemanticMapStore } from "../stores/semanticMap";
import type { SemanticMapSource } from "../domain/semanticMap";
import * as runtime from "../runtime/runtime.js";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import SemanticMapFrame from "../components/semantic/SemanticMapFrame.vue";

const i18n = useI18nStore();
const map = useSemanticMapStore();
const sources = ref<SemanticMapSource[]>([]);
const focusId = ref("");

function load() {
  try {
    const data = runtime.listSemanticMapSources();
    sources.value = data?.records || [];
    focusId.value = data?.focusId || "";
  } catch {
    sources.value = [];
    focusId.value = "";
  }
}

onMounted(() => {
  map.enable("page");
  load();
});
watch(
  () => i18n.locale,
  () => load(),
);
</script>

<template>
  <main class="semantic-map-page" data-page-width="full">
    <UiPageHeader
      :kicker="i18n.t('section.corpus', 'Corpus')"
      :title="i18n.t('nav.semantic_map', 'Semantic map')"
      title-id="semantic-map-title"
      :description="
        i18n.t(
          'semantic_map.page_help',
          'Concepts, topics, and persons that occur together. Drag the map to move it, or choose another place to keep it open.',
        )
      "
    />
    <SemanticMapFrame variant="page" :sources="sources" :focus-id="focusId" :show-close="false" />
  </main>
</template>

<style scoped>
.semantic-map-page {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 140px);
}
.semantic-map-page :deep(.semantic-map-frame) {
  flex: 1;
}
</style>
