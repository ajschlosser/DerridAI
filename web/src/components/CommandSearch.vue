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
    /><kbd>{{ shortcut }}</kbd>
  </form>
</template>
