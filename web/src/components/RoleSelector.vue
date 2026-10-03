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
export interface RoleChoice {
  id: string;
  name: string;
  kind: string;
  assigned: string;
}

const props = defineProps<{
  label: string;
  choices: RoleChoice[];
  modelValue: string;
  disabled?: boolean;
}>();

const emit = defineEmits<{ "update:modelValue": [id: string] }>();
</script>

<template>
  <nav class="role-selector" :aria-label="props.label">
    <p class="roles-list-head">{{ props.label }}</p>
    <div class="roles-list-items">
      <button
        v-for="choice in props.choices"
        :key="choice.id"
        type="button"
        class="role-list-item"
        :class="{ active: props.modelValue === choice.id }"
        :aria-pressed="props.modelValue === choice.id"
        :disabled="props.disabled"
        @click="emit('update:modelValue', choice.id)"
      >
        <span>
          <b>{{ choice.name }}</b>
          <small>{{ choice.kind }} · {{ choice.assigned }}</small>
        </span>
      </button>
    </div>
  </nav>
</template>

<style scoped>
.role-selector {
  min-width: 0;
}
.roles-list-head {
  margin: 0;
  padding: 14px 14px 6px;
  font-size: 0.8125rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
}
.roles-list-items {
  display: grid;
  gap: 4px;
  padding: 0 8px 10px;
}
.role-list-item {
  width: 100%;
  border: 0;
  background: transparent;
  border-radius: var(--radius-control);
  padding: 11px 12px;
  text-align: left;
  color: var(--text-primary);
  cursor: pointer;
}
.role-list-item:hover:not(:disabled) {
  background: var(--surface-hover);
}
.role-list-item.active {
  background: var(--surface-selected);
  color: var(--accent-fg);
}
.role-list-item:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}
.role-list-item span {
  display: grid;
  gap: 2px;
}
.role-list-item b {
  font-size: 0.875rem;
}
.role-list-item small {
  font-size: 0.8125rem;
  color: var(--text-tertiary);
  line-height: 1.4;
}
.role-list-item:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
@media (max-width: 900px) {
  .roles-list-items {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 560px) {
  .roles-list-items {
    grid-template-columns: 1fr;
  }
}
@media (forced-colors: active) {
  .role-list-item:focus-visible {
    outline-color: Highlight;
  }
  .role-list-item.active {
    outline: 1px solid Highlight;
  }
}
</style>
