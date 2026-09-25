<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";

const props = defineProps<{
  stage?: string;
  status?: string;
  published?: boolean;
  hasAsset?: boolean;
  hasManifest?: boolean;
  acceptedCount?: number;
  recordCount?: number;
  blockerCount?: number;
  canPublish?: boolean;
}>();
const i18n = useI18nStore();

const currentStep = computed(() => {
  const stage = String(props.stage || "");
  const status = String(props.status || "");
  if (props.published || status === "published") return 4;
  if (["ready"].includes(stage) || status === "ready" || Boolean(props.canPublish)) return 4;
  if (["enriching", "review", "metadata_retry"].includes(stage) || status === "awaiting_review")
    return 3;
  if (
    [
      "analyzing",
      "extracting",
      "manifest",
      "segmenting",
      "constructing_records",
      "reconciling",
    ].includes(stage) ||
    ["queued", "running", "awaiting_manifest_review"].includes(status)
  )
    return 2;
  return 1;
});

const steps = computed(() => {
  const items = [
    [1, "pdf_corpus.workflow.source_configure", "Source & configure"],
    [2, "pdf_corpus.workflow.build_phase", "Build"],
    [3, "pdf_corpus.workflow.review_short", "Review"],
    [4, "pdf_corpus.workflow.publish", "Publish"],
  ] as const;
  return items.map(([number, key, fallback]) => ({
    number,
    label: i18n.t(key, fallback),
    state:
      number < currentStep.value
        ? "complete"
        : number === currentStep.value
          ? "current"
          : "upcoming",
  }));
});
</script>

<template>
  <nav class="workflow" :aria-label="i18n.t('pdf_corpus.workflow.label')">
    <ol>
      <li
        v-for="step in steps"
        :key="step.number"
        :data-state="step.state"
        :aria-current="step.state === 'current' ? 'step' : undefined"
      >
        <span class="marker" aria-hidden="true">
          {{ step.state === "complete" ? "✓" : step.number }}
        </span>
        <span class="step-copy">
          <b>{{ step.label }}</b>
          <small>{{
            step.state === "complete"
              ? i18n.t("pdf_corpus.workflow.complete")
              : step.state === "current"
                ? i18n.t("pdf_corpus.workflow.current")
                : i18n.t("pdf_corpus.workflow.upcoming")
          }}</small>
        </span>
      </li>
    </ol>
  </nav>
</template>

<style scoped>
.workflow {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  padding: var(--space-3);
}

.workflow ol {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-2);
}

.workflow li {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  border-radius: var(--radius-control);
  color: var(--text-secondary);
}

.workflow li[data-state="current"] {
  background: var(--surface-inset);
  color: var(--text-primary);
}

.workflow li[data-state="complete"] {
  color: var(--text-primary);
}

.marker {
  display: grid;
  place-items: center;
  inline-size: 26px;
  block-size: 26px;
  flex: 0 0 26px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-pill);
  font-size: var(--fs-sm);
  font-weight: var(--fw-bold);
}

.workflow li[data-state="current"] .marker {
  border-color: var(--border-interactive);
  outline: 2px solid color-mix(in srgb, var(--accent-fg) 20%, transparent);
}

.step-copy {
  display: grid;
  gap: var(--space-1);
  min-width: 0;
}

.step-copy b,
.step-copy small {
  overflow-wrap: anywhere;
}

.step-copy b {
  font-size: var(--fs-sm);
}

.step-copy small {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
}

@media (max-width: 760px) {
  .workflow ol {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 480px) {
  .workflow ol {
    grid-template-columns: 1fr;
  }
}

@media (forced-colors: active) {
  .workflow li[data-state="current"] .marker {
    border-color: Highlight;
    outline-color: Highlight;
  }
}
</style>
