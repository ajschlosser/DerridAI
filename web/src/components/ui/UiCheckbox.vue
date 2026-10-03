/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

<script setup lang="ts">
import { computed, useId } from "vue";
import "../../styles/form-controls.css";

const props = withDefaults(
  defineProps<{
    modelValue?: boolean;
    label: string;
    description?: string;
    disabled?: boolean;
    invalid?: boolean;
    inputId?: string;
    hideLabel?: boolean;
  }>(),
  {
    modelValue: false,
    description: "",
    disabled: false,
    invalid: false,
    inputId: "",
    hideLabel: false,
  },
);
const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();
const generatedId = useId();
const id = computed(() => props.inputId || generatedId);
const descriptionId = computed(() => (props.description ? `${id.value}-description` : undefined));
</script>

<template>
  <label class="ui-checkbox" :for="id" :data-disabled="disabled ? 'true' : undefined">
    <input
      :id="id"
      class="ui-checkbox-control"
      type="checkbox"
      :checked="modelValue"
      :disabled="disabled"
      :aria-invalid="invalid ? 'true' : undefined"
      :aria-describedby="descriptionId"
      @change="emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
    />
    <span class="ui-checkbox-copy" :class="{ 'sr-only': hideLabel && !description }">
      <span class="ui-checkbox-label" :class="{ 'sr-only': hideLabel && description }">{{ label }}</span>
      <span v-if="description" :id="descriptionId" class="ui-checkbox-description">{{ description }}</span>
    </span>
  </label>
</template>
