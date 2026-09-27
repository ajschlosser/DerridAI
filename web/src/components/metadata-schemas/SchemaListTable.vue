<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useSchemaCopy } from "../../composables/useSchemaCopy";
import type { SchemaSummary } from "../../api/metadataSchemas";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

// The saved schemas as a compact table, in the same dense-table idiom as Records. An unsaved
// draft (a new schema or a copy) appears as a pending first row so it is never mistaken for a saved one.
defineProps<{
  items: SchemaSummary[];
  selectedId: string;
  /** Name of the unsaved draft, or "" when there is none. */
  unsavedName: string;
}>();
const emit = defineEmits<{ select: [id: string] }>();
const { t, tf } = useSchemaCopy();
</script>

<template>
  <div class="schema-list ui-table-scroll">
    <table class="schema-table ui-table" :aria-label="t('saved_schemas', 'Saved schemas')">
      <thead>
        <tr>
          <th scope="col">{{ t("col_name", "Schema") }}</th>
          <th scope="col" class="num">{{ t("col_version", "Version") }}</th>
          <th scope="col" class="num">{{ t("col_groups", "Groups") }}</th>
          <th scope="col" class="num">{{ t("col_fields", "Fields") }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="unsavedName" class="schema-row is-new selected" aria-current="true">
          <td>
            <b>{{ unsavedName }}</b>
            <UiStatusBadge tone="warning" :label="t('unsaved', 'Not saved yet')" />
          </td>
          <td class="num">—</td>
          <td class="num">—</td>
          <td class="num">—</td>
        </tr>
        <tr
          v-for="item in items"
          :key="item.id"
          class="schema-row"
          :class="{ selected: item.id === selectedId && !unsavedName }"
          @click="emit('select', item.id)"
        >
          <td>
            <button
              type="button"
              class="schema-name"
              :aria-current="item.id === selectedId && !unsavedName ? 'true' : undefined"
              @click.stop="emit('select', item.id)"
            >
              {{ item.name }}
            </button>
            <UiStatusBadge
              v-if="item.builtin"
              tone="info"
              :show-dot="false"
              :label="t('builtin', 'Built in')"
            />
            <small v-if="item.description" class="schema-description">{{ item.description }}</small>
          </td>
          <td class="num">v{{ item.schema_version || "1.0.0" }}</td>
          <td class="num">{{ item.groups.length || "—" }}</td>
          <td class="num" :title="tf('field_count', { count: item.field_count })">
            {{ item.field_count }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.schema-list {
  max-block-size: 15rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-overlay);
  background: var(--surface-card);
}
.schema-table {
  inline-size: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.8125rem;
}
.schema-table th,
.schema-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-subtle);
  text-align: start;
  vertical-align: middle;
}
.schema-table thead th {
  position: sticky;
  inset-block-start: 0;
  z-index: 1;
}
.schema-table tbody tr:last-child td {
  border-bottom: 0;
}
.schema-table .num {
  inline-size: 1%;
  white-space: nowrap;
  text-align: end;
  font-variant-numeric: tabular-nums;
}
.schema-row {
  cursor: pointer;
}
.schema-row.selected td:first-child {
  box-shadow: inset 3px 0 0 var(--accent-fg);
}
.schema-name {
  margin-inline-end: 8px;
  padding: 2px 4px;
  border: 0;
  border-radius: var(--radius-control);
  background: none;
  color: var(--text-primary);
  font: inherit;
  font-weight: var(--fw-semibold);
  text-align: start;
  cursor: pointer;
}
.schema-name:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.schema-description {
  display: block;
  padding-inline: 4px;
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
}
.is-new b {
  margin-inline-end: 8px;
  padding-inline: 4px;
}
</style>
