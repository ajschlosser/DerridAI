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
import { computed } from "vue";

const props = defineProps<{ text: string; query?: string }>();

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Splits text into plain and matching runs; the text itself is never altered. */
const segments = computed(() => {
  const terms = (props.query || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .sort((a, b) => b.length - a.length)
    .map(escapeRegExp);
  if (!terms.length) return [{ text: props.text, match: false }];
  const pattern = new RegExp(`(${terms.join("|")})`, "gi");
  return props.text
    .split(pattern)
    .filter(Boolean)
    .map((part, index) => ({ text: part, match: index % 2 === 1 }));
});
</script>

<template>
  <template v-for="(segment, index) in segments" :key="index">
    <mark v-if="segment.match" class="help-highlight">{{ segment.text }}</mark>
    <template v-else>{{ segment.text }}</template>
  </template>
</template>

<style scoped>
.help-highlight {
  padding: 0 1px;
  border-radius: 2px;
  background: var(--mark-bg);
  color: var(--mark-fg);
}
</style>
