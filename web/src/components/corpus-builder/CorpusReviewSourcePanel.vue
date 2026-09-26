<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import type { CorpusRecord, SourceBlock } from "../../api/corpus";
import type { ProviderProfile } from "../../api/system";
import { timeLabel } from "../../domain/sourceMedia";
import { useI18nStore } from "../../stores/i18n";
import CorpusBoundaryAdjudication from "../CorpusBoundaryAdjudication.vue";
import CorpusRevisionHistory from "../CorpusRevisionHistory.vue";
import CorpusSourceSummary from "../CorpusSourceSummary.vue";

/** Source view of the selected record. The parent still owns every mutation. */
const props = defineProps<{
  record: CorpusRecord;
  // Source viewer
  mediaKind?: string;
  audioUrl?: string;
  imageUrl?: string;
  showPdfExplorer: boolean;
  pdfUrl?: string;
  page: number;
  pageCount: number;
  pageWidth: number;
  pageHeight: number;
  pageBlocks: SourceBlock[];
  evidenceIds: string[];
  zoomable: boolean;
  canPreviousPage: boolean;
  canNextPage: boolean;
  // Boundary second reader
  canMergePrevious: boolean;
  canMergeNext: boolean;
  profiles: ProviderProfile[];
  providerProfileId: string;
  modelOverride: string;
  concurrencyRisk: boolean;
  activeRequests: number;
  concurrencyLimit: number;
  // Extracted source text
  blocks: SourceBlock[];
  evidenceBlockIds: Set<string>;
  paginatedSource: boolean;
  selectedEvidenceField: string;
  busy: boolean;
}>();

const emit = defineEmits<{
  previousPage: [];
  nextPage: [];
  openViewer: [];
  openPdfExplorer: [];
  "update:providerProfileId": [value: string];
  "update:modelOverride": [value: string];
  adjudicate: [direction: "previous" | "next", providerProfileId: string, model: string];
  toggleEvidence: [blockId: string];
  split: [blockId: string];
}>();

const i18n = useI18nStore();
</script>

<template>
  <section
    id="review-panel-source"
    class="review-inspector-panel source-review-panel"
    role="tabpanel"
    aria-labelledby="review-tab-source"
    tabindex="0"
  >
    <CorpusSourceSummary
      :media-kind="props.mediaKind"
      :audio-url="props.audioUrl"
      :image-url="props.imageUrl"
      :show-pdf-explorer="props.showPdfExplorer"
      :pdf-url="props.pdfUrl"
      :page="props.page"
      :page-count="props.pageCount"
      :page-width="props.pageWidth"
      :page-height="props.pageHeight"
      :blocks="props.pageBlocks"
      :evidence-block-ids="props.evidenceIds"
      :zoomable="props.zoomable"
      :can-previous="props.canPreviousPage"
      :can-next="props.canNextPage"
      @previous="emit('previousPage')"
      @next="emit('nextPage')"
      @open-viewer="emit('openViewer')"
      @open-pdf-explorer="emit('openPdfExplorer')"
    />
    <details class="source-tool-section">
      <summary>{{ i18n.t("pdf_corpus.boundary_second_reader") }}</summary>
      <CorpusBoundaryAdjudication
        :record="props.record"
        :can-previous="props.canMergePrevious"
        :can-next="props.canMergeNext"
        :busy="props.busy"
        :profiles="props.profiles"
        :provider-profile-id="props.providerProfileId"
        :model-override="props.modelOverride"
        :concurrency-risk="props.concurrencyRisk"
        :active-requests="props.activeRequests"
        :concurrency-limit="props.concurrencyLimit"
        @update:provider-profile-id="emit('update:providerProfileId', $event)"
        @update:model-override="emit('update:modelOverride', $event)"
        @adjudicate="
          (direction, profileId, model) => emit('adjudicate', direction, profileId, model)
        "
      />
    </details>
    <details class="source-tool-section">
      <summary>{{ i18n.t("pdf_corpus.extracted_source_text") }}</summary>
      <p class="inspector-help">{{ i18n.t("pdf_corpus.extracted_source_text_help") }}</p>
      <pre v-if="props.record.source_extracted_text" class="original-extraction-snapshot">{{
        props.record.source_extracted_text
      }}</pre>
      <div class="source-blocks">
        <article
          v-for="(block, index) in props.blocks"
          :key="block.block_id"
          class="source-block"
          :class="{ 'evidence-block': props.evidenceBlockIds.has(block.block_id) }"
        >
          <header>
            <span>{{ block.block_id }}</span
            ><span
              >{{
                block.locator_kind === "time"
                  ? timeLabel(block.start, block.end)
                  : props.paginatedSource
                    ? block.page
                    : block.block_id
              }}
              · {{ block.speaker || block.type }}</span
            >
          </header>
          <p>{{ block.text }}</p>
          <button
            v-if="props.selectedEvidenceField"
            type="button"
            class="evidence-toggle"
            :aria-pressed="props.evidenceBlockIds.has(block.block_id)"
            :disabled="props.busy"
            @click="emit('toggleEvidence', block.block_id)"
          >
            {{
              props.evidenceBlockIds.has(block.block_id)
                ? i18n.t("pdf_corpus.remove_evidence")
                : i18n.t("pdf_corpus.add_evidence")
            }}
            · {{ props.selectedEvidenceField }}</button
          ><button
            v-if="index < props.blocks.length - 1"
            type="button"
            class="split-button"
            :disabled="props.busy"
            @click="emit('split', block.block_id)"
          >
            {{ i18n.t("pdf_corpus.split_after") }}
          </button>
        </article>
      </div>
    </details>
    <details class="source-tool-section">
      <summary>{{ i18n.t("pdf_corpus.revision_history") }}</summary>
      <CorpusRevisionHistory :record="props.record" />
    </details>
  </section>
</template>

<style scoped>
.source-review-panel {
  background: var(--card);
  min-height: 100%;
}
.source-tool-section {
  min-width: 0;
  border-top: 1px solid var(--line);
  background: var(--card);
}
.source-tool-section > summary {
  display: flex;
  align-items: center;
  min-height: 44px;
  padding: 10px 12px;
  font-size: 0.8125rem;
  font-weight: 800;
  cursor: pointer;
}
.source-tool-section :deep(.boundary-adjudication) {
  border: 0;
  border-radius: 0;
}
.inspector-help {
  margin: 0;
  padding: 12px 14px 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--muted);
}
.original-extraction-snapshot {
  max-height: 320px;
  overflow: auto;
  overflow-wrap: anywhere;
  max-width: 100%;
  white-space: pre-wrap;
  padding: 12px;
  margin: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--soft);
  font:
    13px/1.52 Georgia,
    serif;
}
.source-blocks {
  display: grid;
  gap: 8px;
  padding: 10px;
  min-width: 0;
}
.source-block {
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 9px;
  position: relative;
}
.source-block.evidence-block {
  box-shadow: inset 3px 0 0 var(--accent);
}
:global([dir="rtl"]) .source-block.evidence-block {
  box-shadow: inset -3px 0 0 var(--accent);
}
.source-block header {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.8125rem;
  color: var(--muted);
  overflow-wrap: anywhere;
  max-width: 100%;
}
.source-block p {
  white-space: pre-wrap;
  font:
    13px/1.52 Georgia,
    serif;
  margin: 7px 0;
  overflow-wrap: anywhere;
  max-width: 100%;
}
.split-button {
  display: block;
  width: 100%;
  border: 0;
  border-top: 1px dashed var(--line);
  background: transparent;
  color: var(--muted);
  font-size: 0.8125rem;
  padding: 5px;
  cursor: pointer;
}
.evidence-toggle {
  display: block;
  width: 100%;
  margin: 5px 0;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--soft);
  color: var(--text);
  font-size: 0.8125rem;
  padding: 6px;
  text-align: start;
  cursor: pointer;
}
.evidence-toggle[aria-pressed="true"] {
  border-color: var(--accent);
  box-shadow: inset 3px 0 0 var(--accent);
}
.split-button:focus-visible,
.evidence-toggle:focus-visible,
summary:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
:global(.detail-mode) .source-review-panel {
  padding-bottom: 18px;
}
:global(.detail-mode) .source-review-panel > :deep(.source-summary) {
  max-width: 1100px;
  margin-inline: auto;
}
:global(.detail-mode) .source-tool-section {
  max-width: 1100px;
  margin-inline: auto;
}
</style>
