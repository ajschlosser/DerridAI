<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";

export type CorpusConfigurationSection =
  | "source"
  | "structure"
  | "enrichment"
  | "metadata"
  | "advanced";

const props = withDefaults(
  defineProps<{
    modelValue: CorpusConfigurationSection;
    hasSource?: boolean;
    structureAvailable?: boolean;
  }>(),
  {
    hasSource: false,
    structureAvailable: false,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: CorpusConfigurationSection];
}>();

const i18n = useI18nStore();
const tabs: Array<{
  id: CorpusConfigurationSection;
  labelKey: string;
  fallback: string;
}> = [
  { id: "source", labelKey: "pdf_corpus.configure_source", fallback: "Source" },
  { id: "structure", labelKey: "pdf_corpus.configure_structure", fallback: "Structure" },
  { id: "enrichment", labelKey: "pdf_corpus.configure_enrichment", fallback: "Enrichment" },
  { id: "metadata", labelKey: "pdf_corpus.configure_metadata", fallback: "Metadata" },
  { id: "advanced", labelKey: "pdf_corpus.configure_advanced", fallback: "Advanced" },
];

function disabled(id: CorpusConfigurationSection) {
  if (id === "structure") return !props.hasSource || !props.structureAvailable;
  if (id === "enrichment" || id === "metadata" || id === "advanced") return !props.hasSource;
  return false;
}

function select(id: CorpusConfigurationSection) {
  if (!disabled(id)) emit("update:modelValue", id);
}
</script>

<template>
  <nav class="corpus-config-nav" :aria-label="i18n.t('pdf_corpus.configure_sections', 'Build configuration')">
    <div class="corpus-config-tabs" role="tablist">
      <button
        v-for="tab in tabs"
        :id="`corpus-config-tab-${tab.id}`"
        :key="tab.id"
        type="button"
        role="tab"
        :aria-selected="modelValue === tab.id"
        :aria-controls="`corpus-config-panel-${tab.id}`"
        :tabindex="modelValue === tab.id ? 0 : -1"
        :disabled="disabled(tab.id)"
        @click="select(tab.id)"
      >
        <span>{{ i18n.t(tab.labelKey, tab.fallback) }}</span>
        <span
          v-if="tab.id === 'source' && hasSource"
          class="corpus-config-tab-status"
          aria-hidden="true"
        >✓</span>
      </button>
    </div>
  </nav>
</template>

<style scoped>
.corpus-config-nav {
  position: sticky;
  top: var(--app-header-height, 0px);
  z-index: 8;
  padding-block: var(--space-2);
  background: color-mix(in srgb, var(--surface-canvas) 94%, transparent);
  backdrop-filter: blur(14px);
}
.corpus-config-tabs {
  display: flex;
  gap: var(--space-1);
  overflow-x: auto;
  padding: var(--space-1);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
  scrollbar-width: thin;
}
.corpus-config-tabs button {
  min-height: 2.5rem;
  display: inline-flex;
  flex: 1 0 auto;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding-inline: var(--space-4);
  border: 0;
  border-radius: calc(var(--radius-control) - 2px);
  background: transparent;
  color: var(--text-secondary);
  font: inherit;
  font-weight: var(--fw-semibold);
  cursor: pointer;
}
.corpus-config-tabs button:hover:not(:disabled) {
  background: var(--surface-card);
  color: var(--text-primary);
}
.corpus-config-tabs button[aria-selected="true"] {
  background: var(--surface-card);
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);
}
.corpus-config-tabs button:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 1px;
}
.corpus-config-tabs button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.corpus-config-tab-status {
  display: inline-grid;
  width: 1.15rem;
  height: 1.15rem;
  place-items: center;
  border-radius: 999px;
  background: var(--tone-success-bg);
  color: var(--tone-success-fg);
  font-size: 0.72rem;
}
@media (max-width: 720px) {
  .corpus-config-tabs button {
    flex: 0 0 auto;
    padding-inline: var(--space-3);
  }
}
</style>
