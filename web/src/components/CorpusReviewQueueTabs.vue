<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
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
const primary: Array<{ id: ReviewQueue; key: string; fallback: string }> = [
  { id: "all", key: "pdf_corpus.queue_all", fallback: "All" },
  { id: "ready", key: "pdf_corpus.queue_tab.ready", fallback: "Ready" },
  { id: "issues", key: "pdf_corpus.queue_tab.issues", fallback: "Needs attention" },
  { id: "accepted", key: "pdf_corpus.queue_accepted", fallback: "Accepted" },
  { id: "rejected", key: "pdf_corpus.queue_rejected", fallback: "Rejected" },
];
function count(id: ReviewQueue): number {
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
/** One list: the five filters, with the kinds of issue indented under Needs attention when they have records. */
const options = computed(() => {
  const rows: Array<{ id: ReviewQueue; label: string; sub: boolean }> = [];
  const sub: Array<{ id: ReviewQueue; key: string }> = [
    { id: "metadata", key: "pdf_corpus.queue_metadata" },
    { id: "topology", key: "pdf_corpus.queue_topology" },
    { id: "source", key: "pdf_corpus.queue_source" },
  ];
  for (const item of primary) {
    rows.push({
      id: item.id,
      label: `${i18n.t(item.key, item.fallback)} · ${count(item.id)}`,
      sub: false,
    });
    if (item.id !== "issues") continue;
    for (const kind of sub) {
      if (count(kind.id) > 0 || props.modelValue === kind.id)
        rows.push({
          id: kind.id,
          label: `${i18n.t(kind.key)} · ${count(kind.id)}`,
          sub: true,
        });
    }
  }
  return rows;
});
function select(event: Event) {
  emit("update:modelValue", (event.target as HTMLSelectElement).value as ReviewQueue);
}
</script>

<template>
  <div class="queue-controls">
    <label class="queue-filter">
      <span>{{ i18n.t("pdf_corpus.queue_filter_label") }}</span>
      <select
        class="control"
        data-review-queue-select
        :aria-label="i18n.t('pdf_corpus.review_queue')"
        aria-describedby="review-queue-count-help"
        :disabled="disabled"
        :value="modelValue"
        @change="select"
      >
        <option v-for="item in options" :key="item.id" :value="item.id">
          {{ item.sub ? "\u00a0\u00a0↳ " : "" }}{{ item.label }}
        </option>
      </select>
    </label>
    <p id="review-queue-count-help" class="sr-only">
      {{ i18n.t("pdf_corpus.queue_count_help") }}
    </p>
  </div>
</template>

<style scoped>
.queue-controls {
  display: flex;
  align-items: center;
}
.queue-filter {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 700;
}
/* The select names itself for assistive technology; the word "Show" is only worth its width when there is room. */
.queue-filter > span {
  display: none;
}
@container (min-width: 60rem) {
  .queue-filter > span {
    display: inline;
  }
}
.queue-filter .control {
  min-height: 40px;
  min-width: 9.5rem;
  font-size: 0.8125rem;
}
.queue-filter select:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 2px;
}
</style>
