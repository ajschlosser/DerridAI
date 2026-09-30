<script setup lang="ts">
import UiButton from "../ui/UiButton.vue";
// Copyright 2026 Aaron John Schlosser, PhD.
import { onBeforeUnmount, onMounted, ref } from "vue";
import type { CorpusRecord } from "../../api/corpus";
import { recordIssueKinds } from "../../domain/corpusReview";
import { useI18nStore } from "../../stores/i18n";
import UiTooltip from "../ui/UiTooltip.vue";
import MovableRecordModal from "./MovableRecordModal.vue";
import RecordContextReader from "./RecordContextReader.vue";

/** The central Record reader for Review: Record text, text editing and the per-Record notices. */
defineProps<{
  record: CorpusRecord | null;
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
}>();
const textDraft = defineModel<string>("textDraft", { required: true });
const showContext = defineModel<boolean>("showContext", { required: true });
const resolveSource = defineModel<boolean>("resolveSource", { required: true });
const i18n = useI18nStore();
const root = ref<HTMLElement | null>(null);
onMounted(() => emit("rootChange", root.value));
onBeforeUnmount(() => emit("rootChange", null));
</script>

<template>
  <article
    v-show="visible"
    ref="root"
    class="record-review-pane"
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
          <h3 id="review-record-title">{{ record.record_id }}</h3>
          <p>
            {{ record.inline_citation }}
            · {{ record.text_length.toLocaleString() }} {{ i18n.t("pdf_corpus.characters")
            }}{{ activitySummary }}
          </p>
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
        <header>
          <div>
            <b id="reviewed-record-text-title">{{ i18n.t("pdf_corpus.reviewed_record_text") }}</b
            ><span v-if="record.text_review_status === 'human_corrected'" class="human-corrected">{{
              i18n.t("pdf_corpus.human_corrected")
            }}</span
            ><span
              v-else-if="record.text_review_status === 'human_reviewed'"
              class="human-corrected"
              >{{ i18n.t("pdf_corpus.human_reviewed") }}</span
            >
          </div>
          <div class="record-text-head-actions">
            <label v-if="!editing" class="context-toggle">
              <input v-model="showContext" type="checkbox" />
              {{ i18n.t("pdf_corpus.context_show") }}
            </label>
            <UiButton size="small" v-if="!editing" @click="emit('openPopout')">
              {{ i18n.t("pdf_corpus.reviewed_record_text") }}
            </UiButton>
            <UiButton
              size="small"
              v-if="editing"
              @click="emit('cleanup')"
              :disabled="busy || locked"
            >
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
    <div v-else class="inspector-empty">
      {{ i18n.t("pdf_corpus.select_record") }}
    </div>
  </article>
</template>
