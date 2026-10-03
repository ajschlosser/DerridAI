<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026 Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.
-->

<script setup lang="ts">
defineProps<{
  modelValue: string;
  value: string;
  name: string;
  title: string;
  description: string;
  badge?: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();
</script>

<template>
  <label class="site-radio-option">
    <input
      :checked="modelValue === value"
      type="radio"
      :name="name"
      :value="value"
      @change="emit('update:modelValue', value)"
    />
    <span class="site-radio-copy">
      <span class="site-radio-title">
        <strong>{{ title }}</strong>
        <span v-if="badge" class="site-radio-badge">{{ badge }}</span>
      </span>
      <small>{{ description }}</small>
    </span>
  </label>
</template>

<style scoped>
.site-radio-option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.7rem;
  align-items: start;
  padding: 0.72rem 0.8rem;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--surface-raised);
  cursor: pointer;
}

.site-radio-option:has(input:checked) {
  border-color: var(--ui-accent);
  box-shadow: 0 0 0 1px var(--ui-accent);
}

.site-radio-option input {
  width: 1rem;
  height: 1rem;
  margin-top: 0.22rem;
}

.site-radio-copy {
  display: grid;
  gap: 0.22rem;
  min-width: 0;
}

.site-radio-title {
  display: flex;
  gap: 0.5rem;
  align-items: baseline;
  flex-wrap: wrap;
}

.site-radio-option small {
  color: var(--muted);
  line-height: 1.45;
}

.site-radio-badge {
  padding: 0.12rem 0.42rem;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text);
  font-size: 0.72rem;
  font-weight: 700;
}
</style>
