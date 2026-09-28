<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../../stores/i18n";

const props = withDefaults(
  defineProps<{
    sourceFilename?: string;
    buildId?: string;
    publicationId?: string;
    stage?: string;
    status?: string;
    recordCount?: number;
    acceptedCount?: number;
    workspace?: "setup" | "build" | "review";
    canBuild?: boolean;
    canReview?: boolean;
    sticky?: boolean;
  }>(),
  {
    sourceFilename: "",
    buildId: "",
    publicationId: "",
    stage: "",
    status: "",
    recordCount: 0,
    acceptedCount: 0,
    workspace: "setup",
    canBuild: false,
    canReview: false,
    sticky: true,
  },
);

const emit = defineEmits<{ workspace: [value: "setup" | "build" | "review"] }>();
const i18n = useI18nStore();
const contextual = computed(() => Boolean(props.sourceFilename || props.buildId));
const lifecycleLabel = computed(() => {
  const raw = props.publicationId ? "published" : props.stage || props.status;
  return raw ? raw.replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase()) : "";
});
const progressLabel = computed(() => {
  if (!props.recordCount) return "";
  return i18n.tf("pdf_corpus.workspace.record_progress", "{accepted} of {total} Records accepted", {
    accepted: props.acceptedCount.toLocaleString(),
    total: props.recordCount.toLocaleString(),
  });
});
</script>

<template>
  <header class="corpus-workspace-header" :class="{ contextual, sticky }">
    <div class="corpus-workspace-identity">
      <span class="eyebrow">{{ i18n.t("pdf_corpus.eyebrow") }}</span>
      <div class="corpus-workspace-title-row">
        <h1 id="pdf-corpus-builder-title">{{ i18n.t("pdf_corpus.title") }}</h1>
        <span v-if="contextual && lifecycleLabel" class="corpus-workspace-stage">
          {{ lifecycleLabel }}
        </span>
      </div>
      <p v-if="!contextual" class="corpus-workspace-intro">
        {{ i18n.t("pdf_corpus.subtitle") }}
      </p>
      <div v-else class="corpus-workspace-context">
        <strong v-if="sourceFilename">{{ sourceFilename }}</strong>
        <span v-if="progressLabel">{{ progressLabel }}</span>
        <span v-if="publicationId">
          {{ i18n.t("pdf_corpus.workflow.publish", "Publish") }} · {{ publicationId }}
        </span>
        <span v-else-if="buildId">{{ buildId }}</span>
      </div>
      <nav class="workspace-mode-nav" :aria-label="i18n.t('pdf_corpus.workspace.navigation')">
        <button
          type="button"
          :aria-pressed="workspace === 'setup'"
          :class="{ active: workspace === 'setup' }"
          @click="emit('workspace', 'setup')"
        >
          {{ i18n.t("pdf_corpus.workspace.setup") }}
        </button>
        <button
          type="button"
          :disabled="!canBuild"
          :aria-pressed="workspace === 'build'"
          :class="{ active: workspace === 'build' }"
          @click="emit('workspace', 'build')"
        >
          {{ i18n.t("pdf_corpus.workspace.build") }}
        </button>
        <button
          type="button"
          :disabled="!canReview"
          :aria-pressed="workspace === 'review'"
          :class="{ active: workspace === 'review' }"
          @click="emit('workspace', 'review')"
        >
          {{ i18n.t("pdf_corpus.workspace.review") }}
        </button>
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
.corpus-workspace-title-row {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  min-width: 0;
}
.corpus-workspace-title-row h1 {
  margin: 0.15rem 0;
  font-size: clamp(1.35rem, 2vw, 1.7rem);
}
.corpus-workspace-stage {
  flex: 0 0 auto;
  padding: 0.28rem 0.55rem;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--surface-subtle);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
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
.corpus-workspace-context span:last-child {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: var(--fs-xs);
}
.workspace-mode-nav {
  display: inline-flex;
  gap: 2px;
  margin-top: var(--space-2);
  padding: 3px;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--surface-subtle);
}
.workspace-mode-nav button {
  min-height: 34px;
  padding: 0.35rem 0.75rem;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font: inherit;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.workspace-mode-nav button.active {
  background: var(--surface-raised);
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);
}
.workspace-mode-nav button:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--accent) 35%, transparent);
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
  .corpus-workspace-actions {
    justify-content: flex-start;
  }
}
</style>
