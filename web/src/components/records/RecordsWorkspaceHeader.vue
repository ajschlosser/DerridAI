<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import UiPageHeader from "../ui/UiPageHeader.vue";

const props = withDefaults(
  defineProps<{
    fileName?: string;
    matched?: number;
    total?: number;
    flagged?: number;
    selected?: number;
  }>(),
  { fileName: "", matched: 0, total: 0, flagged: 0, selected: 0 },
);
const emit = defineEmits<{ share: []; columns: []; import: [] }>();
const i18n = useI18nStore();
const copyLinkHelp = computed(() => i18n.t("records.copy_view_link_help"));
</script>
<template>
  <UiPageHeader
    class="records-hero"
    :kicker="i18n.t('section.corpus')"
    :title="i18n.t('nav.records')"
    :description="i18n.t('records.page_help')"
    title-id="records-page-title"
    :actions-label="i18n.t('records.view_actions')"
  >
    <template #actions>
      <div class="records-hero-actions">
        <button type="button" class="btn" @click="emit('import')">
          <AppIcon name="upload" />{{ i18n.t("records.choose_jsonl") }}
        </button>
        <button type="button" class="btn" @click="emit('columns')">
          <AppIcon name="list" />{{ i18n.t("records.columns") }}
        </button>
        <button
          type="button"
          class="btn soft"
          aria-describedby="records-copy-link-help"
          @click="emit('share')"
        >
          <AppIcon name="copy" />{{ i18n.t("records.copy_view_link") }}
        </button>
        <span id="records-copy-link-help" class="sr-only">{{ copyLinkHelp }}</span>
      </div>
    </template>
    <template #meta>
      <ul class="records-stats" :aria-label="i18n.t('records.workspace_stats')">
        <li>
          <b>{{ props.fileName || i18n.t("records.no_file") }}</b
          ><span>{{ i18n.t("records.active_tab") }}</span>
        </li>
        <li>
          <b
            >{{ props.matched.toLocaleString(i18n.locale) }} /
            {{ props.total.toLocaleString(i18n.locale) }}</b
          ><span>{{ i18n.t("records.visible_of_loaded") }}</span>
        </li>
        <li>
          <b>{{ props.flagged.toLocaleString(i18n.locale) }}</b
          ><span>{{ i18n.t("records.needs_review_count") }}</span>
        </li>
        <li>
          <b>{{ props.selected.toLocaleString(i18n.locale) }}</b
          ><span>{{ i18n.t("search.selected_records") }}</span>
        </li>
      </ul>
    </template>
  </UiPageHeader>
</template>
<style scoped>
.records-hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.records-hero-actions :deep(svg) {
  width: 1rem;
  height: 1rem;
  flex: 0 0 1rem;
}
.records-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.records-stats li {
  display: grid;
  gap: 2px;
  min-height: 3.5rem;
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.records-stats b {
  font-size: 0.9375rem;
  line-height: 1.3;
  overflow-wrap: anywhere;
}
.records-stats span {
  font-size: 0.8125rem;
  color: var(--text-tertiary);
}
</style>
