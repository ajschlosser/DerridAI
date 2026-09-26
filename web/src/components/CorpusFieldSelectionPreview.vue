<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";

/** What the reviewer has selected in the record, shown before it is cited as evidence for a field. */
const props = defineProps<{ selection: string }>();
const emit = defineEmits<{ clear: [] }>();
const i18n = useI18nStore();
const preview = computed(() =>
  props.selection.length > 160 ? `${props.selection.slice(0, 160).trimEnd()}…` : props.selection,
);
</script>

<template>
  <div class="selection-preview" :data-state="selection ? 'set' : 'empty'">
    <template v-if="selection">
      <span class="selection-label">{{ i18n.t("pdf_corpus.evidence_selection_label") }}</span>
      <q>{{ preview }}</q>
      <button type="button" class="link-button" @click="emit('clear')">
        {{ i18n.t("pdf_corpus.evidence_selection_clear") }}
      </button>
    </template>
    <span v-else class="selection-hint">{{ i18n.t("pdf_corpus.evidence_selection_hint") }}</span>
  </div>
</template>

<style scoped>
.selection-preview {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 8px;
  padding: 6px 10px;
  border: 1px dashed var(--border-strong, var(--line));
  border-radius: var(--radius-control);
  font-size: var(--fs-sm);
}
.selection-preview[data-state="set"] {
  border-style: solid;
  border-color: var(--tone-info-edge);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
}
.selection-label {
  font-weight: 700;
}
.selection-preview q {
  min-width: 0;
  font-family: var(--font-reading, Georgia, serif);
  overflow-wrap: anywhere;
}
.selection-hint {
  color: var(--text-secondary, var(--muted));
}
.link-button {
  border: 0;
  background: none;
  color: var(--accent-fg);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
.link-button:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: 2px;
}
</style>
