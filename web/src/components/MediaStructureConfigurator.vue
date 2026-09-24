<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";

const props = defineProps<{
  mediaKind?: string;
  filename: string;
  pageCount?: number;
  blockCount?: number;
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
        detail: i18n.t("pdf_corpus.source_structure_detail", "Source-specific controls are shown when applicable."),
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
      <span><b>{{ filename }}</b></span>
      <span v-if="pageCount">{{ pageCount }} {{ i18n.t("pdf_corpus.source_units", "source units") }}</span>
      <span v-if="blockCount">{{ blockCount }} {{ i18n.t("pdf_corpus.blocks", "blocks") }}</span>
    </div>
    <p class="media-detail">{{ copy.detail }}</p>
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
  font-size: 0.72rem;
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
@media (max-width: 700px) {
  .media-structure header {
    display: grid;
  }
}
</style>
