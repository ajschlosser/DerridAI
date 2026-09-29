<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
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
