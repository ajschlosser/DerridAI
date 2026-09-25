<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { ReviewQueue } from "../types/corpus";

const props = withDefaults(
  defineProps<{
    modelValue: ReviewQueue;
    total: number;
    ready: number;
    issues: number;
    metadata: number;
    topology: number;
    sourceProblems?: number;
    accepted: number;
    rejected: number;
    disabled?: boolean;
  }>(),
  { sourceProblems: 0, disabled: false },
);
const emit = defineEmits<{ "update:modelValue": [value: ReviewQueue] }>();
const i18n = useI18nStore();
const issueQueues = new Set<ReviewQueue>(["metadata", "topology", "source"]);
const primaryModel = computed<ReviewQueue>(() =>
  issueQueues.has(props.modelValue) ? "issues" : props.modelValue,
);
const primaryTabs: Array<{ id: ReviewQueue; key: string; fallback: string }> = [
  { id: "all", key: "pdf_corpus.queue_all", fallback: "All" },
  { id: "ready", key: "pdf_corpus.queue_ready", fallback: "Reviewable" },
  { id: "issues", key: "pdf_corpus.queue_issues", fallback: "Issues" },
  { id: "accepted", key: "pdf_corpus.queue_accepted", fallback: "Accepted" },
  { id: "rejected", key: "pdf_corpus.queue_rejected", fallback: "Rejected" },
];
function tabCount(id: ReviewQueue): number {
  switch (id) {
    case "all":
      return props.total;
    case "ready":
      return props.ready;
    case "issues":
      return props.issues;
    case "metadata":
      return props.metadata;
    case "topology":
      return props.topology;
    case "source":
      return props.sourceProblems;
    case "accepted":
      return props.accepted;
    case "rejected":
      return props.rejected;
  }
}
const issueFilter = computed(() =>
  issueQueues.has(props.modelValue) ? props.modelValue : "issues",
);
function selectPrimary(value: ReviewQueue) {
  emit("update:modelValue", value);
}
function selectIssue(event: Event) {
  emit("update:modelValue", (event.target as HTMLSelectElement).value as ReviewQueue);
}
function onKeydown(event: KeyboardEvent, current: ReviewQueue) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  const ids = primaryTabs.map((tab) => tab.id);
  const currentIndex = Math.max(0, ids.indexOf(current));
  let next = currentIndex;
  if (event.key === "Home") next = 0;
  else if (event.key === "End") next = ids.length - 1;
  else if (event.key === "ArrowRight") next = (currentIndex + 1) % ids.length;
  else next = (currentIndex - 1 + ids.length) % ids.length;
  event.preventDefault();
  const value = ids[next];
  selectPrimary(value);
  queueMicrotask(() =>
    document.querySelector<HTMLButtonElement>(`[data-review-queue="${value}"]`)?.focus(),
  );
}
</script>

<template>
  <div class="queue-controls">
    <div class="queue-tabs" role="toolbar" :aria-label="i18n.t('pdf_corpus.review_queue')">
      <button
        v-for="tab in primaryTabs"
        :key="tab.id"
        type="button"
        class="queue-tab"
        :data-review-queue="tab.id"
        :aria-pressed="modelValue === tab.id || primaryModel === tab.id"
        :tabindex="primaryModel === tab.id ? 0 : -1"
        :disabled="disabled"
        @keydown="onKeydown($event, tab.id)"
        @click="selectPrimary(tab.id)"
      >
        <span>{{ i18n.t(tab.key, tab.fallback) }}</span
        ><strong>{{ tabCount(tab.id) }}</strong>
      </button>
    </div>
    <label v-if="primaryModel === 'issues'" class="issue-filter">
      <span>{{ i18n.t("pdf_corpus.issue_filter") }}</span>
      <select class="control" :disabled="disabled" :value="issueFilter" @change="selectIssue">
        <option value="issues">{{ i18n.t("pdf_corpus.issue_filter_all") }} · {{ issues }}</option>
        <option v-if="metadata > 0 || modelValue === 'metadata'" value="metadata">
          {{ i18n.t("pdf_corpus.queue_metadata") }} · {{ metadata }}
        </option>
        <option v-if="topology > 0 || modelValue === 'topology'" value="topology">
          {{ i18n.t("pdf_corpus.queue_topology") }} · {{ topology }}
        </option>
        <option v-if="sourceProblems > 0 || modelValue === 'source'" value="source">
          {{ i18n.t("pdf_corpus.queue_source") }} · {{ sourceProblems }}
        </option>
      </select>
    </label>
    <p class="queue-count-help" role="note">
      {{ i18n.t("pdf_corpus.queue_count_help") }}
    </p>
  </div>
</template>

<style scoped>
.queue-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.queue-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.queue-tab {
  min-height: 40px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: var(--muted);
  padding: 7px 11px;
  display: flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 700;
}
.queue-tab strong {
  min-width: 22px;
  padding: 2px 6px;
  border-radius: 999px;
  background: var(--soft);
  color: var(--text);
  font-size: 0.8125rem;
  text-align: center;
}
.queue-tab[aria-pressed="true"] {
  background: var(--card);
  border-color: var(--line);
  color: var(--text);
  box-shadow: 0 1px 2px rgb(0 0 0/0.04);
}
.queue-tab:focus-visible,
.issue-filter select:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.queue-tab:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.issue-filter {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--muted);
}
.issue-filter .control {
  min-height: 40px;
  font-size: 0.8125rem;
  min-width: 150px;
}
.queue-count-help {
  flex-basis: 100%;
  margin: 0;
  color: var(--muted);
  font-size: 0.75rem;
}
@media (max-width: 700px) {
  .queue-controls,
  .issue-filter {
    align-items: stretch;
  }
  .issue-filter {
    width: 100%;
    display: grid;
  }
  .issue-filter .control {
    width: 100%;
  }
}
</style>
