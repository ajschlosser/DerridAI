<script setup lang="ts">
import { ref, watch } from "vue";
import UiDialog from "./ui/UiDialog.vue";
import UiButton from "./ui/UiButton.vue";
import PdfEvidenceViewer from "./PdfEvidenceViewer.vue";
import { useI18nStore } from "../stores/i18n";
import type { SourceBlock } from "../api/pdfCorpus";
const props = withDefaults(
  defineProps<{
    open: boolean;
    pdfUrl: string;
    page: number;
    pageCount: number;
    text: string;
    blocks?: SourceBlock[];
    pageWidth?: number;
    pageHeight?: number;
    busy?: boolean;
    printedPage?: string | number | null;
  }>(),
  { blocks: () => [], pageWidth: 0, pageHeight: 0, busy: false, printedPage: null },
);
const emit = defineEmits<{ close: []; pageChange: [page: number]; saveText: [text: string] }>();
const i18n = useI18nStore();
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
</script>
<template>
  <UiDialog
    :open="open"
    size="xlarge"
    :title="i18n.t('pdf_corpus.source_transcription_title', 'Source viewer & manual transcription')"
    :description="
      i18n.t(
        'pdf_corpus.source_transcription_help',
        'Inspect the rendered PDF/OCR source at full size while correcting the reviewed record text. Source extraction remains immutable.',
      )
    "
    @close="emit('close')"
  >
    <div class="source-toolbar">
      <div>
        <b>{{ i18n.tf("pdf_corpus.pdf_page", "PDF page {page}", { page }) }}</b
        ><span v-if="printedPage !== null && printedPage !== undefined">
          ·
          {{
            i18n.tf("pdf_corpus.printed_page_value", "printed p. {page}", { page: printedPage })
          }}</span
        >
      </div>
      <div>
        <UiButton
          :label="i18n.t('ui.previous', 'Previous')"
          :disabled="page <= 1"
          @click="move(-1)"
        /><span aria-live="polite">{{ page }} / {{ pageCount }}</span
        ><UiButton
          :label="i18n.t('ui.next', 'Next')"
          :disabled="page >= pageCount"
          @click="move(1)"
        />
      </div>
    </div>
    <div class="transcription-grid">
      <section class="source-pane" :aria-label="i18n.t('pdf_corpus.source_pdf', 'Source PDF')">
        <PdfEvidenceViewer
          :pdf-url="pdfUrl"
          :page="page"
          :page-width="pageWidth"
          :page-height="pageHeight"
          :blocks="blocks"
          :evidence-block-ids="blocks.map((b) => b.block_id)"
          :zoomable="true"
        />
      </section>
      <section class="transcription-pane">
        <label
          ><span>{{ i18n.t("pdf_corpus.reviewed_record_text", "Reviewed record text") }}</span
          ><textarea v-model="draft" :disabled="busy"></textarea>
        </label>
        <details>
          <summary>
            {{ i18n.t("pdf_corpus.extracted_source_blocks", "Extracted source blocks") }}
          </summary>
          <article v-for="block in blocks" :key="block.block_id">
            <b>{{ block.block_id }}</b>
            <pre>{{ block.text }}</pre>
          </article>
          <p v-if="!blocks.length">
            {{
              i18n.t(
                "pdf_corpus.source_loading_or_unavailable",
                "Source blocks are loading or unavailable.",
              )
            }}
          </p>
        </details>
      </section>
    </div>
    <template #footer
      ><span>{{
        i18n.t(
          "pdf_corpus.manual_transcription_source_preserved",
          "Saving changes updates reviewed text only; the PDF and extracted source remain unchanged.",
        )
      }}</span>
      <div class="footer-actions">
        <UiButton :label="i18n.t('ui.cancel', 'Cancel')" @click="emit('close')" /><UiButton
          variant="primary"
          :disabled="busy || !draft.trim()"
          :label="i18n.t('pdf_corpus.save_transcription', 'Save transcription')"
          @click="emit('saveText', draft)"
        /></div
    ></template>
  </UiDialog>
</template>
<style scoped>
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
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: auto;
  background: var(--soft);
}
.transcription-pane {
  padding: 12px;
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
  margin: 5px 0 0;
  font:
    13px/1.45 ui-monospace,
    monospace;
}
.transcription-pane :is(textarea, summary):focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
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
