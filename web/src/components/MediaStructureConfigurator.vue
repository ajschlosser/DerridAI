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
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import AudioSpeakerAssignments from "./corpus-builder/AudioSpeakerAssignments.vue";

const props = withDefaults(defineProps<{
  mediaKind?: string;
  filename: string;
  pageCount?: number;
  blockCount?: number;
  audioProvenance?: {
    duration_seconds?: number;
    model?: string;
    provider?: string;
    diarization_requested?: boolean;
    diarization_status?: string;
  };
  speakers?: string[];
  voiceAssignments?: Record<string, string>;
  disabled?: boolean;
  voiceAssignmentsBusy?: boolean;
}>(), {
  speakers: () => [],
  voiceAssignments: () => ({}),
  disabled: false,
  voiceAssignmentsBusy: false,
});
const emit = defineEmits<{
  saveVoiceAssignments: [assignments: Record<string, string>];
}>();
const i18n = useI18nStore();
const copy = computed(() => {
  switch (props.mediaKind) {
    case "audio":
      return {
        title: i18n.t("pdf_corpus.audio_structure_title", "Audio transcript & speaker timeline"),
        help: i18n.t(
          "pdf_corpus.audio_structure_help",
          "Audio is organized by timestamps and speaker turns, not printed pages. Review the transcript and diarization as evidence before record construction.",
        ),
        label: i18n.t("pdf_corpus.audio_structure_label", "Timed source"),
        detail: i18n.t(
          "pdf_corpus.audio_structure_detail",
          "Records retain time ranges and speaker labels. Page-number controls are intentionally unavailable.",
        ),
      };
    case "docx":
    case "rtf":
      return {
        title: i18n.t("pdf_corpus.structured_text_structure_title", "Document structure & pagination"),
        help: i18n.t(
          "pdf_corpus.structured_text_structure_help",
          "Structured documents can expose detected, native, or estimated page boundaries. Review the page scope below before record construction.",
        ),
        label: i18n.t("pdf_corpus.structured_text_structure_label", "Structured document"),
        detail: i18n.t(
          "pdf_corpus.structured_text_structure_detail",
          "Page selection applies to this build only; the complete extracted source remains preserved.",
        ),
      };
    case "text":
    case "html":
    case "gutenberg":
    case "url":
      return {
        title: i18n.t("pdf_corpus.text_structure_title", "Text structure & segmentation"),
        help: i18n.t(
          "pdf_corpus.text_structure_help",
          "Plain and web text are already logical text streams. Review headings, paragraph boundaries, and cleanup before record construction rather than assigning physical pages.",
        ),
        label: i18n.t("pdf_corpus.text_structure_label", "Logical text source"),
        detail: i18n.t(
          "pdf_corpus.text_structure_detail",
          "Segmentation follows extracted text order; printed-page mapping is not applicable.",
        ),
      };
    case "image":
      return {
        title: i18n.t("pdf_corpus.image_structure_title", "Image & OCR interpretation"),
        help: i18n.t(
          "pdf_corpus.image_structure_help",
          "Images are treated as visual sources. Review OCR quality, reading order, and image boundaries; pagination is available only when the image set represents paginated material.",
        ),
        label: i18n.t("pdf_corpus.image_structure_label", "Visual source"),
        detail: i18n.t(
          "pdf_corpus.image_structure_detail",
          "OCR text remains linked to the image source so reviewers can distinguish extracted words from the original visual evidence.",
        ),
      };
    default:
      return {
        title: i18n.t("pdf_corpus.source_structure_title", "Source interpretation"),
        help: i18n.t(
          "pdf_corpus.source_structure_help",
          "Review how this source should be interpreted before records are built.",
        ),
        label: i18n.t("pdf_corpus.source_structure_label", "Source"),
        detail: i18n.t(
          "pdf_corpus.source_structure_detail",
          "Source-specific controls are shown when applicable.",
        ),
      };
  }
});
</script>

<template>
  <section class="media-structure" :aria-labelledby="`media-structure-${mediaKind || 'source'}`">
    <header>
      <div>
        <span class="eyebrow">{{ copy.label }}</span>
        <h3 :id="`media-structure-${mediaKind || 'source'}`">{{ copy.title }}</h3>
        <p>{{ copy.help }}</p>
      </div>
      <span class="media-badge">{{ mediaKind || "source" }}</span>
    </header>
    <div class="media-facts">
      <span
        ><b>{{ filename }}</b></span
      >
      <span v-if="pageCount"
        >{{ pageCount }} {{ i18n.t("pdf_corpus.source_units", "source units") }}</span
      >
      <span v-if="blockCount">{{ blockCount }} {{ i18n.t("pdf_corpus.blocks", "blocks") }}</span>
    </div>
    <p class="media-detail">{{ copy.detail }}</p>

    <template v-if="mediaKind === 'audio'">
      <dl class="audio-status">
        <div>
          <dt>{{ i18n.t("pdf_corpus.audio_transcript_status", "Transcript") }}</dt>
          <dd>{{ blockCount ? i18n.t("pdf_corpus.audio_transcript_ready", "Ready") : i18n.t("pdf_corpus.audio_transcript_missing", "Unavailable") }}</dd>
        </div>
        <div v-if="audioProvenance?.duration_seconds">
          <dt>{{ i18n.t("pdf_corpus.audio_duration", "Duration") }}</dt>
          <dd>{{ Math.round(audioProvenance.duration_seconds) }}s</dd>
        </div>
        <div>
          <dt>{{ i18n.t("pdf_corpus.audio_diarization_status", "Speaker detection") }}</dt>
          <dd>{{ audioProvenance?.diarization_status || i18n.t("pdf_corpus.audio_diarization_unknown", "Unknown") }}</dd>
        </div>
        <div v-if="audioProvenance?.model">
          <dt>{{ i18n.t("pdf_corpus.audio_transcription_model", "Transcription model") }}</dt>
          <dd>{{ audioProvenance.model }}</dd>
        </div>
      </dl>
      <a class="audio-settings-link" href="/settings/services#settings-heading-audio">
        {{ i18n.t("pdf_corpus.audio_settings_link", "Audio transcription service settings") }}
      </a>
      <AudioSpeakerAssignments
        :speakers="speakers"
        :assignments="voiceAssignments"
        :disabled="disabled || voiceAssignmentsBusy"
        @save="emit('saveVoiceAssignments', $event)"
      />
    </template>
  </section>
</template>

<style scoped>
.media-structure {
  display: grid;
  gap: 14px;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.media-structure header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}
.eyebrow {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
h3 {
  margin: 4px 0;
}
p {
  margin: 0;
  max-width: 72ch;
  color: var(--muted);
  line-height: 1.5;
}
.media-badge {
  align-self: start;
  padding: 5px 9px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
  text-transform: capitalize;
}
.media-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--soft);
  font-size: 0.8125rem;
}
.media-detail {
  font-size: 0.875rem;
}
.audio-status {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 8px;
  margin: 0;
}
.audio-status div {
  display: grid;
  gap: 2px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--soft);
}
.audio-status dt {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 700;
}
.audio-status dd {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}
.audio-settings-link {
  justify-self: start;
  color: var(--accent-fg);
  font-size: 0.8125rem;
  font-weight: 700;
}
@media (max-width: 700px) {
  .media-structure header {
    display: grid;
  }
}
</style>
