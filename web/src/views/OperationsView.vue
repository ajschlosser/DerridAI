<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { nextTick, onMounted } from "vue";
import * as runtime from "../runtime/runtime.js";

onMounted(async () => {
  await runtime.refreshJobs?.({ rerender: true });
  await nextTick();
  runtime.mountOperationsPanelHost();
});
</script>

<template>
  <main class="vue-native-page operations-page" aria-labelledby="ops-heading">
    <div id="operationsPanelHost"></div>
  </main>
</template>

<style scoped>
.operations-page {
  min-width: 0;
}
</style>
