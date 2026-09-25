<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import type { SaveStatus } from "../../domain/settings";

defineProps<{ status: SaveStatus; label: string; detail?: string }>();
</script>
<template>
  <p class="settings-save-state" :data-status="status" role="status">
    <span class="settings-save-mark" aria-hidden="true"></span>
    <span>{{ label }}</span>
    <span v-if="detail" class="settings-save-detail">{{ detail }}</span>
  </p>
</template>
<style scoped>
.settings-save-state {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  margin: 0;
  padding: 4px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--panel-2);
  color: var(--text);
  font-size: 0.8125rem;
  font-weight: 700;
}
.settings-save-mark {
  inline-size: 8px;
  block-size: 8px;
  border-radius: 50%;
  background: var(--muted);
}
.settings-save-state[data-status="dirty"] {
  border-color: var(--warn);
  background: var(--warn-bg);
  color: var(--warn);
}
.settings-save-state[data-status="dirty"] .settings-save-mark {
  background: var(--warn);
}
.settings-save-state[data-status="saving"] {
  border-color: var(--line-strong);
}
.settings-save-state[data-status="success"],
.settings-save-state[data-status="saved"] {
  border-color: var(--ok);
  color: var(--ok);
  background: var(--accent-soft);
}
.settings-save-state[data-status="success"] .settings-save-mark,
.settings-save-state[data-status="saved"] .settings-save-mark {
  background: var(--ok);
}
.settings-save-state[data-status="failed"] {
  border-color: var(--danger);
  background: var(--danger-bg);
  color: var(--danger);
}
.settings-save-state[data-status="failed"] .settings-save-mark {
  background: var(--danger);
}
.settings-save-state[data-status="readonly"] {
  color: var(--muted);
}
.settings-save-detail {
  font-weight: 650;
  color: var(--muted);
}
</style>
