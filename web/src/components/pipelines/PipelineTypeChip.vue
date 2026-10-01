<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { dataTypeGlyph, dataTypeTone } from "../../domain/pipelineAnalysisPresentation";
import { pipelineDataTypeLabel } from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";

const props = defineProps<{ type: string }>();
const i18n = useI18nStore();
const label = computed(() =>
  pipelineDataTypeLabel(props.type, (key, fallback) => i18n.t(key, fallback)),
);
const tone = computed(() => dataTypeTone(props.type));
</script>

<template>
  <span class="type-chip" :data-type="type" :data-tone="tone">
    <span class="type-glyph" aria-hidden="true">{{ dataTypeGlyph(type) }}</span>
    {{ label }}
  </span>
</template>

<style scoped>
.type-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 24px;
  padding: 1px 8px 1px 6px;
  border: 1px solid var(--border-subtle);
  border-inline-start: 4px solid var(--text-tertiary);
  border-radius: var(--radius-xs);
  background: var(--surface-inset);
  color: var(--text-primary);
  font-size: 0.75rem;
  font-weight: 700;
  white-space: nowrap;
}
.type-glyph {
  color: var(--text-secondary);
}
.type-chip[data-tone="1"] {
  border-inline-start-color: var(--viz-cat-1);
}
.type-chip[data-tone="2"] {
  border-inline-start-color: var(--viz-cat-2);
}
.type-chip[data-tone="3"] {
  border-inline-start-color: var(--viz-cat-3);
}
.type-chip[data-tone="4"] {
  border-inline-start-color: var(--viz-cat-4);
}
.type-chip[data-tone="5"] {
  border-inline-start-color: var(--viz-cat-5);
}
.type-chip[data-tone="6"] {
  border-inline-start-color: var(--viz-cat-6);
}
</style>
