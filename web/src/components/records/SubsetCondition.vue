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
import { computed, useId } from "vue";
import { useI18nStore } from "../../stores/i18n";
import {
  SUBSET_OPERATORS,
  VALUELESS_OPERATORS,
  fieldHasSuggestions,
} from "../../domain/subsetExpression";

/** One filter condition: field, comparison and value, with a remove button. */
const props = defineProps<{
  fields: { key: string; label: string }[];
  /** Distinct values of the chosen field in the source, offered as suggestions. */
  suggestions: string[];
  /** Names this condition in labels, e.g. "item 2" or "condition 1 of item 3". */
  position: string;
}>();
const emit = defineEmits<{ remove: [] }>();
const field = defineModel<string>("field", { required: true });
const operator = defineModel<string>("operator", { required: true });
const value = defineModel<string>("value", { required: true });

const i18n = useI18nStore();
const listId = `subset-values-${useId()}`;
const valueless = computed(() => VALUELESS_OPERATORS.has(operator.value));
const suggested = computed(() => !valueless.value && fieldHasSuggestions(field.value));

function setOperator(next: string) {
  operator.value = next;
  if (VALUELESS_OPERATORS.has(next)) value.value = "";
}
</script>

<template>
  <div class="subset-condition">
    <select
      v-model="field"
      class="control"
      :aria-label="i18n.tf('subset.field_label', { position: props.position })"
    >
      <option v-for="item in props.fields" :key="item.key" :value="item.key">
        {{ item.label }}
      </option>
    </select>
    <select
      class="control"
      :value="operator"
      :aria-label="i18n.tf('subset.operator_label', { position: props.position })"
      @change="setOperator(($event.target as HTMLSelectElement).value)"
    >
      <option v-for="item in SUBSET_OPERATORS" :key="item" :value="item">
        {{ i18n.t(`subset.operator.${item}`, item) }}
      </option>
    </select>
    <input
      v-model="value"
      class="control"
      autocomplete="off"
      :disabled="valueless"
      :placeholder="valueless ? i18n.t('subset.no_value') : i18n.t('subset.value')"
      :list="suggested ? listId : undefined"
      :aria-label="i18n.tf('subset.value_label', { position: props.position })"
    />
    <datalist v-if="suggested" :id="listId">
      <option v-for="item in props.suggestions" :key="item" :value="item" />
    </datalist>
    <button
      type="button"
      class="btn danger"
      :aria-label="i18n.tf('subset.remove_condition_named', { position: props.position })"
      @click="emit('remove')"
    >
      {{ i18n.t("ui.remove") }}
    </button>
  </div>
</template>

<style scoped>
.subset-condition {
  display: grid;
  grid-template-columns: minmax(9rem, 1fr) minmax(9rem, 0.9fr) minmax(10rem, 1.3fr) auto;
  gap: var(--space-2);
  align-items: center;
}
@media (max-width: 760px) {
  .subset-condition {
    grid-template-columns: 1fr;
  }
}
</style>
