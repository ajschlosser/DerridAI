<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed } from "vue";
import { useI18nStore } from "../../stores/i18n";
import type {
  CorpusPrimaryStatus,
  CorpusWorkflowStep,
} from "../../features/corpus-builder/domain/workflowPresentation";
import type { CorpusWorkspace } from "../../features/corpus-builder/domain/workspace";

const props = withDefaults(
  defineProps<{
    sourceFilename?: string;
    buildId?: string;
    publicationId?: string;
    status?: CorpusPrimaryStatus | null;
    recordCount?: number;
    acceptedCount?: number;
    workspace?: CorpusWorkspace;
    steps?: CorpusWorkflowStep[];
    sticky?: boolean;
  }>(),
  {
    sourceFilename: "",
    buildId: "",
    publicationId: "",
    status: null,
    recordCount: 0,
    acceptedCount: 0,
    workspace: "setup",
    steps: () => [],
    sticky: true,
  },
);

const emit = defineEmits<{ workspace: [value: CorpusWorkspace] }>();
const i18n = useI18nStore();
const contextual = computed(() => Boolean(props.sourceFilename || props.buildId));
const progressLabel = computed(() => {
  if (!props.recordCount) return "";
  return i18n.tf("pdf_corpus.workspace.record_progress", "{accepted} of {total} Records accepted", {
    accepted: props.acceptedCount.toLocaleString(),
    total: props.recordCount.toLocaleString(),
  });
});
function stepLabel(step: CorpusWorkflowStep) {
  return i18n.t(`pdf_corpus.workspace.${step.id}`);
}
</script>

<template>
  <header class="corpus-workspace-header" :class="{ contextual, sticky }">
    <div class="corpus-workspace-identity">
      <span class="eyebrow">{{ i18n.t("pdf_corpus.eyebrow") }}</span>
      <div class="corpus-workspace-title-row">
        <h1 id="pdf-corpus-builder-title">{{ i18n.t("pdf_corpus.title") }}</h1>
      </div>
      <p v-if="!contextual" class="corpus-workspace-intro">
        {{ i18n.t("pdf_corpus.subtitle") }}
      </p>
      <div v-else class="corpus-workspace-context">
        <strong v-if="sourceFilename">{{ sourceFilename }}</strong>
        <span v-if="status" class="corpus-workspace-stage" :data-tone="status.tone">
          {{ status.label }}
        </span>
        <span v-if="progressLabel">{{ progressLabel }}</span>
        <details v-if="buildId" class="corpus-workspace-build-details">
          <summary>{{ i18n.t("pdf_corpus.workspace.build_details") }}</summary>
          <dl>
            <dt>{{ i18n.t("pdf_corpus.build_id") }}</dt>
            <dd>
              <code>{{ buildId }}</code>
            </dd>
            <template v-if="publicationId">
              <dt>{{ i18n.t("pdf_corpus.publication_id") }}</dt>
              <dd>
                <code>{{ publicationId }}</code>
              </dd>
            </template>
          </dl>
        </details>
      </div>
      <nav class="workspace-mode-nav" :aria-label="i18n.t('pdf_corpus.workspace.navigation')">
        <ol>
          <li v-for="step in steps" :key="step.id">
            <button
              type="button"
              :disabled="!step.available"
              :data-state="step.state"
              :aria-current="step.state === 'current' ? 'step' : undefined"
              @click="emit('workspace', step.id)"
            >
              <span class="step-mark" aria-hidden="true">{{
                step.state === "complete" ? "✓" : ""
              }}</span>
              {{ stepLabel(step) }}
              <span v-if="step.state === 'complete'" class="sr-only">
                {{ i18n.t("pdf_corpus.workspace.step_complete") }}
              </span>
            </button>
          </li>
        </ol>
      </nav>
    </div>
    <div class="corpus-workspace-actions">
      <slot name="actions"></slot>
    </div>
  </header>
</template>

<style scoped>
.corpus-workspace-header {
  position: relative;
  z-index: 14;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-4);
  align-items: end;
  padding: var(--space-3) 0;
  background: color-mix(in srgb, var(--surface-canvas) 94%, transparent);
  backdrop-filter: blur(16px);
}
.corpus-workspace-header.sticky {
  position: sticky;
  top: var(--ref-topbar, 60px);
}
.corpus-workspace-header.contextual {
  align-items: center;
  border-bottom: 1px solid var(--border-subtle);
}
.corpus-workspace-identity {
  min-width: 0;
}
.eyebrow {
  display: block;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.corpus-workspace-title-row h1 {
  margin: 0.15rem 0;
  font-size: clamp(1.35rem, 2vw, 1.7rem);
}
.corpus-workspace-intro {
  max-width: 78ch;
  margin: var(--space-1) 0 0;
  color: var(--text-secondary);
  line-height: 1.5;
}
.corpus-workspace-context {
  display: flex;
  gap: var(--space-2) var(--space-4);
  align-items: center;
  min-width: 0;
  flex-wrap: wrap;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.corpus-workspace-context strong {
  max-width: min(38rem, 60vw);
  overflow: hidden;
  color: var(--text-primary);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.corpus-workspace-stage {
  flex: 0 0 auto;
  padding: 0.2rem 0.55rem;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--surface-subtle);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.corpus-workspace-stage[data-tone="info"] {
  border-color: var(--tone-info-border);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
}
.corpus-workspace-stage[data-tone="success"] {
  border-color: var(--tone-ok-border);
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
}
.corpus-workspace-stage[data-tone="warning"] {
  border-color: var(--tone-warn-border);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.corpus-workspace-stage[data-tone="danger"] {
  border-color: var(--tone-danger-border);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.corpus-workspace-build-details summary {
  cursor: pointer;
  font-size: var(--fs-xs);
}
.corpus-workspace-build-details summary:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 2px;
}
.corpus-workspace-build-details dl {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: var(--space-1) var(--space-3);
  margin: var(--space-1) 0 0;
}
.corpus-workspace-build-details dd {
  margin: 0;
}
.corpus-workspace-build-details code {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: var(--fs-xs);
  overflow-wrap: anywhere;
}
.workspace-mode-nav ol {
  display: inline-flex;
  gap: 2px;
  margin: var(--space-2) 0 0;
  padding: 3px;
  list-style: none;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
}
.workspace-mode-nav button {
  min-height: 34px;
  display: inline-flex;
  gap: var(--space-1);
  align-items: center;
  padding: 0.35rem 0.75rem;
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font: inherit;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.workspace-mode-nav button[data-state="current"] {
  background: var(--surface-raised);
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);
}
.workspace-mode-nav button[data-state="complete"] .step-mark {
  color: var(--tone-ok-fg);
}
.step-mark:empty {
  display: none;
}
.workspace-mode-nav button:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 1px;
}
.workspace-mode-nav button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.corpus-workspace-actions {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
}
@media (max-width: 760px) {
  .corpus-workspace-header {
    position: static;
    grid-template-columns: 1fr;
    align-items: start;
  }
  .corpus-workspace-header.sticky {
    position: static;
  }
  .corpus-workspace-actions {
    justify-content: flex-start;
  }
}
</style>
