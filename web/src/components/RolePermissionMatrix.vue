<script setup lang="ts">
import { computed } from "vue";
import type { CapabilityDefinition } from "../api/auth";

const props = defineProps<{ capabilities: CapabilityDefinition[]; modelValue: string[]; disabled?: boolean }>();
const emit = defineEmits<{ "update:modelValue": [value: string[]] }>();
const selected = computed(() => new Set(props.modelValue));
const groups = computed(() => {
  const byCategory = new Map<string, CapabilityDefinition[]>();
  for (const capability of props.capabilities) {
    const list = byCategory.get(capability.category) || [];
    list.push(capability);
    byCategory.set(capability.category, list);
  }
  return [...byCategory.entries()].map(([category, items]) => ({ category, items }));
});
function toggle(id: string, checked: boolean) {
  const next = new Set(props.modelValue);
  checked ? next.add(id) : next.delete(id);
  emit("update:modelValue", [...next]);
}
</script>

<template>
  <div class="permission-matrix">
    <fieldset v-for="group in groups" :key="group.category" class="permission-group">
      <legend>{{ group.category }}</legend>
      <label v-for="capability in group.items" :key="capability.id" class="permission-row" :class="{locked: !capability.configurable}">
        <input
          type="checkbox"
          :checked="selected.has(capability.id)"
          :disabled="disabled || !capability.configurable"
          :aria-describedby="`permission-${capability.id.replaceAll('.', '-')}`"
          @change="toggle(capability.id, ($event.target as HTMLInputElement).checked)"
        >
        <span>
          <b>{{ capability.label }}</b>
          <small :id="`permission-${capability.id.replaceAll('.', '-')}`">{{ capability.description }}</small>
          <code>{{ capability.id }}</code>
        </span>
      </label>
    </fieldset>
  </div>
</template>
