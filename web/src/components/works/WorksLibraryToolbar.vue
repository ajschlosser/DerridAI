<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
import type { WorksFilters, WorksSort, WorksViewMode } from "../../types/works";
import UiButton from "../ui/UiButton.vue";

const props = defineProps<{
  mode: "admin" | "researcher";
  query: string;
  sort: WorksSort;
  filters: WorksFilters;
  viewMode: WorksViewMode;
  authors: string[];
  totalWorks: number;
  visibleWorks: number;
  totalReview: number;
}>();
const emit = defineEmits<{
  query: [value: string];
  sort: [value: WorksSort];
  filters: [patch: Partial<WorksFilters>];
  viewMode: [value: WorksViewMode];
}>();
const i18n = useI18nStore();

const admin = computed(() => props.mode === "admin");
const filtersOpen = ref(false);
const activeFilterCount = computed(
  () =>
    Number(props.filters.needsReview) +
    Number(Boolean(props.filters.dbStatus)) +
    Number(Boolean(props.filters.author)),
);
const sorts = computed<Array<{ value: WorksSort; label: string; admin?: boolean }>>(() => [
  { value: "title-asc", label: i18n.t("works.sort_title_asc") },
  { value: "title-desc", label: i18n.t("works.sort_title_desc") },
  { value: "records-desc", label: i18n.t("works.sort_records_desc") },
  { value: "review-desc", label: i18n.t("works.sort_review_desc"), admin: true },
  { value: "year-asc", label: i18n.t("works.sort_year_asc"), admin: true },
]);
const statusKinds = ["changed", "synced", "exists", "absent", "unknown", "none"];
const summary = computed(() => {
  const base = i18n.tf("works.result_summary", {
    visible: props.visibleWorks.toLocaleString(i18n.locale),
    total: props.totalWorks.toLocaleString(i18n.locale),
  });
  return admin.value && props.totalReview
    ? `${base} · ${i18n.tf("works.result_review", {
        count: props.totalReview.toLocaleString(i18n.locale),
      })}`
    : base;
});
function clearFilters() {
  emit("filters", { needsReview: false, dbStatus: "", author: "" });
}
</script>

<template>
  <div class="works-toolbar-shell">
    <div class="works-toolbar-row">
      <div class="search works-toolbar-search">
        <input
          id="worksSearch"
          type="search"
          :value="props.query"
          :aria-label="i18n.t('works.search_label')"
          :placeholder="admin ? i18n.t('works.filter_title') : i18n.t('research.filter_works')"
          @input="emit('query', ($event.target as HTMLInputElement).value)"
        />
      </div>
      <UiButton
        v-if="admin"
        size="small"
        icon="filter"
        :label="i18n.t('works.filters')"
        :count="activeFilterCount"
        :expanded="filtersOpen"
        @click="filtersOpen = !filtersOpen"
      />
      <label class="works-toolbar-field">
        <span>{{ i18n.t("works.sort_label") }}</span>
        <select
          id="worksSort"
          class="control compact-select"
          :value="props.sort"
          @change="emit('sort', ($event.target as HTMLSelectElement).value as WorksSort)"
        >
          <option
            v-for="option in sorts.filter((item) => admin || !item.admin)"
            :key="option.value"
            :value="option.value"
          >
            {{ option.label }}
          </option>
        </select>
      </label>
      <div class="works-toolbar-views" role="group" :aria-label="i18n.t('works.view_label')">
        <UiButton
          size="small"
          :label="i18n.t('works.view_cards')"
          :pressed="props.viewMode === 'cards'"
          @click="emit('viewMode', 'cards')"
        />
        <UiButton
          size="small"
          :label="i18n.t('works.view_compact')"
          :pressed="props.viewMode === 'compact'"
          @click="emit('viewMode', 'compact')"
        />
      </div>
    </div>

    <div
      v-if="admin && filtersOpen"
      id="works-filter-panel"
      class="works-filter-panel"
      role="group"
      :aria-label="i18n.t('works.filters')"
    >
      <label class="works-filter-check">
        <input
          type="checkbox"
          :checked="props.filters.needsReview"
          @change="emit('filters', { needsReview: ($event.target as HTMLInputElement).checked })"
        />
        <span>{{ i18n.t("works.filter_needs_review") }}</span>
      </label>
      <label class="works-toolbar-field">
        <span>{{ i18n.t("works.filter_db_status") }}</span>
        <select
          class="control compact-select"
          :value="props.filters.dbStatus"
          @change="emit('filters', { dbStatus: ($event.target as HTMLSelectElement).value })"
        >
          <option value="">{{ i18n.t("works.filter_any") }}</option>
          <option v-for="kind in statusKinds" :key="kind" :value="kind">
            {{ i18n.t(`works.db_status_${kind}`) }}
          </option>
        </select>
      </label>
      <label class="works-toolbar-field">
        <span>{{ i18n.t("works.filter_author") }}</span>
        <select
          class="control compact-select"
          :value="props.filters.author"
          @change="emit('filters', { author: ($event.target as HTMLSelectElement).value })"
        >
          <option value="">{{ i18n.t("works.filter_any") }}</option>
          <option v-for="author in props.authors" :key="author" :value="author">
            {{ author }}
          </option>
        </select>
      </label>
      <UiButton
        size="small"
        variant="ghost"
        :label="i18n.t('works.filters_clear')"
        :disabled="!activeFilterCount"
        @click="clearFilters"
      />
    </div>

    <p class="works-toolbar-summary" role="status" aria-live="polite">{{ summary }}</p>
  </div>
</template>

<style scoped>
.works-toolbar-shell {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.works-toolbar-row,
.works-filter-panel {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: end;
}
.works-toolbar-search {
  flex: 1 1 14rem;
  min-width: 0;
}
.works-toolbar-search input {
  width: 100%;
}
.works-toolbar-field {
  display: grid;
  gap: 2px;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.works-toolbar-views {
  display: inline-flex;
  gap: var(--space-1);
}
.works-filter-panel {
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.works-filter-check {
  display: inline-flex;
  gap: var(--space-2);
  align-items: center;
  min-height: var(--control-height-small);
  color: var(--text-primary);
  font-size: var(--fs-sm);
}
.works-toolbar-summary {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
</style>
