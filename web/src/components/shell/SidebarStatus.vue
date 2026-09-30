<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";

const props = defineProps<{
  isAdmin: boolean;
  hasCorpusDb: boolean;
  totalLoaded: number;
  corpusStoreCount: number;
  activeStore: string;
  dbRecords: number;
  selectedEvidenceCount: number;
}>();
const i18n = useI18nStore();
</script>
<template>
  <div class="shell-sidebar-footer">
    <div class="shell-mini-status">
      <template v-if="props.isAdmin">
        <span
          ><i :class="['status-dot', props.hasCorpusDb ? 'ok' : '']" aria-hidden="true"></i
          >{{ props.totalLoaded.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records") }}</span
        >
        <span v-if="props.corpusStoreCount"
          >{{ props.corpusStoreCount }} {{ i18n.t("ui.corpus_dbs") }}</span
        >
      </template>
      <template v-else>
        <span
          ><i :class="['status-dot', props.hasCorpusDb ? 'ok' : '']" aria-hidden="true"></i
          >{{ props.activeStore || i18n.t("research.none_selected") }}</span
        >
        <span
          >{{ props.dbRecords.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records") }} ·
          {{ props.selectedEvidenceCount }} {{ i18n.t("dynamic.selected_evidence") }}</span
        >
      </template>
    </div>
  </div>
</template>

<style scoped>
.shell-mini-status {
  display: grid;
  gap: 5px;
  min-height: 56px;
  align-content: center;
  padding: 8px 10px;
  border: 1px solid color-mix(in srgb, var(--line) 78%, transparent);
  border-radius: 10px;
  background: color-mix(in srgb, var(--surface-inset) 68%, transparent);
  color: var(--muted);
  font-size: 0.8125rem;
}
.shell-mini-status span {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (max-height: 820px) and (min-width: 901px) {
  .shell-mini-status {
    font-size: 0.8125rem !important;
    gap: 2px !important;
  }
}
</style>
