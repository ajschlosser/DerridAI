<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

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
const progressValue = computed(() =>
  props.recordCount ? Math.min(props.recordCount, Math.max(0, props.acceptedCount)) : 0,
);
const progressLabel = computed(() => {
  if (!props.recordCount) return "";
  return i18n.tf("pdf_corpus.workspace.record_progress", "{accepted} of {total} Records accepted", {
    accepted: props.acceptedCount.toLocaleString(),
    total: props.recordCount.toLocaleString(),
  });
});
type WorkspacePhaseId = "setup" | "build_review" | "publish";
interface WorkspacePhase {
  id: WorkspacePhaseId;
  available: boolean;
  state: CorpusWorkflowStep["state"];
  target: CorpusWorkspace;
}

function internalStep(id: CorpusWorkspace) {
  return props.steps.find((step) => step.id === id);
}

const phases = computed<WorkspacePhase[]>(() => {
  const setup = internalStep("setup");
  const build = internalStep("build");
  const review = internalStep("review");
  const publish = internalStep("publish");
  const buildReviewCurrent = props.workspace === "build" || props.workspace === "review";
  const buildReviewAvailable = Boolean(build?.available || review?.available);
  const buildReviewComplete = build?.state === "complete" && review?.state === "complete";
  const buildReviewState: CorpusWorkflowStep["state"] = buildReviewCurrent
    ? "current"
    : buildReviewComplete
      ? "complete"
      : buildReviewAvailable
        ? "available"
        : "unavailable";

  return [
    {
      id: "setup",
      available: setup?.available ?? true,
      state: props.workspace === "setup" ? "current" : setup?.state || "available",
      target: "setup",
    },
    {
      id: "build_review",
      available: buildReviewAvailable,
      state: buildReviewState,
      // Keep the current internal workspace when the grouped phase is already active.
      // From Setup/Publish, prefer Review once Records exist; otherwise land on Build.
      target: buildReviewCurrent ? props.workspace : review?.available ? "review" : "build",
    },
    {
      id: "publish",
      available: publish?.available ?? false,
      state: props.workspace === "publish" ? "current" : publish?.state || "unavailable",
      target: "publish",
    },
  ];
});
const buildAvailable = computed(() => Boolean(internalStep("build")?.available));
const reviewAvailable = computed(() => Boolean(internalStep("review")?.available));
const buildReviewActive = computed(
  () => props.workspace === "build" || props.workspace === "review",
);

function phaseLabel(phase: WorkspacePhase) {
  return i18n.t(`pdf_corpus.workspace.${phase.id}`);
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
        <span class="corpus-workspace-source">
          <strong v-if="sourceFilename">{{ sourceFilename }}</strong>
          <span v-if="status" class="corpus-workspace-stage" :data-tone="status.tone">
            {{ status.label }}
          </span>
        </span>
        <span
          v-if="progressLabel"
          class="corpus-workspace-progress"
          role="group"
          :aria-label="i18n.t('pdf_corpus.review_progress')"
        >
          <span>{{ progressLabel }}</span>
          <progress
            :max="Math.max(recordCount, 1)"
            :value="progressValue"
            :aria-label="progressLabel"
          ></progress>
        </span>
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
        <ol class="workspace-phase-list">
          <li v-for="(phase, index) in phases" :key="phase.id">
            <button
              type="button"
              :disabled="!phase.available"
              :data-state="phase.state"
              :data-phase="phase.id"
              :aria-current="phase.state === 'current' ? 'step' : undefined"
              @click="emit('workspace', phase.target)"
            >
              <span class="step-mark" aria-hidden="true">{{
                phase.state === "complete" ? "✓" : index + 1
              }}</span>
              {{ phaseLabel(phase) }}
              <span v-if="phase.state === 'complete'" class="sr-only">
                {{ i18n.t("pdf_corpus.workspace.step_complete") }}
              </span>
            </button>
          </li>
        </ol>
        <div
          v-if="buildReviewActive"
          class="workspace-subnav"
          role="group"
          :aria-label="i18n.t('pdf_corpus.workspace.build_review')"
        >
          <button
            type="button"
            :aria-pressed="workspace === 'build'"
            :disabled="!buildAvailable"
            @click="emit('workspace', 'build')"
          >
            {{ i18n.t("pdf_corpus.workspace.build") }}
          </button>
          <button
            type="button"
            :aria-pressed="workspace === 'review'"
            :disabled="!reviewAvailable"
            @click="emit('workspace', 'review')"
          >
            {{ i18n.t("pdf_corpus.workspace.review") }}
          </button>
        </div>
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
/* With a build open the page title is already on the tab and breadcrumb, so the header becomes one
   compact row: the source and status, then the phase stepper, instead of a repeated heading. */
.contextual .corpus-workspace-identity {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-5);
  align-items: center;
}
.contextual .eyebrow,
.contextual .corpus-workspace-title-row {
  position: absolute;
  inline-size: 1px;
  block-size: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}
.contextual .workspace-mode-nav .workspace-phase-list {
  margin: 0;
}
.contextual .corpus-workspace-context strong {
  font-size: var(--fs-md, 1rem);
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
.corpus-workspace-source {
  display: inline-flex;
  min-width: 0;
  gap: var(--space-2);
  align-items: center;
}
.corpus-workspace-context strong {
  max-width: min(34rem, 48vw);
  overflow: hidden;
  color: var(--text-primary);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.corpus-workspace-progress {
  display: grid;
  min-width: 10rem;
  gap: 3px;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.corpus-workspace-progress progress {
  inline-size: 100%;
  block-size: 5px;
  overflow: hidden;
  appearance: none;
  border: 0;
  border-radius: 999px;
  background: var(--border-subtle);
}
.corpus-workspace-progress progress::-webkit-progress-bar {
  background: var(--border-subtle);
}
.corpus-workspace-progress progress::-webkit-progress-value {
  background: var(--ui-accent);
}
.corpus-workspace-progress progress::-moz-progress-bar {
  background: var(--ui-accent);
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
.workspace-mode-nav .workspace-phase-list {
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
.workspace-subnav {
  display: inline-flex;
  gap: 2px;
  margin-inline-start: var(--space-2);
  padding: 2px;
  border-inline-start: 1px solid var(--border-subtle);
  vertical-align: middle;
}
.workspace-subnav button {
  min-height: 30px;
  padding-inline: var(--space-2);
  font-size: var(--fs-xs);
}
.workspace-subnav button[aria-pressed="true"] {
  background: var(--surface-raised);
  color: var(--text-primary);
}
.step-mark {
  display: inline-grid;
  inline-size: 1.25rem;
  block-size: 1.25rem;
  place-items: center;
  flex: 0 0 auto;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  line-height: 1;
}
.workspace-mode-nav button[data-state="current"] .step-mark {
  border-color: var(--ui-accent);
  background: var(--surface-selected);
  color: var(--text-primary);
}
.workspace-mode-nav button[data-state="complete"] .step-mark {
  border-color: var(--tone-ok-border);
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
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
  .workspace-subnav {
    display: flex;
    width: fit-content;
    margin: var(--space-1) 0 0;
    border-inline-start: 0;
  }
}
</style>
