<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { LlmActivity } from "../api/pdfCorpus";

// What the build is waiting for, in words. The progress bar only moves when a stage finishes, and the first
// model call of a build can take minutes (a large model has to be loaded into memory first), so a bar that sits
// still looks like a hang. This says which it is, and counts the seconds.
const props = defineProps<{ activity: LlmActivity | null | undefined }>();
const i18n = useI18nStore();

// The server reports elapsed seconds at the moment it answered; tick locally between polls.
const receivedAt = ref(Date.now());
const tick = ref(Date.now());
watch(
  () => props.activity,
  () => {
    receivedAt.value = Date.now();
    tick.value = Date.now();
  },
);
const timer = window.setInterval(() => {
  tick.value = Date.now();
}, 1000);
onBeforeUnmount(() => window.clearInterval(timer));

const elapsed = computed(() => {
  if (!props.activity) return "";
  const total = Math.max(
    0,
    Math.round(props.activity.seconds + (tick.value - receivedAt.value) / 1000),
  );
  return total >= 60
    ? `${Math.floor(total / 60)} min ${String(total % 60).padStart(2, "0")} s`
    : `${total} s`;
});
const task = computed(() => {
  const kind = props.activity?.task ?? "other";
  const fallback = {
    manifest: "the document structure",
    segmentation: "the record boundaries",
    metadata: "record metadata",
    other: "this step",
  }[kind];
  return i18n.t(`pdf_corpus.model_task.${kind}`, fallback);
});
const message = computed(() => {
  const a = props.activity;
  if (!a) return "";
  const values = { model: a.model, task: task.value, elapsed: elapsed.value };
  if (a.state === "loading_model") return i18n.tf("pdf_corpus.model_loading", values);
  if (a.state === "working") return i18n.tf("pdf_corpus.model_working", values);
  return i18n.tf("pdf_corpus.model_waiting", values);
});
</script>

<template>
  <p v-if="activity" class="model-activity" :data-state="activity.state" role="status">
    <span class="model-activity-dot" aria-hidden="true"></span>{{ message }}
  </p>
</template>

<style scoped>
.model-activity {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--tone-info-border);
  border-radius: var(--radius-control);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
  font-size: var(--fs-base);
  line-height: var(--lh-normal);
}
.model-activity[data-state="loading_model"] {
  border-color: var(--tone-warn-border);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.model-activity-dot {
  flex: none;
  inline-size: 0.5rem;
  block-size: 0.5rem;
  border-radius: 50%;
  background: currentColor;
  animation: model-activity-pulse 1.4s ease-in-out infinite;
}
@keyframes model-activity-pulse {
  50% {
    opacity: 0.25;
  }
}
@media (prefers-reduced-motion: reduce) {
  .model-activity-dot {
    animation: none;
  }
}
</style>
