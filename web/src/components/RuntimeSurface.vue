<script setup lang="ts">
import { nextTick, onMounted, onUpdated } from "vue";
import * as runtime from "../runtime/runtime.js";

const props = withDefaults(defineProps<{ preview?: boolean }>(), {
  preview: false,
});

async function renderRuntime() {
  // Storybook uses preview mode so it can document the Vue/runtime boundary
  // without booting IndexedDB, PDF.js, polling, or API-backed renderers.
  if (props.preview) return;
  await nextTick();
  await runtime.renderView();
}

onMounted(renderRuntime);
onUpdated(() => {
  if (props.preview) return;
  runtime.decorateDisabledControls(document.querySelector("#main") ?? document);
});
</script>

<template>
  <main id="main" class="runtime-surface" aria-live="polite">
    <slot v-if="props.preview" />
  </main>
</template>
