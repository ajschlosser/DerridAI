<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
import type { CorpusRecord } from "../../api/pdfCorpus";
import AppIcon from "../AppIcon.vue";
import CorpusReviewShortcuts from "./CorpusReviewShortcuts.vue";

/** Focus View's header: which record this is, where it sits in the queue, movement, and the build's progress. */
const props = defineProps<{
  record: CorpusRecord;
  accepted: number;
  remaining: number;
  total: number;
  canHistoryBack?: boolean;
  canHistoryForward?: boolean;
  canPreviousRecord?: boolean;
  canNextRecord?: boolean;
}>();
const emit = defineEmits<{
  close: [];
  historyBack: [];
  historyForward: [];
  previousRecord: [];
  nextRecord: [];
}>();
const i18n = useI18nStore();
const closeButton = ref<HTMLButtonElement | null>(null);
defineExpose({ focusClose: () => closeButton.value?.focus({ preventScroll: true }) });

const state = computed(
  () =>
    props.record.review_disposition ||
    (props.record.accepted ? "accepted" : props.record.rejected ? "rejected" : "pending"),
);
const position = computed(() => {
  const index = Number(props.record.topology_index ?? -1),
    total = Number(props.record.topology_count ?? 0);
  return index >= 0 && total > 0 ? { index: index + 1, total } : null;
});
const progressPercent = computed(() =>
  props.total > 0 ? Math.min(100, Math.round((props.accepted / props.total) * 100)) : 0,
);
</script>

<template>
  <header class="focus-head">
    <div class="focus-title-block">
      <span class="eyebrow">{{ i18n.t("pdf_corpus.focus_view") }}</span>
      <h2 :id="`focus-title-${record.record_id}`">{{ record.record_id }}</h2>
      <div class="focus-facts">
        <span class="state-pill" :data-state="state">{{
          i18n.t(`pdf_corpus.disposition.${state}`, state)
        }}</span>
        <span v-if="record.inline_citation">{{ record.inline_citation }}</span>
        <span
          >{{ Number(record.text_length || String(record.text || "").length).toLocaleString() }}
          {{ i18n.t("pdf_corpus.characters") }}</span
        >
        <span
          v-if="record.text_noise?.score != null"
          class="state-pill"
          :data-state="record.text_noise.unusable ? 'rejected' : 'pending'"
          >{{
            i18n.tf("pdf_corpus.text_noise.score", {
              score: Math.round(Number(record.text_noise.score)),
            })
          }}</span
        >
      </div>
    </div>
    <nav class="focus-nav" :aria-label="i18n.t('pdf_corpus.focus_navigation')">
      <div class="focus-nav-group" role="group" :aria-label="i18n.t('record.previous_next')">
        <button
          class="btn small icon-only"
          type="button"
          :title="`${i18n.t('pdf_corpus.previous_record')} (Alt ←)`"
          :disabled="!canPreviousRecord"
          @click="emit('previousRecord')"
        >
          <AppIcon name="chevron-left" /><span class="sr-only">{{
            i18n.t("pdf_corpus.previous_record")
          }}</span>
        </button>
        <span class="focus-position" role="status">
          <template v-if="position"
            ><b>{{ position.index }}</b> / {{ position.total }}</template
          ><template v-else>—</template>
        </span>
        <button
          class="btn small icon-only"
          type="button"
          :title="`${i18n.t('pdf_corpus.next_record')} (Alt →)`"
          :disabled="!canNextRecord"
          @click="emit('nextRecord')"
        >
          <AppIcon name="chevron-right" /><span class="sr-only">{{
            i18n.t("pdf_corpus.next_record")
          }}</span>
        </button>
      </div>
      <div class="focus-nav-group" role="group" :aria-label="i18n.t('pdf_corpus.record_history')">
        <button
          class="btn small"
          type="button"
          :disabled="!canHistoryBack"
          @click="emit('historyBack')"
        >
          ← {{ i18n.t("ui.back") }}
        </button>
        <button
          class="btn small"
          type="button"
          :disabled="!canHistoryForward"
          @click="emit('historyForward')"
        >
          {{ i18n.t("ui.forward") }} →
        </button>
      </div>
    </nav>
    <div class="focus-head-actions">
      <CorpusReviewShortcuts />
      <button ref="closeButton" class="btn" type="button" @click="emit('close')">
        <AppIcon name="close" />{{ i18n.t("ui.close") }}<kbd aria-hidden="true">Esc</kbd>
      </button>
    </div>
    <div
      v-if="total > 0"
      class="focus-progress"
      role="progressbar"
      :aria-label="i18n.t('pdf_corpus.focus_progress_label')"
      aria-valuemin="0"
      :aria-valuemax="total"
      :aria-valuenow="accepted"
      :aria-valuetext="i18n.tf('pdf_corpus.focus_progress_summary', { accepted, remaining })"
    >
      <span :style="{ inlineSize: `${progressPercent}%` }"></span>
    </div>
  </header>
</template>

<style scoped>
.eyebrow {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted);
  font-weight: 800;
}
kbd {
  padding: 0 0.3rem;
  border: 1px solid color-mix(in srgb, currentColor 35%, transparent);
  border-radius: 4px;
  font: inherit;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1.4;
}
/* Header: identity on the left, movement in the middle, session controls on the right. */
.focus-head {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1.5rem;
  padding: 0.75rem clamp(16px, 2.5vw, 32px) 0.875rem;
  border-bottom: 1px solid var(--line);
  background: var(--surface-card, var(--card));
}
.focus-title-block {
  display: grid;
  gap: 0.125rem;
  min-width: 0;
  flex: 1 1 16rem;
}
.focus-head h2 {
  margin: 0;
  font-size: 1.25rem;
  line-height: 1.2;
  overflow-wrap: anywhere;
}
.focus-facts {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.75rem;
  font-size: 0.8125rem;
  color: var(--muted);
}
.state-pill {
  border: 1px solid var(--line);
  border-radius: var(--radius-pill, 999px);
  padding: 0.125rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 750;
}
.state-pill[data-state="accepted"] {
  border-color: var(--tone-ok-border);
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
}
.state-pill[data-state="rejected"] {
  border-color: var(--tone-danger-border);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.state-pill[data-state="pending"] {
  border-color: var(--tone-warn-border);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.focus-nav {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1rem;
}
.focus-nav-group {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}
.focus-nav .btn.icon-only {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-inline-size: 2.25rem;
  padding-inline: 0.5rem;
}
.focus-nav .btn svg,
.focus-head-actions .btn svg {
  inline-size: 1rem;
  block-size: 1rem;
}
.focus-position {
  min-inline-size: 5.5rem;
  text-align: center;
  font-size: 0.875rem;
  font-variant-numeric: tabular-nums;
  color: var(--muted);
}
.focus-position b {
  color: var(--text);
}
.focus-head-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.focus-head-actions .btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}
.focus-head-actions kbd {
  opacity: 0.8;
}
.focus-progress {
  position: absolute;
  inset-inline: 0;
  inset-block-end: -1px;
  block-size: 3px;
  background: var(--surface-inset, var(--soft));
}
.focus-progress span {
  display: block;
  block-size: 100%;
  background: var(--tone-ok-edge, var(--accent));
  transition: inline-size 240ms ease;
}
</style>
