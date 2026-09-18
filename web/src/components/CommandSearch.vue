<script setup lang="ts">
import { ref } from "vue";
import AppIcon from "./AppIcon.vue";
withDefaults(defineProps<{ placeholder?: string; shortcut?: string }>(), { placeholder: "Search…", shortcut: "⌘K" });
const model = defineModel<string>({ default: "" });
const emit = defineEmits<{ submit: [] }>();
const input = ref<HTMLInputElement | null>(null);
function focus() { input.value?.focus(); input.value?.select(); }
defineExpose({ focus });
</script>
<template><form class="shell-command-search" @submit.prevent="emit('submit')"><AppIcon name="search" /><input ref="input" v-model="model" :placeholder="placeholder" type="search" autocomplete="off"><kbd>{{ shortcut }}</kbd></form></template>
