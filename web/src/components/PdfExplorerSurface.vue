<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { nextTick, onMounted, onUpdated } from "vue";
import * as runtime from "../runtime/runtime.js";

onMounted(async () => {
  await nextTick();
  await runtime.renderView();
});

onUpdated(() => {
  runtime.decorateDisabledControls(document.querySelector("#main") ?? document);
});
</script>

<template>
  <main id="main" class="runtime-surface" aria-live="polite"></main>
</template>
