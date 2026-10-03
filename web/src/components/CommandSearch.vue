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
import { ref } from "vue";
import AppIcon from "./AppIcon.vue";
// The handler in App.vue accepts Ctrl+K and ⌘K; advertise the one this platform uses.
withDefaults(defineProps<{ placeholder?: string; shortcut?: string }>(), {
  placeholder: "Search…",
  shortcut: () =>
    typeof navigator !== "undefined" &&
    /Mac|iPhone|iPad/i.test(navigator.platform || navigator.userAgent || "")
      ? "⌘K"
      : "Ctrl K",
});
const model = defineModel<string>({ default: "" });
const emit = defineEmits<{ submit: [] }>();
const input = ref<HTMLInputElement | null>(null);
function focus() {
  input.value?.focus();
  input.value?.select();
}
defineExpose({ focus });
</script>
<template>
  <form class="shell-command-search" @submit.prevent="emit('submit')">
    <AppIcon name="search" /><input
      ref="input"
      v-model="model"
      :placeholder="placeholder"
      type="search"
      autocomplete="off"
    /><kbd v-if="shortcut">{{ shortcut }}</kbd>
  </form>
</template>
