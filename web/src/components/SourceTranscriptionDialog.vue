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
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed, ref, watch } from "vue";
import UiDialog from "./ui/UiDialog.vue";
import UiButton from "./ui/UiButton.vue";
import { hasPages, timeLabel } from "../domain/sourceMedia";
import PdfEvidenceViewer from "./PdfEvidenceViewer.vue";
import { useI18nStore } from "../stores/i18n";
import type { SourceBlock } from "../api/pdfCorpus";
const props = withDefaults(
  defineProps<{
    open: boolean;
    mediaKind?: string;
    audioUrl?: string;
    imageUrl?: string;
    pdfUrl: string;
    page: number;
    pageCount: number;
    text: string;
    blocks?: SourceBlock[];
    voiceAssignments?: Record<string, string>;
    pageWidth?: number;
    pageHeight?: number;
    busy?: boolean;
    printedPage?: string | number | null;
  }>(),
  { blocks: () => [], pageWidth: 0, pageHeight: 0, busy: false, printedPage: null },
);
const emit = defineEmits<{
  close: [];
  pageChange: [page: number];
  saveText: [text: string];
  saveVoiceAssignments: [assignments: Record<string, string>];
}>();
const i18n = useI18nStore();
const audioElement = ref<HTMLAudioElement | null>(null);
const voices = computed(() =>
  Array.from(new Set(props.blocks.map((block) => String(block.speaker || "")).filter(Boolean))),
);
const draft = ref("");
watch(
  () => [props.open, props.text] as const,
  () => {
    if (props.open) draft.value = props.text;
  },
  { immediate: true },
);
function move(delta: number) {
  emit("pageChange", Math.max(1, Math.min(props.pageCount || 1, props.page + delta)));
}

function seekToBlock(block: SourceBlock) {
  if (!audioElement.value || typeof block.start !== "number") return;
  audioElement.value.currentTime = Math.max(0, block.start);
  void audioElement.value.play().catch(() => {
    // Browsers may refuse scripted playback; seeking still succeeds.
  });
}
</script>
<template>
  <UiDialog
    :open="open"
    :close-label="i18n.t('ui.close')"
    size="xlarge"
    :title="i18n.t('pdf_corpus.source_transcription_title')"
    :description="i18n.t('pdf_corpus.source_transcription_help')"
    @close="emit('close')"
  >
    <div v-if="hasPages(mediaKind)" class="source-toolbar">
      <div>
        <b>{{ i18n.tf("pdf_corpus.pdf_page", { page }) }}</b
        ><span v-if="printedPage !== null && printedPage !== undefined">
          ·
          {{ i18n.tf("pdf_corpus.printed_page_value", { page: printedPage }) }}</span
        >
      </div>
      <div>
        <UiButton :label="i18n.t('ui.previous')" :disabled="page <= 1" @click="move(-1)" /><span
          aria-live="polite"
          >{{ page }} / {{ pageCount }}</span
        ><UiButton :label="i18n.t('ui.next')" :disabled="page >= pageCount" @click="move(1)" />
      </div>
    </div>
    <div class="transcription-grid">
      <section class="source-pane" tabindex="0" :aria-label="i18n.t('pdf_corpus.source_context')">
        <PdfEvidenceViewer
          v-if="pdfUrl"
          :pdf-url="pdfUrl"
          :page="page"
          :page-width="pageWidth"
          :page-height="pageHeight"
          :blocks="blocks"
          :evidence-block-ids="blocks.map((b) => b.block_id)"
          :zoomable="true"
        />
        <img v-if="imageUrl" :src="imageUrl" :alt="i18n.t('pdf_corpus.source_context')" />
        <audio
          v-if="audioUrl"
          ref="audioElement"
          controls
          preload="metadata"
          :src="audioUrl"
          :aria-label="i18n.t('pdf_corpus.media_kind.audio')"
        />
        <fieldset v-if="audioUrl && voices.length" class="voice-assignments">
          <legend>{{ i18n.t("pdf_corpus.voice_assignments_title") }}</legend>
          <label v-for="voice in voices" :key="voice">
            <span>{{ voice }}</span>
            <input
              :value="voiceAssignments?.[voice] || ''"
              :disabled="busy"
              :placeholder="i18n.t('pdf_corpus.voice_assignment_placeholder')"
              @change="
                emit('saveVoiceAssignments', {
                  ...(voiceAssignments || {}),
                  [voice]: ($event.target as HTMLInputElement).value,
                })
              "
            />
          </label>
        </fieldset>
        <article
          v-for="block in pdfUrl ? [] : blocks"
          :key="block.block_id"
          :class="{ 'speaker-review-needed': block.speaker_assignment?.review_recommended }"
        >
          <button
            v-if="audioUrl && typeof block.start === 'number'"
            type="button"
            class="time-seek"
            :aria-label="
              i18n.t(
                'pdf_corpus.audio_seek_to_span',
                'Play this timed transcript span from its start.',
              )
            "
            @click="seekToBlock(block)"
          >
            {{ timeLabel(block.start, block.end) }}
            {{ voiceAssignments?.[String(block.speaker || "")] || block.speaker }}
          </button>
          <b v-else>
            {{ timeLabel(block.start, block.end) }}
            {{ voiceAssignments?.[String(block.speaker || "")] || block.speaker }}
          </b>
          <p>{{ block.text }}</p>
          <small v-if="block.speaker_assignment?.review_recommended" class="speaker-review-note">
            {{
              i18n.t(
                "pdf_corpus.audio_span_review_recommended",
                "Speaker assignment is uncertain for part of this span.",
              )
            }}
          </small>
        </article>
      </section>
      <section class="transcription-pane" :aria-busy="busy">
        <label
          ><span>{{ i18n.t("pdf_corpus.reviewed_record_text") }}</span
          ><textarea v-model="draft" :disabled="busy"></textarea>
        </label>
        <details>
          <summary>
            {{ i18n.t("pdf_corpus.extracted_source_blocks") }}
          </summary>
          <article v-for="block in blocks" :key="block.block_id">
            <b>{{ block.block_id }}</b>
            <pre>{{ block.text }}</pre>
          </article>
          <p v-if="!blocks.length">
            {{ i18n.t("pdf_corpus.source_loading_or_unavailable") }}
          </p>
        </details>
      </section>
    </div>
    <template #footer
      ><span>{{ i18n.t("pdf_corpus.manual_transcription_source_preserved") }}</span>
      <div class="footer-actions">
        <UiButton :label="i18n.t('ui.cancel')" @click="emit('close')" /><UiButton
          variant="primary"
          :disabled="busy || !draft.trim()"
          :label="i18n.t('pdf_corpus.save_transcription')"
          @click="emit('saveText', draft)"
        /></div
    ></template>
  </UiDialog>
</template>
<style scoped>
img,
audio {
  max-inline-size: 100%;
}
.source-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}
.source-toolbar > div:last-child,
.footer-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.transcription-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.85fr);
  gap: 16px;
  min-height: 62vh;
}
.source-pane,
.transcription-pane {
  min-width: 0;
  padding: 12px;
  overflow-wrap: anywhere;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: auto;
  background: var(--soft);
}
.transcription-pane {
  display: grid;
  align-content: start;
  gap: 12px;
}
.transcription-pane label {
  display: grid;
  gap: 7px;
  font-weight: 800;
}
.transcription-pane textarea {
  box-sizing: border-box;
  width: 100%;
  min-height: 48vh;
  resize: vertical;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
  color: var(--text);
  font:
    16px/1.65 Georgia,
    serif;
}
.transcription-pane details article {
  border-top: 1px solid var(--line);
  padding: 8px 0;
}
.transcription-pane pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  margin: 5px 0 0;
  font:
    13px/1.45 ui-monospace,
    monospace;
}
.source-pane:focus-visible,
.transcription-pane :is(textarea, summary):focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.source-pane article {
  padding: 10px 0;
  border-top: 1px solid var(--line);
}
.time-seek {
  padding: 4px 7px;
  border: 1px solid var(--border-interactive);
  border-radius: var(--radius-control);
  color: var(--accent-fg);
  background: var(--surface-card);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
.time-seek:hover {
  background: var(--surface-hover);
}
.time-seek:focus-visible {
  outline: var(--focus-ring-width) solid var(--accent);
  outline-offset: var(--focus-ring-offset);
}
.speaker-review-needed {
  padding-inline: 10px;
  border-inline-start: 3px solid var(--tone-warn-edge);
  background: var(--tone-warn-bg);
}
.speaker-review-note {
  display: block;
  margin-top: 5px;
  color: var(--tone-warn-fg);
}
.voice-assignments {
  display: grid;
  gap: 8px;
  margin: 12px 0;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 9px;
}
.voice-assignments label {
  display: grid;
  grid-template-columns: minmax(7rem, auto) 1fr;
  gap: 8px;
  align-items: center;
}
.voice-assignments input {
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
  color: var(--text);
}
@media (max-width: 850px) {
  .transcription-grid {
    grid-template-columns: 1fr;
  }
  .source-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
