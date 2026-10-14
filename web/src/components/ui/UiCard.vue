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
withDefaults(
  defineProps<{ as?: "section" | "article" | "div"; padded?: boolean; headingId?: string }>(),
  { as: "section", padded: true, headingId: "" },
);
</script>
<template>
  <component :is="as" class="ui-card" :class="{ padded }" :aria-labelledby="headingId || undefined"
    ><slot
  /></component>
</template>
<style scoped>
.ui-card {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}
.ui-card.padded {
  padding: var(--space-5);
}
</style>
