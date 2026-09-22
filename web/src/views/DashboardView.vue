<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { nextTick, onMounted } from "vue";
import * as runtime from "../runtime/runtimeBridge";

async function renderDashboard() {
  await nextTick();
  const main = document.querySelector<HTMLElement>("#main");
  if (!main) return;
  await runtime.renderDashboard(main);
  runtime.enhanceCollapsibles(main);
}

onMounted(() => {
  void renderDashboard();
});
</script>

<template>
  <main id="main" class="runtime-surface" aria-live="polite"></main>
</template>
