<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed } from "vue";
import { useI18nStore } from "../../stores/i18n";

const props = defineProps<{
  id: string;
  title: string;
  description?: string;
  state: "incomplete" | "complete" | "warning" | "optional";
  summary?: string;
  expanded: boolean;
  disabled?: boolean;
}>();
defineEmits<{ toggle: [] }>();

const i18n = useI18nStore();
const panelId = computed(() => `corpus-setup-panel-${props.id}`);
const headingId = computed(() => `corpus-setup-heading-${props.id}`);
const stateLabel = computed(() => i18n.t(`pdf_corpus.setup.state.${props.state}`));
const indicator = computed(
  () => ({ complete: "✓", warning: "!", incomplete: "", optional: "" })[props.state],
);
</script>

<template>
  <section
    class="corpus-setup-section"
    :data-state="state"
    :data-expanded="expanded ? 'true' : 'false'"
    :data-section="id"
  >
    <h3 :id="headingId" class="corpus-setup-section-head">
      <button
        type="button"
        class="corpus-setup-section-toggle"
        :aria-expanded="expanded"
        :aria-controls="panelId"
        :disabled="disabled"
        @click="$emit('toggle')"
      >
        <span class="corpus-setup-indicator" aria-hidden="true">{{ indicator }}</span>
        <span class="sr-only">{{ stateLabel }}:</span>
        <span class="corpus-setup-title">{{ title }}</span>
        <span v-if="summary" class="corpus-setup-summary">{{ summary }}</span>
        <span class="corpus-setup-affordance">{{
          expanded ? i18n.t("pdf_corpus.setup.collapse") : i18n.t("pdf_corpus.setup.edit")
        }}</span>
      </button>
    </h3>
    <div
      v-show="expanded"
      :id="panelId"
      class="corpus-setup-section-body"
      role="region"
      :aria-labelledby="headingId"
    >
      <p v-if="description" class="corpus-setup-description">{{ description }}</p>
      <slot></slot>
    </div>
  </section>
</template>

<style scoped>
.corpus-setup-section {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.corpus-setup-section[data-expanded="true"] {
  border-color: var(--border-interactive);
  box-shadow: var(--shadow-sm);
}
.corpus-setup-section-head {
  margin: 0;
  font-size: inherit;
}
.corpus-setup-section-toggle {
  width: 100%;
  display: grid;
  grid-template-columns: auto max-content minmax(0, 1fr) auto;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-3) var(--space-4);
  border: 0;
  border-radius: var(--radius-card);
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  text-align: start;
  cursor: pointer;
}
.corpus-setup-section-toggle:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: -3px;
}
.corpus-setup-section-toggle:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.corpus-setup-indicator {
  width: 1.4rem;
  height: 1.4rem;
  display: grid;
  place-items: center;
  border: 2px solid var(--border-interactive);
  border-radius: 999px;
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
}
.corpus-setup-section[data-state="complete"] .corpus-setup-indicator {
  border-color: var(--tone-ok-border);
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
}
.corpus-setup-section[data-state="warning"] .corpus-setup-indicator {
  border-color: var(--tone-warn-border);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.corpus-setup-section[data-state="optional"] .corpus-setup-indicator {
  border-style: dashed;
}
.corpus-setup-title {
  font-size: var(--fs-md, 1rem);
  font-weight: var(--fw-bold);
}
.corpus-setup-summary {
  min-width: 0;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.corpus-setup-affordance {
  color: var(--accent-fg);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.corpus-setup-section-body {
  display: grid;
  gap: var(--space-4);
  padding: 0 var(--space-4) var(--space-4);
}
.corpus-setup-description {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
@media (max-width: 720px) {
  .corpus-setup-section-toggle {
    grid-template-columns: auto minmax(0, 1fr) auto;
  }
  .corpus-setup-summary {
    grid-column: 2 / -1;
    white-space: normal;
  }
}
</style>
