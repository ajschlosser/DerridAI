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
import AppIcon from "./AppIcon.vue";
import UiButton from "./ui/UiButton.vue";
const props = withDefaults(
  defineProps<{
    title: string;
    description: string;
    actionLabel?: string;
    icon?: string;
    iconTone?: "accent" | "neutral";
  }>(),
  { actionLabel: "", icon: "record", iconTone: "accent" },
);
const emit = defineEmits<{ action: [] }>();
</script>
<template>
  <section class="accessible-empty-state" role="status" aria-live="polite">
    <span class="accessible-empty-icon" :class="`tone-${props.iconTone}`" aria-hidden="true"
      ><AppIcon :name="props.icon"
    /></span>
    <h2>{{ props.title }}</h2>
    <p>{{ props.description }}</p>
    <UiButton
      v-if="props.actionLabel"
      :label="props.actionLabel"
      variant="primary"
      @click="emit('action')"
    />
  </section>
</template>
