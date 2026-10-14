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
