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
import { ref } from "vue";
import UiButton from "../ui/UiButton.vue";
import { useI18nStore } from "../../stores/i18n";

// Presentation only: one visual grammar for the Strategies and Executions filters. The parent owns
// the fields, what they mean, and when they apply.
const props = withDefaults(
  defineProps<{
    label: string;
    /** How many advanced filters are active; shown on the trigger as "Filters (n)". */
    advancedCount?: number;
    hasAdvanced?: boolean;
    resultLabel?: string;
    canReset?: boolean;
  }>(),
  { advancedCount: 0, hasAdvanced: false, resultLabel: "", canReset: false },
);
const emit = defineEmits<{ reset: []; submit: [] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const advancedOpen = ref(props.advancedCount > 0);
</script>

<template>
  <form class="filter-bar" :aria-label="label" @submit.prevent="emit('submit')">
    <div class="filter-row">
      <div class="filter-search"><slot name="search" /></div>
      <div class="filter-primary"><slot name="primary" /></div>
      <UiButton
        v-if="hasAdvanced"
        :label="
          advancedCount
            ? i18n.tf('pipelines.filters_active', 'Filters ({count})', { count: advancedCount })
            : t('pipelines.filters', 'Filters')
        "
        :expanded="advancedOpen"
        @click="advancedOpen = !advancedOpen"
      />
      <div v-if="$slots.actions" class="filter-actions"><slot name="actions" /></div>
    </div>
    <div v-if="hasAdvanced && advancedOpen" class="filter-advanced">
      <slot name="advanced" />
    </div>
    <div v-if="resultLabel || canReset" class="filter-summary">
      <span v-if="resultLabel" role="status">{{ resultLabel }}</span>
      <UiButton
        v-if="canReset"
        variant="ghost"
        size="small"
        :label="t('pipelines.reset_filters', 'Reset')"
        @click="emit('reset')"
      />
    </div>
  </form>
</template>

<style scoped>
.filter-bar {
  display: grid;
  gap: var(--space-2);
}
.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--space-2);
}
.filter-search {
  flex: 1 1 14rem;
  min-width: 0;
}
.filter-primary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.filter-advanced {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-inset);
}
.filter-summary {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.filter-bar :deep(label) {
  display: grid;
  gap: 2px;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
}
.filter-bar :deep(.control) {
  width: 100%;
  min-height: var(--control-height);
}
</style>
