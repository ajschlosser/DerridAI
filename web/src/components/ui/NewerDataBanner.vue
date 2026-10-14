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
import { useI18nStore } from "../../stores/i18n";

/** Tells a reader that newer server data exists without replacing what they are reading. */
defineProps<{ visible: boolean }>();
const emit = defineEmits<{ load: [] }>();
const i18n = useI18nStore();
</script>

<template>
  <div v-if="visible" class="newer-data-banner" role="status">
    <span>{{ i18n.t("realtime.newer_data") }}</span>
    <button type="button" class="newer-data-banner__action" @click="emit('load')">
      {{ i18n.t("realtime.load_newer") }}
    </button>
  </div>
</template>

<style scoped>
.newer-data-banner {
  display: flex;
  align-items: center;
  gap: var(--space-4, 0.75rem);
  padding: var(--space-3, 0.5rem) var(--space-4, 0.75rem);
  background: var(--surface-raised);
  border: 1px solid var(--border-strong, var(--border));
  border-radius: var(--radius-control);
  font-size: var(--fs-sm, 0.8125rem);
}
.newer-data-banner__action {
  margin-inline-start: auto;
}
</style>
