<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";

const props = withDefaults(defineProps<{
  fileName?: string;
  matched?: number;
  total?: number;
  flagged?: number;
  selected?: number;
}>(), {fileName: "", matched: 0, total: 0, flagged: 0, selected: 0});
const emit = defineEmits<{share: []; columns: []; import: []}>();
const i18n = useI18nStore();
</script>
<template>
  <header class="records-hero" aria-labelledby="records-page-title">
    <div>
      <p class="records-kicker">{{ i18n.t("section.corpus", "Corpus") }}</p>
      <h1 id="records-page-title">{{ i18n.t("nav.records", "Records") }}</h1>
      <p>{{ i18n.t("records.page_help", "Review loaded JSONL records, keep provenance visible, and act on a precise selection without crowding the table.") }}</p>
    </div>
    <div class="records-hero-actions" :aria-label="i18n.t('records.view_actions', 'Records view actions')">
      <button type="button" class="btn" @click="emit('import')"><AppIcon name="upload"/>{{ i18n.t("records.choose_jsonl", "Choose JSONL files") }}</button>
      <button type="button" class="btn" @click="emit('columns')"><AppIcon name="list"/>{{ i18n.t("records.columns", "Columns") }}</button>
      <button type="button" class="btn soft" @click="emit('share')"><AppIcon name="copy"/>{{ i18n.t("records.copy_link", "Copy link") }}</button>
    </div>
    <ul class="records-stats" :aria-label="i18n.t('records.workspace_stats', 'Workspace statistics')">
      <li><b>{{ props.fileName || i18n.t("records.no_file", "No file") }}</b><span>{{ i18n.t("records.active_tab", "Active file") }}</span></li>
      <li><b>{{ props.matched.toLocaleString(i18n.locale) }} / {{ props.total.toLocaleString(i18n.locale) }}</b><span>{{ i18n.t("records.visible_of_loaded", "Visible of loaded") }}</span></li>
      <li><b>{{ props.flagged.toLocaleString(i18n.locale) }}</b><span>{{ i18n.t("records.needs_review_count", "Need review") }}</span></li>
      <li><b>{{ props.selected.toLocaleString(i18n.locale) }}</b><span>{{ i18n.t("search.selected_records", "selected records") }}</span></li>
    </ul>
  </header>
</template>
<style scoped>
.records-hero{display:grid;gap:16px}
.records-kicker{margin:0;font-size:.8125rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color: var(--accent-fg)}
h1{margin:4px 0 0;font:600 1.75rem/1.2 Georgia,"Times New Roman",serif;color:var(--text)}
p{margin:8px 0 0;max-width:70ch;color:var(--muted);font-size:.875rem;line-height:1.5}
.records-hero-actions{display:flex;flex-wrap:wrap;gap:8px}
.records-hero-actions :deep(svg){width:1rem;height:1rem;flex:0 0 1rem}
.records-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(10rem,1fr));gap:8px;margin:0;padding:0;list-style:none}
.records-stats li{display:grid;gap:2px;min-height:3.5rem;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:var(--panel,var(--card,#fff))}
.records-stats b{font-size:.9375rem;line-height:1.3;overflow-wrap:anywhere}
.records-stats span{font-size:.8125rem;color:var(--muted)}
@media (min-width: 900px){
  .records-hero{grid-template-columns:minmax(0,1fr) auto;align-items:start}
  .records-stats{grid-column:1 / -1}
}
</style>
