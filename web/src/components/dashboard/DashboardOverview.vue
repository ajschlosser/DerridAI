<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { DashboardTotals } from "../../types/dashboard";
defineProps<{ totals: DashboardTotals }>();
const i18n = useI18nStore();
const emit = defineEmits<{ works: []; records: []; databases: [] }>();
</script>
<template>
  <section class="overview" :aria-label="i18n.t('dashboard.corpus_overview', 'Corpus Overview')">
    <button type="button" class="metric card" @click="emit('works')">
      <AppIcon name="books" aria-hidden="true" /><strong>{{
        totals.works.toLocaleString(i18n.locale)
      }}</strong
      ><span>{{ i18n.t("dashboard.works", "Works") }}</span></button
    ><button type="button" class="metric card" @click="emit('records')">
      <AppIcon name="record" aria-hidden="true" /><strong>{{
        totals.records.toLocaleString(i18n.locale)
      }}</strong
      ><span>{{ i18n.t("dashboard.records", "Records") }}</span></button
    ><button type="button" class="metric card" @click="emit('databases')">
      <AppIcon name="database" aria-hidden="true" /><strong>{{
        totals.dbs.toLocaleString(i18n.locale)
      }}</strong
      ><span>{{ i18n.t("dashboard.databases", "Databases") }}</span>
    </button>
    <div class="metric card">
      <AppIcon name="history" aria-hidden="true" /><strong>{{
        totals.changes.toLocaleString(i18n.locale)
      }}</strong
      ><span>{{ i18n.t("dashboard.recent_activity", "Recent Activity") }}</span>
    </div>
  </section>
</template>
<style scoped>
.overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}
.metric {
  display: grid;
  gap: var(--space-2);
  justify-items: start;
  padding: var(--space-4);
  border: 1px solid var(--line);
  color: var(--text);
  text-align: left;
}
.metric:not(div) {
  cursor: pointer;
}
.metric:not(div):hover {
  border-color: var(--accent-border);
  background: var(--panel-2);
}
.metric:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
.metric svg {
  color: var(--accent-fg);
}
.metric strong {
  font-size: var(--fs-xl);
}
.metric span {
  color: var(--text-2);
  font-size: var(--fs-sm);
}
@media (max-width: 900px) {
  .overview {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 620px) {
  .overview {
    grid-template-columns: 1fr;
  }
}
</style>
