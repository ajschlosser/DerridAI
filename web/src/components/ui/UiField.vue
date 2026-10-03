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
import UiTooltip from "./UiTooltip.vue";

const props = withDefaults(
  defineProps<{
    label: string;
    hint?: string;
    tooltip?: string;
    tooltipLabel?: string;
    error?: string;
    wide?: boolean;
    required?: boolean;
    persistence?: string;
  }>(),
  {
    hint: "",
    tooltip: "",
    tooltipLabel: "",
    error: "",
    wide: false,
    required: false,
    persistence: "",
  },
);

const generatedId = useId();
const hintId = computed(() => `${generatedId}-hint`);
const errorId = computed(() => `${generatedId}-error`);
const describedby = computed(
  () =>
    [props.hint ? hintId.value : "", props.error ? errorId.value : ""].filter(Boolean).join(" ") ||
    undefined,
);
</script>
<template>
  <label class="ui-field" :class="{ wide, invalid: Boolean(error) }">
    <span class="ui-field-label">
      {{ label }}
      <UiTooltip
        v-if="tooltip"
        :text="tooltip"
        :label="tooltipLabel || `${label}: ${tooltip}`"
        placement="bottom"
      />
      <span v-if="required" class="ui-field-required" aria-hidden="true"> *</span>
      <span v-if="persistence" class="ui-field-persist">{{ persistence }}</span>
    </span>
    <slot :describedby="describedby" :invalid="Boolean(error)" />
    <span v-if="hint" :id="hintId" class="ui-field-hint">{{ hint }}</span>
    <span v-if="error" :id="errorId" class="ui-field-error" role="alert">{{ error }}</span>
  </label>
</template>
<style scoped>
.ui-field {
  display: grid;
  gap: 6px;
  min-width: 0;
}
.ui-field.wide {
  grid-column: 1/-1;
}
.ui-field-label {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--text-primary);
}
.ui-field-required {
  color: var(--tone-danger-fg);
}
.ui-field-persist {
  margin-left: auto;
  font-weight: 650;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.ui-field-hint {
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--text-tertiary);
}
.ui-field-error {
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--tone-danger-fg);
  font-weight: 700;
}
.ui-field.invalid :deep(input),
.ui-field.invalid :deep(select),
.ui-field.invalid :deep(textarea) {
  border-color: var(--tone-danger-border);
}
</style>
