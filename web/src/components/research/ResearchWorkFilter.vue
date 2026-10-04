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
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";

const props = withDefaults(
  defineProps<{
    modelValue: string[];
    works: string[];
    legendId?: string;
  }>(),
  {
    legendId: "research-work-filter-legend",
  },
);
const emit = defineEmits<{ "update:modelValue": [value: string[]] }>();
const i18n = useI18nStore();

const options = computed(() =>
  [...new Set([...(props.works || []), ...(props.modelValue || [])].map((work) => String(work).trim()))]
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b, i18n.locale)),
);
const selected = computed(() => new Set(props.modelValue || []));
const summary = computed(() =>
  props.modelValue.length
    ? i18n.tf(
        props.modelValue.length === 1
          ? "research.work_filter_selected_one"
          : "research.work_filter_selected_many",
        { count: props.modelValue.length },
      )
    : i18n.t("research.work_filter_all"),
);

function toggle(work: string, checked: boolean) {
  const next = new Set(props.modelValue || []);
  checked ? next.add(work) : next.delete(work);
  emit("update:modelValue", [...next]);
}
</script>

<template>
  <fieldset class="research-work-filter" :aria-describedby="`${legendId}-help ${legendId}-status`">
    <legend :id="legendId">{{ i18n.t("research.work_filter_title") }}</legend>
    <p :id="`${legendId}-help`">{{ i18n.t("research.work_filter_help") }}</p>
    <div class="research-work-filter-toolbar">
      <span :id="`${legendId}-status`" role="status" aria-live="polite" aria-atomic="true">
        {{ summary }}
      </span>
      <UiButton
        v-if="modelValue.length"
        size="small"
        :label="i18n.t('research.work_filter_clear')"
        @click="emit('update:modelValue', [])"
      />
    </div>
    <div v-if="options.length" class="research-work-filter-options">
      <label v-for="work in options" :key="work">
        <input
          type="checkbox"
          :checked="selected.has(work)"
          @change="toggle(work, ($event.target as HTMLInputElement).checked)"
        />
        <span>{{ work }}</span>
      </label>
    </div>
    <p v-else class="research-work-filter-empty">
      {{ i18n.t("research.work_filter_unavailable") }}
    </p>
  </fieldset>
</template>

<style scoped>
.research-work-filter {
  min-width: 0;
}
.research-work-filter > p {
  margin: 0.375rem 0 0.75rem;
  color: var(--muted);
  line-height: 1.45;
}
.research-work-filter-toolbar {
  display: flex;
  min-height: 2.75rem;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}
.research-work-filter-toolbar > span {
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 700;
}
.research-work-filter-options {
  display: grid;
  max-block-size: 18rem;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: var(--radius-control, 0.625rem);
  background: var(--surface-control, var(--card));
}
.research-work-filter-options label {
  display: grid;
  grid-template-columns: 1.25rem minmax(0, 1fr);
  min-block-size: 2.75rem;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem 0.75rem;
  border-block-start: 1px solid var(--line);
  cursor: pointer;
}
.research-work-filter-options label:first-child {
  border-block-start: 0;
}
.research-work-filter-options input {
  inline-size: 1.125rem;
  block-size: 1.125rem;
}
.research-work-filter-options span {
  overflow-wrap: anywhere;
}
.research-work-filter-empty {
  padding: 0.75rem;
  border: 1px dashed var(--line);
  border-radius: var(--radius-control, 0.625rem);
}
</style>
