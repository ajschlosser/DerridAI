<script setup lang="ts">
import { computed } from "vue";
const props = withDefaults(defineProps<{ text?: string; query?: string }>(), {
  text: "",
  query: "",
});
const parts = computed(() => {
  const text = String(props.text || "");
  const terms = [
    ...new Set(
      String(props.query || "")
        .trim()
        .split(/\s+/)
        .filter((term) => term.length > 1),
    ),
  ];
  if (!terms.length) return [{ text, match: false }];
  const escaped = terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const re = new RegExp(`(${escaped.join("|")})`, `gi`);
  return text
    .split(re)
    .filter(Boolean)
    .map((part) => ({
      text: part,
      match: terms.some(
        (term) => part.localeCompare(term, undefined, { sensitivity: "accent" }) === 0,
      ),
    }));
});
</script>
<template>
  <span
    ><template v-for="(part, index) in parts" :key="index"
      ><mark v-if="part.match">{{ part.text }}</mark
      ><template v-else>{{ part.text }}</template></template
    ></span
  >
</template>
