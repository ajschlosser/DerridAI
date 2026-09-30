<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import type { ResearchPipelineBenchmarkCase } from "../../types/pipelines";

defineProps<{ cases: ResearchPipelineBenchmarkCase[]; selectedKey: string }>();
const emit = defineEmits<{ select: [key: string] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

function caseKey(item: ResearchPipelineBenchmarkCase) {
  return `${item.case_id}@${item.version}`;
}
</script>

<template>
  <nav
    class="case-list"
    :aria-label="t('pipelines.benchmark_saved_cases', 'Saved benchmark cases')"
  >
    <h4>{{ t("pipelines.benchmark_saved_cases", "Saved benchmark cases") }}</h4>
    <p v-if="!cases.length" class="empty">
      {{ t("pipelines.benchmark_no_cases", "No benchmark cases yet. Create one to begin.") }}
    </p>
    <ul v-else>
      <li v-for="item in cases" :key="caseKey(item)">
        <button
          type="button"
          class="case-choice"
          :class="{ selected: caseKey(item) === selectedKey }"
          :aria-current="caseKey(item) === selectedKey ? 'true' : undefined"
          @click="emit('select', caseKey(item))"
        >
          <strong
            >{{ item.case_id }} <small>v{{ item.version }}</small></strong
          >
          <span>{{ item.source_collection }}</span>
        </button>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.case-list {
  align-self: start;
  position: sticky;
  top: var(--pipeline-studio-sticky-top, var(--space-3));
  max-height: var(--pipeline-studio-pane-max-height, min(76dvh, 960px));
  overflow: auto;
  overscroll-behavior: contain;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.case-list h4 {
  margin: 0;
  padding: var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.case-list ul {
  margin: 0;
  padding: 0;
  list-style: none;
}
.case-choice {
  position: relative;
  display: grid;
  gap: 2px;
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 0;
  border-bottom: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.case-choice small,
.case-choice span {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.case-choice strong {
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}
.case-choice:hover,
.case-choice.selected {
  background: var(--surface-selected);
}
.case-choice.selected::before {
  position: absolute;
  inset: 8px auto 8px 0;
  width: 3px;
  border-radius: 999px;
  background: var(--accent);
  content: "";
}
.case-choice:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: -2px;
}
.empty {
  margin: 0;
  padding: var(--space-3);
  color: var(--text-tertiary);
  font-size: 0.875rem;
}

@media (max-width: 960px) {
  .case-list {
    position: static;
    max-height: 360px;
  }
}
</style>
