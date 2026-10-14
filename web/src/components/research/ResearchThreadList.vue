<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResearchJob } from "../../types/research";
import { researchJobDetail } from "./researchI18n";

const ACTIVE = ["queued", "running", "cancelling"];

const props = withDefaults(
  defineProps<{
    jobs?: ResearchJob[];
    selectedJobId?: string;
    canManage?: boolean;
    limit?: number;
    now?: number;
  }>(),
  { jobs: () => [], selectedJobId: "", canManage: false, limit: 12, now: () => Date.now() },
);
const emit = defineEmits<{
  select: [job: ResearchJob];
  cancel: [job: ResearchJob];
  new: [];
  openRuns: [];
}>();
const i18n = useI18nStore();
const list = ref<HTMLElement | null>(null);

function stamp(job: ResearchJob) {
  const value = Date.parse(String(job.finished_at || job.started_at || job.created_at || ""));
  return Number.isFinite(value) ? value : 0;
}
const running = computed(() => props.jobs.filter((job) => ACTIVE.includes(job.status)));
const recent = computed(() =>
  props.jobs
    .filter((job) => !ACTIVE.includes(job.status))
    .sort((a, b) => stamp(b) - stamp(a))
    .slice(0, props.limit),
);
const ordered = computed(() => [...running.value, ...recent.value]);
const hidden = computed(() => props.jobs.length - ordered.value.length);
// Roving tabindex: one stop in the tab order, arrow keys move between threads.
const focusId = computed(
  () =>
    ordered.value.find((job) => job.id === props.selectedJobId)?.id || ordered.value[0]?.id || "",
);

function title(job: ResearchJob) {
  return (
    String(job.prompt || "")
      .replace(/\s+/g, " ")
      .trim() || i18n.t("research.untitled_run", "Untitled research run")
  );
}
function statusLabel(job: ResearchJob) {
  return i18n.t(`research.status_${job.status}`, job.status);
}
function meta(job: ResearchJob) {
  if (ACTIVE.includes(job.status))
    return researchJobDetail(job, (key, fallback) => i18n.t(key, fallback), i18n.locale);
  const source = job.source_collection || i18n.t("research.evidence_only", "Evidence only");
  const when = relative(job);
  return when ? `${source} · ${when}` : source;
}
function relative(job: ResearchJob) {
  const value = stamp(job);
  if (!value) return "";
  const seconds = Math.round((value - props.now) / 1000);
  const format = new Intl.RelativeTimeFormat(i18n.locale, { numeric: "auto" });
  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  for (const [unit, size] of units)
    if (Math.abs(seconds) >= size) return format.format(Math.round(seconds / size), unit);
  return format.format(0, "minute");
}
function onKeydown(event: KeyboardEvent, index: number) {
  const last = ordered.value.length - 1;
  const target =
    event.key === "ArrowDown"
      ? Math.min(last, index + 1)
      : event.key === "ArrowUp"
        ? Math.max(0, index - 1)
        : event.key === "Home"
          ? 0
          : event.key === "End"
            ? last
            : -1;
  if (target < 0) return;
  event.preventDefault();
  void nextTick(() =>
    list.value?.querySelectorAll<HTMLButtonElement>(".research-thread-main")[target]?.focus(),
  );
}
</script>

<template>
  <nav
    class="research-thread-list card"
    :aria-label="i18n.t('research.thread_list', 'Research threads')"
  >
    <header class="research-thread-head">
      <b>{{ i18n.t("research.threads", "Threads") }}</b>
      <button class="btn" type="button" @click="emit('new')">
        <AppIcon name="plus" />{{ i18n.t("research.new_question", "New question") }}
      </button>
    </header>
    <ul v-if="ordered.length" ref="list" class="research-thread-items">
      <template v-for="(job, index) in ordered" :key="job.id">
        <li v-if="index === 0 && running.length" class="research-thread-group" aria-hidden="true">
          {{ i18n.t("research.threads_running", "Running") }}
        </li>
        <li
          v-if="index === running.length && recent.length"
          class="research-thread-group"
          aria-hidden="true"
        >
          {{ i18n.t("research.threads_recent", "Recent") }}
        </li>
        <li :class="['research-thread', job.status, { selected: job.id === selectedJobId }]">
          <button
            class="research-thread-main"
            type="button"
            :tabindex="job.id === focusId ? 0 : -1"
            :aria-current="job.id === selectedJobId ? 'true' : undefined"
            @click="emit('select', job)"
            @keydown="onKeydown($event, index)"
          >
            <span :class="['research-run-status-dot', job.status]" aria-hidden="true"></span>
            <span class="research-thread-copy"
              ><b>{{ title(job) }}</b
              ><small>{{ meta(job) }}</small></span
            >
            <span class="sr-only">{{ statusLabel(job) }}</span>
          </button>
          <button
            v-if="canManage && ACTIVE.includes(job.status)"
            class="research-thread-cancel"
            type="button"
            :disabled="job.status === 'cancelling' || job.cancel_requested"
            :aria-label="`${i18n.t('research.cancel_run', 'Cancel research run')}: ${title(job)}`"
            @click="emit('cancel', job)"
          >
            ×
          </button>
        </li>
      </template>
    </ul>
    <p v-else class="research-thread-empty">
      {{ i18n.t("research.no_runs_help", "Completed and active runs will appear here.") }}
    </p>
    <footer v-if="canManage" class="research-thread-foot">
      <button class="research-text-action" type="button" @click="emit('openRuns')">
        <AppIcon name="history" />{{ i18n.t("research.view_all_runs", "View all runs")
        }}<template v-if="hidden > 0"> ({{ jobs.length }})</template>
      </button>
    </footer>
  </nav>
</template>

<style scoped>
.research-thread-list {
  position: sticky;
  top: 118px;
  max-height: calc(100vh - 138px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 13px;
}
.research-thread-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 11px 12px;
  border-bottom: 1px solid var(--line);
}
.research-thread-head b {
  font-size: 0.8125rem;
}
.research-thread-head .btn {
  min-height: 32px;
  padding: 5px 8px;
  font-size: 0.8125rem;
}
.research-thread-items {
  flex: 1 1 auto;
  overflow: auto;
  margin: 0;
  padding: 6px;
  list-style: none;
}
.research-thread-group {
  padding: 8px 8px 4px;
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.research-thread {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  border-radius: 8px;
}
.research-thread:hover {
  background: var(--surface-raised);
}
.research-thread.selected {
  background: var(--ui-accent-soft);
}
.research-thread-main {
  min-height: 48px;
  display: grid;
  grid-template-columns: 9px minmax(0, 1fr);
  gap: 9px;
  align-items: start;
  padding: 8px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-2);
  text-align: left;
  cursor: pointer;
}
.research-thread-main:focus-visible,
.research-thread-cancel:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: -1px;
}
.research-thread-main .research-run-status-dot {
  margin-top: 5px;
}
.research-thread-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.research-thread-copy b {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  font-size: 0.8125rem;
  line-height: 1.35;
}
.research-thread.selected .research-thread-copy b {
  color: var(--accent-fg);
}
.research-thread-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--muted);
  font-size: 0.75rem;
}
.research-thread-cancel {
  width: 30px;
  height: 30px;
  margin-right: 4px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  font-size: 1.0625rem;
  cursor: pointer;
}
.research-thread-cancel:hover:not(:disabled) {
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.research-thread-empty {
  margin: 0;
  padding: 18px 14px;
  color: var(--muted);
  font-size: 0.8125rem;
}
.research-thread-foot {
  padding: 6px 12px 10px;
  border-top: 1px solid var(--line);
}
@media (max-width: 1439px) {
  .research-thread-list {
    position: static;
    max-height: 260px;
  }
}
</style>
