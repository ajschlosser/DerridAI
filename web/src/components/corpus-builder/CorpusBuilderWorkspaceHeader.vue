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
  }>(),
  {
    sourceFilename: "",
    buildId: "",
    publicationId: "",
    stage: "",
    status: "",
    recordCount: 0,
    acceptedCount: 0,
  },
);

const i18n = useI18nStore();
const contextual = computed(() => Boolean(props.sourceFilename || props.buildId));
const lifecycleLabel = computed(() => {
  const raw = props.publicationId ? "published" : props.stage || props.status;
  return raw ? raw.replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase()) : "";
});
const progressLabel = computed(() => {
  if (!props.recordCount) return "";
  return i18n.tf(
    "pdf_corpus.workspace.record_progress",
    { accepted: props.acceptedCount, total: props.recordCount },
    `${props.acceptedCount.toLocaleString()} of ${props.recordCount.toLocaleString()} Records accepted`,
  );
});
</script>

<template>
  <header class="corpus-workspace-header" :class="{ contextual }">
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
    </div>
    <div class="corpus-workspace-actions">
      <slot name="actions"></slot>
    </div>
  </header>
</template>

<style scoped>
.corpus-workspace-header {
  position: sticky;
  top: 0;
  z-index: 14;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-4);
  align-items: end;
  padding: var(--space-3) 0;
  background: color-mix(in srgb, var(--surface-canvas) 94%, transparent);
  backdrop-filter: blur(16px);
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
