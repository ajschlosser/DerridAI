<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import UiButton from "../ui/UiButton.vue";
import AppIcon from "../AppIcon.vue";
import AccessibleEmptyState from "../AccessibleEmptyState.vue";
import { useI18nStore } from "../../stores/i18n";
import type { DashboardWork } from "../../types/dashboard";
const props = defineProps<{ works: DashboardWork[] }>();
const i18n = useI18nStore();
const emit = defineEmits<{ works: []; searchWork: [work: string] }>();
</script>
<template>
  <section class="works card" aria-labelledby="home-works-title">
    <div class="heading">
      <AppIcon name="books" aria-hidden="true" />
      <h2 id="home-works-title">{{ i18n.t("dashboard.works", "Works") }}</h2>
      <UiButton
        size="small"
        variant="ghost"
        :label="i18n.t('dashboard.view_all_works', 'View all works')"
        @click="emit('works')"
      />
    </div>
    <AccessibleEmptyState
      v-if="!props.works.length"
      icon="upload"
      :title="i18n.t('records.open_workspace', 'Open a corpus workspace')"
      :description="
        i18n.t(
          'records.open_workspace_help',
          'Drop one or more JSONL files anywhere on this page, or choose files manually.',
        )
      "
      :action-label="''"
    />
    <ul v-else>
      <li v-for="item in props.works.slice(0, 8)" :key="item.work">
        <button type="button" @click="emit('searchWork', item.work)">
          <span
            ><b>{{ item.work }}</b
            ><small>{{
              item.year || i18n.t("dashboard.year_not_recorded", "Year not recorded")
            }}</small></span
          ><span
            >{{ item.count.toLocaleString(i18n.locale) }}
            {{ i18n.t("dynamic.records", "records") }}</span
          >
        </button>
      </li>
    </ul>
  </section>
</template>
<style scoped>
.works {
  padding: var(--space-5);
}
.heading {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.heading h2 {
  margin: 0;
  font-size: var(--fs-lg);
}
.heading .ui-button-wrap {
  margin-left: auto;
}
ul {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
  padding: 0;
  margin: 0;
  list-style: none;
}
button {
  width: 100%;
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-3);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--text);
  text-align: left;
}
button:hover {
  background: var(--panel-2);
  border-color: var(--accent-border);
}
button:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
button > span:first-child {
  display: grid;
  gap: var(--space-1);
  min-width: 0;
}
b {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
small,
button > span:last-child {
  color: var(--muted);
  font-size: var(--fs-sm);
}
@media (max-width: 620px) {
  ul {
    grid-template-columns: 1fr;
  }
}
</style>
