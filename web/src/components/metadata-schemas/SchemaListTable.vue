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
import { useSchemaCopy } from "../../composables/useSchemaCopy";
import type { SchemaSummary } from "../../api/metadataSchemas";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

// Schema selection is navigation, not tabular analysis. Keep the library compact and make
// the selected schema explicit without attaching click behavior to non-interactive rows.
defineProps<{
  items: SchemaSummary[];
  selectedId: string;
  /** Name of the unsaved draft, or "" when there is none. */
  unsavedName: string;
}>();
const emit = defineEmits<{ select: [id: string] }>();
const { t } = useSchemaCopy();
</script>

<template>
  <nav class="schema-list" :aria-label="t('saved_schemas', 'Saved schemas')">
    <ul>
      <li v-if="unsavedName" class="schema-item is-new selected" aria-current="page">
        <div class="schema-item-main">
          <strong>{{ unsavedName }}</strong>
          <UiStatusBadge tone="warning" :label="t('unsaved', 'Not saved yet')" />
        </div>
      </li>

      <li
        v-for="item in items"
        :key="item.id"
        class="schema-item"
        :class="{ selected: item.id === selectedId && !unsavedName }"
      >
        <button
          type="button"
          class="schema-name"
          :aria-current="item.id === selectedId && !unsavedName ? 'page' : undefined"
          @click="emit('select', item.id)"
        >
          <span class="schema-item-main">
            <strong>{{ item.name }}</strong>
            <UiStatusBadge
              v-if="item.builtin"
              tone="info"
              :show-dot="false"
              :label="t('builtin', 'Built in')"
            />
          </span>
          <span v-if="item.description" class="schema-description">{{ item.description }}</span>
          <span class="schema-meta">
            <span>v{{ item.schema_version || "1.0.0" }}</span>
            <span>{{ t("col_groups", "Groups") }}: {{ item.groups.length }}</span>
            <span>{{ t("col_fields", "Fields") }}: {{ item.field_count }}</span>
          </span>
        </button>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.schema-list {
  overflow: auto;
  max-block-size: min(32rem, 62vh);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.schema-list ul {
  margin: 0;
  padding: 0;
  list-style: none;
}
.schema-item + .schema-item {
  border-block-start: 1px solid var(--border-subtle);
}
.schema-item.selected {
  box-shadow: inset 3px 0 0 var(--accent-fg);
  background: var(--surface-selected);
}
.schema-name {
  display: grid;
  gap: var(--space-2);
  inline-size: 100%;
  min-block-size: var(--control-height);
  padding: var(--space-3);
  border: 0;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  text-align: start;
  cursor: pointer;
}
.schema-name:hover {
  background: var(--surface-hover);
}
.schema-name:focus-visible {
  position: relative;
  z-index: 1;
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: calc(var(--focus-ring-offset) * -1);
}
.schema-item-main {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}
.schema-item-main strong {
  font-size: var(--fs-base);
  font-weight: var(--fw-bold);
}
.schema-description {
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.schema-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-3);
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  font-variant-numeric: tabular-nums;
}
.is-new {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
}
</style>
