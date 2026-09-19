<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "./AppIcon.vue";
import { useI18nStore } from "../stores/i18n";
import { isActive, absoluteTime, elapsedSeconds, etaSeconds, formatDuration, percentOf, relativeTime, type OperationView } from "../domain/operationsPanel";
import { statusBadgeTone } from "../domain/operationsDock";

const props = defineProps<{ view: OperationView; now: number; fresh?: boolean }>();
const emit = defineEmits<{ details: [id: string]; result: [id: string]; cancel: [id: string]; remove: [id: string] }>();
const i18n = useI18nStore();

const titleId = computed(() => `ops-title-${props.view.id}`);
const active = computed(() => isActive(props.view));
const tone = computed(() => statusBadgeTone(props.view.status));
const percent = computed(() => percentOf(props.view));
const determinate = computed(() => active.value && props.view.total > 0 && props.view.status !== "queued");
const locale = computed(() => i18n.locale || "en-US");
const STATUS_FALLBACK: Record<string, string> = {
  queued: "Queued", running: "Running", cancelling: "Cancelling", completed: "Completed", cancelled: "Cancelled", failed: "Failed", blocked: "Blocked",
};
const statusText = computed(() => i18n.t(`operations.panel.status_${props.view.status}`, STATUS_FALLBACK[props.view.status] ?? props.view.status));
const time = (seconds: number) => formatDuration(seconds, locale.value);

const progressText = computed(() => {
  if (props.view.status === "queued") return i18n.t("operations.panel.waiting", "Waiting to start");
  const parts = [props.view.progressLabel];
  const eta = etaSeconds(props.view, props.now);
  if (eta !== null) parts.push(i18n.tf("operations.panel.eta", "About {time} left", { time: time(eta) }));
  return parts.filter(Boolean).join(" · ");
});
const timingText = computed(() => {
  const v = props.view;
  if (active.value) {
    return v.status === "queued" ? "" : i18n.tf("operations.panel.elapsed", "Running for {time}", { time: time(elapsedSeconds(v, props.now)) });
  }
  const parts: string[] = [];
  if (v.startedAt && v.finishedAt) parts.push(i18n.tf("operations.panel.took", "Took {time}", { time: time(elapsedSeconds(v, props.now)) }));
  return parts.join(" · ");
});
const whenIso = computed(() => (props.view.status === "queued" ? props.view.createdAt : active.value ? props.view.startedAt || props.view.createdAt : props.view.finishedAt || props.view.startedAt));
const whenText = computed(() => {
  const when = relativeTime(whenIso.value, props.now, locale.value);
  if (!when) return "";
  if (props.view.status === "queued") return i18n.tf("operations.panel.queued_at", "Queued {when}", { when });
  return active.value
    ? i18n.tf("operations.panel.started", "Started {when}", { when })
    : i18n.tf("operations.panel.finished", "Finished {when}", { when });
});

const resultLabel = computed(() => {
  const kind = props.view.result?.kind;
  if (kind === "build") return i18n.t("operations.panel.action_open_build", "Open corpus build");
  if (kind === "review") return i18n.t("operations.panel.action_review", "Review results");
  if (kind === "review-partial") return i18n.t("operations.panel.action_review_partial", "Review available results");
  return i18n.t("operations.panel.action_open_result", "Open result");
});
const resultAria = computed(() => {
  const name = props.view.label;
  const kind = props.view.result?.kind;
  if (kind === "build") return i18n.tf("operations.panel.open_build_for", "Open corpus build: {name}", { name });
  if (kind === "review") return i18n.tf("operations.panel.review_for", "Review results of {name}", { name });
  if (kind === "review-partial") return i18n.tf("operations.panel.review_partial_for", "Review available results of {name}", { name });
  return i18n.tf("operations.panel.open_result_for", "Open result of {name}", { name });
});
</script>

<template>
  <li class="ops-row" :class="[`tone-${tone}`, { 'is-active': active, 'is-fresh': fresh }]" :data-op-id="view.id" :aria-labelledby="titleId">
    <span class="ops-rail" aria-hidden="true"></span>
    <span class="ops-type" aria-hidden="true"><AppIcon :name="view.icon" /></span>

    <div class="ops-main">
      <div class="ops-heading">
        <h4 :id="titleId" class="ops-title">{{ view.label }}</h4>
        <span class="ops-status" :class="`tone-${tone}`">
          <svg v-if="view.status === 'completed'" class="ops-status-icon ops-check" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3.2 3.2L13 5" /></svg>
          <span v-else-if="active" class="ops-status-icon ops-spinner" :class="{ 'is-queued': view.status === 'queued' }" aria-hidden="true"></span>
          <svg v-else-if="view.status === 'failed' || view.status === 'blocked'" class="ops-status-icon" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2.5l6 10.5H2z" /><path d="M8 7v3M8 11.6v.1" /></svg>
          <span v-else class="ops-status-icon ops-dot" aria-hidden="true"></span>
          {{ statusText }}
        </span>
      </div>
      <p v-if="view.subtitle" class="ops-subtitle">{{ view.subtitle }}</p>

      <div v-if="determinate || view.status === 'queued'" class="ops-progress-area">
        <div
          class="ops-progress"
          :class="{ 'is-indeterminate': !determinate }"
          role="progressbar"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-valuenow="determinate ? percent : undefined"
          :aria-valuetext="progressText"
          :aria-label="i18n.tf('operations.panel.progress_for', 'Progress of {name}', { name: view.label })"
        ><span class="ops-progress-fill" :style="determinate ? { width: `${percent}%` } : undefined"></span></div>
        <p class="ops-progress-text">{{ progressText }}</p>
      </div>

      <p v-if="view.error" class="ops-error">
        <strong>{{ i18n.t("operations.panel.error_heading", "What went wrong") }}</strong>
        <span>{{ view.error }}</span>
      </p>

      <p class="ops-meta">
        <time v-if="whenText" :datetime="whenIso || undefined" :title="absoluteTime(whenIso, locale)">{{ whenText }}</time>
        <span v-if="timingText">{{ timingText }}</span>
        <span v-if="view.owner">{{ i18n.tf("operations.panel.by", "by {name}", { name: view.owner }) }}</span>
      </p>

      <dl v-if="view.facts.length" class="ops-facts">
        <div v-for="fact in view.facts" :key="fact.name"><dt>{{ fact.name }}</dt><dd>{{ fact.value }}</dd></div>
      </dl>
    </div>

    <div class="ops-actions">
      <button v-if="view.result" type="button" class="ops-btn is-primary" data-primary :aria-label="resultAria" @click="emit('result', view.id)">{{ resultLabel }}</button>
      <button type="button" class="ops-btn" :class="{ 'is-primary': !view.result && !active }" :aria-label="i18n.tf('operations.panel.details_for', 'Details for {name}', { name: view.label })" :data-primary="!view.result ? '' : undefined" @click="emit('details', view.id)">{{ i18n.t("operations.panel.action_details", "Details") }}</button>
      <button v-if="active && view.cancelRequested" type="button" class="ops-btn" disabled>{{ i18n.t("operations.panel.action_cancelling", "Cancelling…") }}</button>
      <button v-else-if="active" type="button" class="ops-btn is-danger" :aria-label="i18n.tf('operations.panel.cancel_for', 'Cancel {name}', { name: view.label })" @click="emit('cancel', view.id)">{{ i18n.t("operations.panel.action_cancel", "Cancel") }}</button>
      <button v-else type="button" class="ops-btn is-quiet" :aria-label="i18n.tf('operations.panel.remove_for', 'Remove {name}', { name: view.label })" @click="emit('remove', view.id)">{{ i18n.t("operations.panel.action_remove", "Remove") }}</button>
    </div>
  </li>
</template>
