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
