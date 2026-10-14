<!--
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
 -->

<script setup lang="ts">
import "../../styles/form-controls.css";

const props = withDefaults(
  defineProps<{
    modelValue?: string | number | null;
    type?: string;
    invalid?: boolean;
  }>(),
  {
    modelValue: "",
    type: "text",
    invalid: false,
  },
);
const emit = defineEmits<{ "update:modelValue": [value: string | number | null] }>();

function onInput(event: Event) {
  const input = event.target as HTMLInputElement;
  if (props.type === "number") {
    emit("update:modelValue", input.value === "" ? null : input.valueAsNumber);
    return;
  }
  emit("update:modelValue", input.value);
}
</script>

<template>
  <input
    class="ui-control ui-input"
    :type="type"
    :value="modelValue ?? ''"
    :aria-invalid="invalid ? 'true' : undefined"
    @input="onInput"
  />
</template>
