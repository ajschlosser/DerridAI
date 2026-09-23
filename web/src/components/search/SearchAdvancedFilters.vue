<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { SchemaSummary } from "../../api/metadataSchemas";
import type { SearchFilter } from "../../types/search";
import type { SearchFilterFieldOption } from "../../domain/searchFilterSchema";

defineProps<{
  filters: SearchFilter[];
  fields: SearchFilterFieldOption[];
  schemas: SchemaSummary[];
  schemaId: string;
  associatedSchemaId: string;
  field: string;
  op: string;
  value: string;
  ops: Array<[string, string, string]>;
  suggestions: string[];
}>();
const emit = defineEmits<{
  "update:field": [value: string];
  "update:op": [value: string];
  "update:value": [value: string];
  schema: [id: string];
  fieldChange: [];
  add: [];
  remove: [filter: SearchFilter];
}>();
const i18n = useI18nStore();
function valueRequired(op: string) {
  return !["empty", "notempty"].includes(op);
}
</script>

<template>
  <section class="search-rule-builder" aria-labelledby="search-rule-builder-title">
    <header class="search-rule-builder-head">
      <div>
        <p class="section-label">{{ i18n.t("search.advanced_filters") }}</p>
        <h2 id="search-rule-builder-title">
          {{ i18n.t("search.filter_match_all") }}
        </h2>
      </div>
      <label class="search-rule-schema">
        <span>{{ i18n.t("search.filter_schema") }}</span>
        <select
          class="control"
          :value="schemaId"
          @change="emit('schema', ($event.target as HTMLSelectElement).value)"
        >
          <option v-for="schema in schemas" :key="schema.id" :value="schema.id">
            {{ schema.name
            }}{{
              schema.id === associatedSchemaId
                ? ` · ${i18n.t("search.filter_schema_associated")}`
                : ""
            }}
          </option>
        </select>
      </label>
    </header>
    <p class="search-rule-help">
      {{
        i18n.t("search.advanced_filter_help")
      }}
    </p>
    <ol class="search-rule-list">
      <li v-for="(filter, index) in filters" :key="filter.id" class="search-rule-row is-applied">
        <span class="search-rule-join">{{
          index === 0 ? i18n.t("search.filter_where") : i18n.t("search.filter_and")
        }}</span>
        <span class="search-rule-token">{{ filter.field_label }}</span>
        <span class="search-rule-token is-muted">{{ filter.op_label }}</span>
        <span class="search-rule-token is-value">{{ filter.value || "—" }}</span>
        <button
          type="button"
          class="btn search-rule-remove"
          :aria-label="
            i18n.tf('search.remove_condition_named', {
              field: filter.field_label,
              op: filter.op_label,
              value: filter.value,
            })
          "
          @click="emit('remove', filter)"
        >
          <AppIcon name="close" />
        </button>
      </li>
      <li class="search-rule-row is-compose">
        <span class="search-rule-join">{{
          filters.length
            ? i18n.t("search.filter_and")
            : i18n.t("search.filter_where")
        }}</span>
        <label>
          <span class="sr-only">{{ i18n.t("search.field") }}</span>
          <select
            class="control"
            :value="field"
            @change="
              emit('update:field', ($event.target as HTMLSelectElement).value);
              emit('fieldChange');
            "
          >
            <option v-for="item in fields" :key="item.key" :value="item.key">
              {{ item.label }}
            </option>
          </select>
        </label>
        <label>
          <span class="sr-only">{{ i18n.t("search.condition") }}</span>
          <select
            class="control"
            :value="op"
            @change="emit('update:op', ($event.target as HTMLSelectElement).value)"
          >
            <option v-for="[code, key, fallback] in ops" :key="code" :value="code">
              {{ i18n.t(key, fallback) }}
            </option>
          </select>
        </label>
        <label>
          <span class="sr-only">{{ i18n.t("search.value") }}</span>
          <input
            class="control"
            :value="value"
            :list="`search-suggestions-${field}`"
            :disabled="!valueRequired(op)"
            :placeholder="i18n.t('search.filter_value_placeholder')"
            @input="emit('update:value', ($event.target as HTMLInputElement).value)"
            @keydown.enter.prevent="emit('add')"
          />
          <datalist :id="`search-suggestions-${field}`">
            <option v-for="item in suggestions" :key="item" :value="item"></option>
          </datalist>
        </label>
        <button
          type="button"
          class="btn primary search-add-filter"
          :disabled="valueRequired(op) && !value.trim()"
          @click="emit('add')"
        >
          <AppIcon name="plus" />{{ i18n.t("research.add_filter") }}
        </button>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.search-rule-builder {
  display: grid;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding: var(--space-5) var(--space-5) var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  box-shadow: var(--shadow-card);
}
.search-rule-builder-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}
.search-rule-builder-head h2 {
  margin: 4px 0 0;
  color: var(--text-primary);
  font-size: var(--fs-md);
  font-weight: var(--fw-semibold);
  letter-spacing: -0.02em;
  line-height: var(--lh-tight);
}
.search-rule-schema {
  display: grid;
  gap: 4px;
  min-width: min(16rem, 100%);
}
.search-rule-schema > span {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.search-rule-schema .control {
  min-height: var(--control-height);
}
.search-rule-help {
  max-width: var(--measure);
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.search-rule-list {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.search-rule-row {
  display: grid;
  grid-template-columns: 4.5rem minmax(8.5rem, 1.05fr) minmax(7.5rem, 0.85fr) minmax(
      10rem,
      1.4fr
    ) auto;
  gap: var(--space-2);
  align-items: center;
  min-height: 48px;
  padding: 6px 8px 6px 6px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.search-rule-row.is-compose {
  background: var(--surface-card);
}
.search-rule-join {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  text-align: end;
  padding-inline: 8px;
}
.search-rule-token {
  min-height: var(--control-height);
  display: flex;
  align-items: center;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  background: var(--surface-card);
  color: var(--text-primary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.search-rule-token.is-muted {
  color: var(--text-secondary);
  font-weight: var(--fw-regular);
}
.search-rule-token.is-value {
  font-family: var(--font-reading);
}
.search-rule-row .control {
  min-height: var(--control-height);
  width: 100%;
}
.search-rule-remove,
.search-add-filter {
  min-height: var(--control-height);
}
.search-rule-remove {
  display: inline-grid;
  place-items: center;
  min-width: var(--control-height);
  padding: 0;
}
.search-rule-remove :deep(svg) {
  width: 16px;
  height: 16px;
}
.search-add-filter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding-inline: 12px;
  white-space: nowrap;
}
@media (max-width: 900px) {
  .search-rule-row {
    grid-template-columns: 4.5rem minmax(0, 1fr);
  }
  .search-rule-row > :not(.search-rule-join) {
    grid-column: 2;
  }
}
</style>
