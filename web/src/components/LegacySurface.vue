<script setup lang="ts">
import { nextTick, onMounted, onUpdated } from "vue";
import * as runtime from "../legacy/runtime.js";

const props = withDefaults(defineProps<{ preview?: boolean }>(), {
  preview: false,
});

async function renderLegacy() {
  // Storybook uses preview mode so it can document the Vue/legacy boundary
  // without booting IndexedDB, PDF.js, polling, or API-backed renderers.
  if (props.preview) return;
  await nextTick();
  await runtime.renderView();
}

onMounted(renderLegacy);
onUpdated(() => {
  if (props.preview) return;
  runtime.decorateDisabledControls(document.querySelector("#main") ?? document);
});
</script>

<template>
  <main id="main" class="legacy-surface" aria-live="polite">
    <slot v-if="props.preview" />
  </main>
</template>
