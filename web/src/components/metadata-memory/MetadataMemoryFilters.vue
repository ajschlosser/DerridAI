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
import { computed } from "vue";
import type { MetadataMemoryPayload } from "../../api/metadataMemory";
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";

const props = defineProps<{
  query: string;
  field: string;
  kind: string;
  buildId: string;
  language: string;
  facets: MetadataMemoryPayload["facets"];
}>();

const emit = defineEmits<{
  "update:query": [value: string];
  "update:field": [value: string];
  "update:kind": [value: string];
  "update:buildId": [value: string];
  "update:language": [value: string];
  apply: [];
  clear: [];
}>();

const i18n = useI18nStore();
const searchModel = computed({
  get: () => props.query,
  set: (value: string) => emit("update:query", value),
});
const fieldModel = computed({
  get: () => props.field,
  set: (value: string) => emit("update:field", value),
});
const kindModel = computed({
  get: () => props.kind,
  set: (value: string) => emit("update:kind", value),
});
const buildModel = computed({
  get: () => props.buildId,
  set: (value: string) => emit("update:buildId", value),
});
const languageModel = computed({
  get: () => props.language,
  set: (value: string) => emit("update:language", value),
});

function kindLabel(value: string): string {
  if (value === "positive") return i18n.t("metadata_memory.kind_positive");
  if (value === "correction") return i18n.t("metadata_memory.kind_correction");
  return value;
}

const activeFilters = computed(() => {
  const filters: Array<{ key: string; label: string; value: string }> = [];
  const add = (key: string, label: string, value: string) => {
    if (value) filters.push({ key, label, value });
  };
  add("q", i18n.t("metadata_memory.search"), props.query.trim());
  add("field", i18n.t("metadata_memory.field"), props.field);
  add("kind", i18n.t("metadata_memory.kind"), props.kind ? kindLabel(props.kind) : "");
  add("build", i18n.t("metadata_memory.build"), props.buildId);
  add("language", i18n.t("metadata_memory.language"), props.language);
  return filters;
});

function chipText(label: string, value: string) {
  return i18n.tf("metadata_memory.filter_chip", { label, value });
}

function clearFilter(key: string) {
  if (key === "q") emit("update:query", "");
  else if (key === "field") emit("update:field", "");
  else if (key === "kind") emit("update:kind", "");
  else if (key === "build") emit("update:buildId", "");
  else if (key === "language") emit("update:language", "");
}
</script>

<template>
  <form
    class="memory-filters"
    role="search"
    :aria-label="i18n.t('metadata_memory.filters_label')"
    @submit.prevent="emit('apply')"
  >
    <label class="filter-search">
      <span>{{ i18n.t("metadata_memory.search") }}</span>
      <input
        v-model="searchModel"
        class="control"
        type="search"
        :placeholder="i18n.t('metadata_memory.search_placeholder')"
      />
    </label>
    <label>
      <span>{{ i18n.t("metadata_memory.field") }}</span>
      <select v-model="fieldModel" class="control">
        <option value="">{{ i18n.t("metadata_memory.all_fields") }}</option>
        <option v-for="value in facets.fields" :key="value" :value="value">{{ value }}</option>
      </select>
    </label>
    <label>
      <span>{{ i18n.t("metadata_memory.kind") }}</span>
      <select v-model="kindModel" class="control">
        <option value="">{{ i18n.t("metadata_memory.all_kinds") }}</option>
        <option v-for="value in facets.kinds" :key="value" :value="value">
          {{ kindLabel(value) }}
        </option>
      </select>
    </label>
    <label>
      <span>{{ i18n.t("metadata_memory.build") }}</span>
      <select v-model="buildModel" class="control">
        <option value="">{{ i18n.t("metadata_memory.all_builds") }}</option>
        <option v-for="value in facets.builds" :key="value" :value="value">{{ value }}</option>
      </select>
    </label>
    <label>
      <span>{{ i18n.t("metadata_memory.language") }}</span>
      <select v-model="languageModel" class="control">
        <option value="">{{ i18n.t("metadata_memory.all_languages") }}</option>
        <option v-for="value in facets.languages" :key="value" :value="value">{{ value }}</option>
      </select>
    </label>
  </form>

  <ul
    v-if="activeFilters.length"
    class="filter-chips"
    :aria-label="i18n.t('metadata_memory.active_filters')"
  >
    <li v-for="filter in activeFilters" :key="filter.key">
      <button
        type="button"
        class="chip"
        :aria-label="
          i18n.tf('metadata_memory.remove_filter', {
            label: chipText(filter.label, filter.value),
          })
        "
        @click="clearFilter(filter.key)"
      >
        {{ chipText(filter.label, filter.value) }}
        <AppIcon name="close" aria-hidden="true" />
      </button>
    </li>
    <li>
      <button type="button" class="chip-clear" @click="emit('clear')">
        {{ i18n.t("metadata_memory.clear_filters") }}
      </button>
    </li>
  </ul>
</template>

<style scoped>
.memory-filters {
  display: grid;
  grid-template-columns: minmax(220px, 1.6fr) repeat(4, minmax(130px, 1fr));
  gap: 10px;
  align-items: end;
  padding: 0 14px 12px;
}
.memory-filters label {
  display: grid;
  gap: 5px;
  min-width: 0;
  color: var(--text-secondary, var(--muted));
  font-size: 0.8125rem;
  font-weight: 700;
}
.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0;
  padding: 0 14px 12px;
  list-style: none;
}
.chip,
.chip-clear {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 28px;
  padding: 3px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--surface-inset);
  color: inherit;
  font: inherit;
  font-size: 0.8125rem;
  cursor: pointer;
}
.chip:hover {
  background: var(--surface-hover);
}
.chip-clear {
  border-color: transparent;
  background: none;
  color: var(--accent-fg, var(--accent));
  font-weight: 700;
  text-decoration: underline;
}
.chip:focus-visible,
.chip-clear:focus-visible {
  outline: var(--focus-ring-width, 3px) solid var(--focus-ring);
  outline-offset: 2px;
}
.chip :deep(svg) {
  width: 12px;
  height: 12px;
}
@media (max-width: 1000px) {
  .memory-filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .filter-search {
    grid-column: 1 / -1;
  }
}
@media (max-width: 650px) {
  .memory-filters {
    grid-template-columns: 1fr;
  }
}
@media (forced-colors: active) {
  .chip,
  .chip-clear {
    border-color: ButtonText;
  }
}
</style>
