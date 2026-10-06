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
import { computed, ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
import { WORKS_DB_STATUSES } from "../../domain/worksWorkspace";
import type { WorksDbStatusKind, WorksFilters, WorksSort, WorksViewMode } from "../../types/works";
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
  /** Initial workspace reads keep the toolbar mounted but inert until its authoritative snapshot is known. */
  pending?: boolean;
  /** Failed/denied first reads keep the toolbar frame visible without implying usable data. */
  unavailable?: boolean;
}>();
const emit = defineEmits<{
  query: [value: string];
  sort: [value: WorksSort];
  filters: [patch: Partial<WorksFilters>];
  viewMode: [value: WorksViewMode];
}>();
const i18n = useI18nStore();

const admin = computed(() => props.mode === "admin");
const controlsDisabled = computed(() => Boolean(props.pending || props.unavailable));
const filtersOpen = ref(false);
const activeFilterCount = computed(
  () =>
    Number(admin.value && props.filters.needsReview) +
    Number(admin.value && Boolean(props.filters.dbStatus)) +
    Number(Boolean(props.filters.author)),
);
const sorts = computed<Array<{ value: WorksSort; label: string; admin?: boolean }>>(() => [
  { value: "title-asc", label: i18n.t("works.sort_title_asc") },
  { value: "title-desc", label: i18n.t("works.sort_title_desc") },
  { value: "records-desc", label: i18n.t("works.sort_records_desc") },
  { value: "review-desc", label: i18n.t("works.sort_review_desc"), admin: true },
  { value: "year-asc", label: i18n.t("works.sort_year_asc"), admin: true },
]);
const statusKinds = WORKS_DB_STATUSES;
const summary = computed(() => {
  if (props.pending) return i18n.t("works.loading");
  if (props.unavailable) return i18n.t("loading.unavailable", "Unavailable");
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
  <div class="works-toolbar-shell" :aria-busy="props.pending || undefined">
    <div class="works-toolbar-row">
      <div class="search works-toolbar-search">
        <input
          id="worksSearch"
          type="search"
          :value="props.query"
          :aria-label="i18n.t('works.search_label')"
          :placeholder="admin ? i18n.t('works.filter_title') : i18n.t('research.filter_works')"
          :disabled="controlsDisabled"
          @input="emit('query', ($event.target as HTMLInputElement).value)"
        />
      </div>
      <UiButton
        v-if="admin || props.authors.length"
        size="small"
        icon="filter"
        :label="i18n.t('works.filters')"
        :count="activeFilterCount"
        :expanded="filtersOpen"
        :disabled="controlsDisabled"
        @click="filtersOpen = !filtersOpen"
      />
      <label class="works-toolbar-field">
        <span>{{ i18n.t("works.sort_label") }}</span>
        <select
          id="worksSort"
          class="control compact-select"
          :value="props.sort"
          :disabled="controlsDisabled"
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
          :disabled="controlsDisabled"
          @click="emit('viewMode', 'cards')"
        />
        <UiButton
          size="small"
          :label="i18n.t('works.view_list')"
          :pressed="props.viewMode === 'list'"
          :disabled="controlsDisabled"
          @click="emit('viewMode', 'list')"
        />
      </div>
    </div>

    <div
      v-if="filtersOpen"
      id="works-filter-panel"
      class="works-filter-panel"
      role="group"
      :aria-label="i18n.t('works.filters')"
    >
      <label v-if="admin" class="works-filter-check">
        <input
          type="checkbox"
          :checked="props.filters.needsReview"
          :disabled="controlsDisabled"
          @change="emit('filters', { needsReview: ($event.target as HTMLInputElement).checked })"
        />
        <span>{{ i18n.t("works.filter_needs_review") }}</span>
      </label>
      <label v-if="admin" class="works-toolbar-field">
        <span>{{ i18n.t("works.filter_db_status") }}</span>
        <select
          class="control compact-select"
          :value="props.filters.dbStatus"
          :disabled="controlsDisabled"
          @change="
            emit('filters', {
              dbStatus: ($event.target as HTMLSelectElement).value as WorksDbStatusKind | '',
            })
          "
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
          :disabled="controlsDisabled"
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
        :disabled="controlsDisabled || !activeFilterCount"
        @click="clearFilters"
      />
    </div>

    <div
      v-if="activeFilterCount"
      class="works-filter-chips"
      :aria-label="i18n.t('works.active_filters')"
    >
      <button
        v-if="admin && props.filters.needsReview"
        type="button"
        class="works-filter-chip"
        @click="emit('filters', { needsReview: false })"
      >
        <span>{{ i18n.t("works.filter_needs_review") }}</span>
        <span aria-hidden="true">×</span>
        <span class="sr-only">{{ i18n.t("ui.remove") }}</span>
      </button>
      <button
        v-if="admin && props.filters.dbStatus"
        type="button"
        class="works-filter-chip"
        @click="emit('filters', { dbStatus: '' })"
      >
        <span>{{ i18n.t(`works.db_status_${props.filters.dbStatus}`) }}</span>
        <span aria-hidden="true">×</span>
        <span class="sr-only">{{ i18n.t("ui.remove") }}</span>
      </button>
      <button
        v-if="props.filters.author"
        type="button"
        class="works-filter-chip"
        @click="emit('filters', { author: '' })"
      >
        <span>{{ props.filters.author }}</span>
        <span aria-hidden="true">×</span>
        <span class="sr-only">{{ i18n.t("ui.remove") }}</span>
      </button>
      <UiButton
        size="small"
        variant="ghost"
        :label="i18n.t('works.filters_clear')"
        :disabled="controlsDisabled"
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
.works-filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}
.works-filter-chip {
  display: inline-flex;
  gap: var(--space-1);
  align-items: center;
  min-height: var(--control-height-small);
  padding: 0 var(--space-2);
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--surface-selected);
  color: var(--text-primary);
  font: inherit;
  font-size: var(--fs-sm);
  cursor: pointer;
}
.works-filter-chip:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.works-toolbar-summary {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
</style>
