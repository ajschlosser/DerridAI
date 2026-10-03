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
import UiButton from "../ui/UiButton.vue";
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import type { CorpusRecord } from "../../api/corpus";
import { recordIssueKinds } from "../../domain/corpusReview";
import { useI18nStore } from "../../stores/i18n";
import UiTooltip from "../ui/UiTooltip.vue";
import MovableRecordModal from "./MovableRecordModal.vue";
import RecordContextReader from "./RecordContextReader.vue";

/** The central Record reader for Review: Record text, text editing and the per-Record notices. */
const props = defineProps<{
  record: CorpusRecord | null;
  loading?: boolean;
  loadError?: string;
  buildId: string;
  visible: boolean;
  queueCollapsed: boolean;
  editing: boolean;
  busy: boolean;
  locked: boolean;
  activitySummary: string;
  popout: { recordId: string; text: string } | null;
}>();
const emit = defineEmits<{
  showQueue: [];
  beginEdit: [touchup: boolean];
  cancelEdit: [];
  cleanup: [];
  llmTouchup: [];
  save: [];
  markReviewed: [];
  openPopout: [];
  closePopout: [];
  selectRecord: [recordId: string];
  rootChange: [element: HTMLElement | null];
  retry: [];
}>();
const textDraft = defineModel<string>("textDraft", { required: true });
const showContext = defineModel<boolean>("showContext", { required: true });
const resolveSource = defineModel<boolean>("resolveSource", { required: true });
const i18n = useI18nStore();
function shortRecordId(recordId: string) {
  const match = /^.+?[-_.:](\d+)$/.exec(recordId);
  return match ? `#${Number(match[1])}` : recordId;
}
const recordLocator = computed(() => {
  const record = props.record;
  if (!record) return "";
  const start = record.page_start;
  const end = record.page_end;
  if (start == null || start === "") return "";
  const pages = end != null && end !== "" && end !== start ? `${start}–${end}` : String(start);
  return `${i18n.t("pdf_corpus.page_abbrev")} ${pages}`;
});
const recordHeading = computed(() => {
  const record = props.record;
  if (!record) return "";
  return [shortRecordId(String(record.record_id || "")), recordLocator.value]
    .filter(Boolean)
    .join(" · ");
});
const recordCitation = computed(() => String(props.record?.inline_citation || "").trim());
const showRecordId = computed(() => Boolean(props.record?.record_id));
const recordLengthLabel = computed(() =>
  props.record
    ? `${props.record.text_length.toLocaleString()} ${i18n.t("pdf_corpus.characters")}`
    : "",
);
const root = ref<HTMLElement | null>(null);
onMounted(() => emit("rootChange", root.value));
onBeforeUnmount(() => emit("rootChange", null));
</script>

<template>
  <article
    v-show="visible"
    ref="root"
    class="record-review-pane"
    :aria-busy="loading"
    :aria-labelledby="record ? 'review-record-title' : undefined"
  >
    <template v-if="record">
      <header class="record-review-head">
        <div>
          <button
            v-if="queueCollapsed"
            type="button"
            class="link-button queue-toggle"
            @click="emit('showQueue')"
          >
            {{ i18n.t("pdf_corpus.show_queue") }}</button
          ><span class="eyebrow">{{ i18n.t("pdf_corpus.proposed_record") }}</span>
          <h3 id="review-record-title">{{ recordHeading }}</h3>
          <p class="record-meta">
            <span v-if="recordCitation" class="record-citation">{{ recordCitation }}</span>
            <code v-if="showRecordId" class="record-id">{{ record.record_id }}</code>
            <span>{{ recordLengthLabel }}</span
            >{{ activitySummary }}
            <span v-if="record.text_review_status === 'human_corrected'" class="human-corrected">{{
              i18n.t("pdf_corpus.human_corrected")
            }}</span
            ><span
              v-else-if="record.text_review_status === 'human_reviewed'"
              class="human-corrected"
              >{{ i18n.t("pdf_corpus.human_reviewed") }}</span
            >
          </p>
        </div>
        <div class="record-text-head-actions">
          <label v-if="!editing" class="context-toggle">
            <input v-model="showContext" type="checkbox" />
            <span :title="i18n.t('pdf_corpus.context_show')">{{
              i18n.t("pdf_corpus.context_short")
            }}</span>
          </label>
          <UiButton size="small" v-if="!editing" @click="emit('openPopout')">
            {{ i18n.t("pdf_corpus.popout_record") }}
          </UiButton>
          <UiButton size="small" v-if="editing" @click="emit('cleanup')" :disabled="busy || locked">
            {{ i18n.t("pdf_corpus.clean_text") }}</UiButton
          ><UiTooltip
            v-if="editing"
            :text="i18n.t('pdf_corpus.save_reviewed_text') + ' (Ctrl/Cmd S)'"
            trigger-mode="content"
            :content-focusable="Boolean(busy || locked || !textDraft.trim())"
            placement="bottom"
          >
            <button
              type="button"
              class="btn small primary"
              @click="emit('save')"
              :disabled="busy || locked || !textDraft.trim()"
              aria-keyshortcuts="Control+S Meta+S"
            >
              {{ i18n.t("ui.save") }}
            </button> </UiTooltip
          ><UiButton
            size="small"
            v-if="editing"
            @click="emit('llmTouchup')"
            :disabled="busy || locked"
          >
            {{ i18n.t("pdf_corpus.llm_touchup") }}</UiButton
          ><UiButton
            size="small"
            v-if="
              !editing &&
              record.text_review_status !== 'human_corrected' &&
              record.text_review_status !== 'human_reviewed'
            "
            @click="emit('markReviewed')"
            :disabled="busy || locked"
          >
            {{ i18n.t("pdf_corpus.mark_text_reviewed") }}</UiButton
          ><UiButton
            size="small"
            @click="editing ? emit('cancelEdit') : emit('beginEdit', false)"
            :disabled="busy || locked"
          >
            {{ editing ? i18n.t("ui.cancel") : i18n.t("pdf_corpus.edit_text") }}
          </UiButton>
        </div>
      </header>
      <aside
        v-if="record.text_touchup_proposal?.status === 'pending_review'"
        class="review-reason touchup-review-notice"
        data-tone="info"
        role="status"
      >
        <div class="touchup-review-copy">
          <b>{{ i18n.t("pdf_corpus.llm_touchup_proposal_available") }}</b>
          <span>{{ i18n.t("pdf_corpus.llm_touchup_proposal_help") }}</span>
        </div>
        <UiButton size="small" @click="emit('beginEdit', true)" :disabled="busy || locked">
          {{ i18n.t("pdf_corpus.review_touchup_proposal") }}
        </UiButton>
      </aside>
      <aside
        v-else-if="
          record.review_reason && record.review_reason.toLowerCase() !== 'pending human review.'
        "
        class="review-reason"
        role="note"
      >
        <b>{{
          recordIssueKinds(record).length
            ? recordIssueKinds(record)
                .map((kind) => i18n.t(`pdf_corpus.record_state.${kind}`, kind))
                .join(" · ")
            : i18n.t("pdf_corpus.why_review")
        }}</b
        ><span class="review-reason-text">{{ record.review_reason }}</span>
      </aside>
      <section class="record-text-review" aria-labelledby="reviewed-record-text-title">
        <b id="reviewed-record-text-title" class="sr-only">{{
          i18n.t("pdf_corpus.reviewed_record_text")
        }}</b>
        <textarea
          v-if="editing"
          v-model="textDraft"
          class="record-text-editor"
          :aria-label="i18n.t('pdf_corpus.reviewed_record_text')"
        ></textarea>
        <RecordContextReader
          v-else
          class="record-primary-text"
          :build-id="buildId"
          :record-id="record.record_id"
          :text="record.text"
          :show-context="showContext"
          @select="(id) => emit('selectRecord', id)"
        />
        <p v-if="record.text_noise?.score != null" class="record-noise-summary" role="status">
          {{
            i18n.tf("pdf_corpus.text_noise.score", {
              score: Math.round(Number(record.text_noise.score)),
            })
          }}
          <span v-if="record.text_noise.unusable">
            ·
            {{ i18n.t("pdf_corpus.text_noise.unusable") }}
          </span>
        </p>
        <div v-if="editing && record.source_quality_issues?.length" class="text-review-actions">
          <label v-if="record.source_quality_issues?.length" class="resolve-source-check"
            ><input v-model="resolveSource" type="checkbox" /><span>{{
              i18n.t("pdf_corpus.resolve_source_with_correction")
            }}</span></label
          >
        </div>
      </section>
      <MovableRecordModal
        v-if="popout"
        :record-id="popout.recordId"
        :text="popout.text"
        @close="emit('closePopout')"
      />
    </template>
    <div v-else-if="loading" class="reader-state" role="status" aria-live="polite">
      <b>{{ i18n.t("pdf_corpus.loading_record") }}</b>
      <div class="reader-skeleton" aria-hidden="true"><span></span><span></span><span></span></div>
    </div>
    <div v-else-if="loadError" class="reader-state" role="alert">
      <b>{{
        i18n.t(
          loadError === "not_found"
            ? "pdf_corpus.record_not_found"
            : "pdf_corpus.record_load_failed",
        )
      }}</b>
      <p v-if="loadError !== 'not_found'">{{ loadError }}</p>
      <UiButton :label="i18n.t('ui.retry')" @click="emit('retry')" />
    </div>
    <div v-else class="inspector-empty" role="status">
      {{ i18n.t("pdf_corpus.select_record") }}
    </div>
  </article>
</template>

<style scoped>
/* Review: the record pane. Reading typography stays quiet; the Record text is the largest area. */
.record-review-pane {
  min-width: 0;
  background: var(--surface-card);
}
.reader-state {
  display: grid;
  align-content: start;
  gap: var(--space-3);
  padding: var(--space-5);
  overflow-wrap: anywhere;
}
.reader-skeleton {
  display: grid;
  gap: var(--space-3);
}
.reader-skeleton span {
  height: var(--space-4);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
}
.reader-skeleton span:last-child {
  width: 65%;
}
.record-review-head {
  position: sticky;
  top: 0;
  z-index: 4;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-card);
}
.record-review-head > div:first-child {
  min-width: 0;
  flex: 1 1 8rem;
}
.record-review-head {
  align-items: center;
  gap: 6px 16px;
}
.record-review-head .human-corrected {
  margin-inline-start: 6px;
}
.record-review-head .eyebrow {
  display: none;
}
.record-review-head h3 {
  margin: 0;
  font-size: 1rem;
  overflow-wrap: anywhere;
}
.record-review-head p {
  margin: 2px 0 0;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}
.record-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 3px 8px;
  align-items: center;
}
.record-citation {
  color: var(--text-primary);
  font-weight: var(--fw-semibold);
}
.record-id {
  max-width: min(30rem, 52vw);
  padding: 1px 6px;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--surface-subtle);
  color: var(--text-tertiary);
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: var(--fs-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.record-primary-text {
  flex: 1;
  width: 100%;
  max-width: 76ch;
  margin: 0 auto;
  padding: 30px 38px;
  white-space: pre-wrap;
  font:
    17px/1.72 Georgia,
    serif;
}
.record-text-review {
  display: grid;
  flex: none;
  gap: 0;
  margin: 0;
  background: var(--surface-card);
}
/* The text card keeps its full height and the pane scrolls, so a long record is never clipped. */
.record-text-review .record-primary-text {
  padding: 24px 28px 40px;
  min-height: 220px;
  max-height: none;
  overflow: visible;
}
.record-text-review > header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 6px 12px;
  padding: 6px 16px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-subtle);
}
.record-text-review > header > div {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.record-text-review > header b {
  font-size: 0.875rem;
  white-space: nowrap;
}
.record-text-head-actions {
  display: flex;
  flex: 1 1 auto;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  min-width: 0;
  gap: 6px;
}
.record-text-head-actions :deep(.ui-button) {
  white-space: nowrap;
}
.human-corrected {
  display: inline-flex;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
  font-size: 0.8125rem;
  font-weight: 800;
}
.context-toggle {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  cursor: pointer;
}
.record-noise-summary {
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: 0.8125rem;
}
.record-text-editor {
  width: calc(100% - 24px);
  min-height: 330px;
  height: min(62vh, 720px);
  max-height: 72vh;
  overflow-y: auto;
  overscroll-behavior: contain;
  margin: 0 12px;
  padding: 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--surface-card);
  color: var(--text-primary);
  font:
    16px/1.65 Georgia,
    serif;
  resize: vertical;
}
.record-text-editor:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 2px;
}
.text-review-actions {
  position: sticky;
  bottom: 0;
  z-index: 5;
  display: grid;
  gap: 10px;
  padding: 10px 12px 12px;
  border-top: 1px solid var(--border-subtle);
  background: var(--surface-card);
  box-shadow: var(--shadow-sm);
}
.resolve-source-check {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: 8px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.resolve-source-check input {
  inline-size: 18px;
  block-size: 18px;
  flex: 0 0 auto;
  margin-top: 2px;
  accent-color: var(--ui-accent);
}
/* Per-record notices are one quiet line, so moving between records does not push the text around. */
.review-reason {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  margin: 10px 16px 0;
  padding: 0.375rem 0.625rem;
  border: 1px solid var(--tone-warn-edge);
  border-radius: var(--radius-control);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.review-reason > b {
  flex: none;
}
.review-reason-text {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.review-reason :deep(.ui-button) {
  flex: none;
}
/* The LLM touch-up notice is informational, and its explanation must stay readable: it wraps. */
.review-reason.touchup-review-notice {
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  padding: 0.5rem 0.75rem;
  border-color: var(--tone-info-border);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
}
.touchup-review-copy {
  display: grid;
  flex: 1 1 22ch;
  gap: 0.125rem;
  min-width: 0;
  line-height: 1.45;
}
.review-reason.touchup-review-notice :deep(.ui-button) {
  margin-inline-start: auto;
}

.record-review-head p {
  font-size: 0.8125rem !important;
}
@media (max-width: 1400px) {
  .record-primary-text {
    font-size: 1rem;
    padding: 24px;
  }
}
@media (max-width: 760px) {
  .record-primary-text {
    font-size: 1rem;
    padding: 20px 18px;
  }
}
</style>
