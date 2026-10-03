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
const props = withDefaults(
  defineProps<{
    code?: string;
    symbol?: string;
    label?: string;
    size?: "small" | "medium" | "large";
  }>(),
  { code: "", symbol: "", label: "", size: "medium" },
);
function canonical() {
  return props.symbol || "🌐";
}
</script>
<template>
  <span
    class="language-flag-component"
    :class="`size-${props.size}`"
    role="img"
    :aria-label="props.label || props.code || 'Language'"
    >{{ canonical() }}</span
  >
</template>
