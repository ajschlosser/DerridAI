<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import type { CorpusRecord, SourceBlock } from "../../api/corpus";
import type { ProviderProfile } from "../../api/system";
import { timeLabel } from "../../domain/sourceMedia";
import { useI18nStore } from "../../stores/i18n";
import CorpusBoundaryAdjudication from "../CorpusBoundaryAdjudication.vue";
import CorpusRevisionHistory from "../CorpusRevisionHistory.vue";
import CorpusSourceSummary from "../CorpusSourceSummary.vue";

const props = defineProps<{
  record: CorpusRecord;
  workspaceMode: "record" | "metadata" | "source";
  mediaKind?: string;
  audioUrl?: string;
  imageUrl?: string;
  showPdfExplorer: boolean;
  pdfUrl: string;
  page: number;
  pageCount: number;
  pageWidth: number;
  pageHeight: number;
  pageBlocks: SourceBlock[];
  visibleBlocks: SourceBlock[];
  evidenceIds: string[];
  evidenceBlockIds: Set<string>;
  selectedEvidenceField: string;
  paginatedSource: boolean;
  canPreviousSourcePage: boolean;
  canNextSourcePage: boolean;
  canMergePrevious: boolean;
  canMergeNext: boolean;
  profiles: ProviderProfile[];
  providerProfileId: string;
  modelOverride: string;
  activeRequests: number;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  previousSourcePage: [];
  nextSourcePage: [];
  openViewer: [];
  openPdfExplorer: [];
  "update:providerProfileId": [value: string];
  "update:modelOverride": [value: string];
  adjudicate: [direction: "previous" | "next", providerProfileId: string, model: string];
  toggleEvidence: [blockId: string];
  split: [blockId: string];
}>();

const i18n = useI18nStore();

const activeProfile = computed(() =>
  props.profiles.find((profile) => profile.id === props.providerProfileId),
);
const concurrencyLimit = computed(() =>
  Number(activeProfile.value?.max_concurrent_requests || 1),
);
const concurrencyRisk = computed(
  () =>
    activeProfile.value?.type === "ollama" &&
    props.activeRequests + 1 > concurrencyLimit.value,
);

function adjudicate(
  direction: "previous" | "next",
  providerProfileId: string,
  model: string,
) {
  emit("adjudicate", direction, providerProfileId, model);
}
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
      :zoomable="props.workspaceMode === 'source'"
      :can-previous="props.canPreviousSourcePage"
      :can-next="props.canNextSourcePage"
      @previous="emit('previousSourcePage')"
      @next="emit('nextSourcePage')"
      @open-viewer="emit('openViewer')"
      @open-pdf-explorer="emit('openPdfExplorer')"
    />

    <details class="source-tool-section">
      <summary>{{ i18n.t("pdf_corpus.boundary_second_reader") }}</summary>
      <CorpusBoundaryAdjudication
        :record="props.record"
        :can-previous="props.canMergePrevious"
        :can-next="props.canMergeNext"
        :busy="props.disabled"
        :profiles="props.profiles"
        :provider-profile-id="props.providerProfileId"
        :model-override="props.modelOverride"
        :concurrency-risk="concurrencyRisk"
        :active-requests="props.activeRequests"
        :concurrency-limit="concurrencyLimit"
        @update:provider-profile-id="emit('update:providerProfileId', $event)"
        @update:model-override="emit('update:modelOverride', $event)"
        @adjudicate="adjudicate"
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
          v-for="(block, index) in props.visibleBlocks"
          :key="block.block_id"
          class="source-block"
          :class="{ 'evidence-block': props.evidenceBlockIds.has(block.block_id) }"
        >
          <header>
            <span>{{ block.block_id }}</span>
            <span>
              {{
                block.locator_kind === "time"
                  ? timeLabel(block.start, block.end)
                  : props.paginatedSource
                    ? block.page
                    : block.block_id
              }}
              · {{ block.speaker || block.type }}
            </span>
          </header>
          <p>{{ block.text }}</p>
          <button
            v-if="props.selectedEvidenceField"
            type="button"
            class="evidence-toggle"
            :aria-pressed="props.evidenceBlockIds.has(block.block_id)"
            :disabled="props.disabled"
            @click="emit('toggleEvidence', block.block_id)"
          >
            {{
              props.evidenceBlockIds.has(block.block_id)
                ? i18n.t("pdf_corpus.remove_evidence")
                : i18n.t("pdf_corpus.add_evidence")
            }}
            · {{ props.selectedEvidenceField }}
          </button>
          <button
            v-if="index < props.visibleBlocks.length - 1"
            type="button"
            class="split-button"
            :disabled="props.disabled"
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
.review-inspector-panel {
  min-width: 0;
}
.source-review-panel {
  min-height: 100%;
  background: var(--card);
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
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.original-extraction-snapshot {
  max-width: 100%;
  max-height: 320px;
  margin: 10px 12px;
  padding: 12px;
  overflow: auto;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--soft);
  font:
    12px/1.5 ui-monospace,
    SFMono-Regular,
    Consolas,
    monospace;
}
.source-blocks {
  display: grid;
  gap: 8px;
  min-width: 0;
  padding: 10px;
}
.source-block {
  position: relative;
  min-width: 0;
  padding: 9px;
  border: 1px solid var(--line);
  border-radius: 9px;
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
  max-width: 100%;
  overflow-wrap: anywhere;
  color: var(--muted);
  font-size: 0.8125rem;
}
.source-block p {
  max-width: 100%;
  margin: 7px 0;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  font:
    0.8125rem/1.5 Georgia,
    serif;
}
.evidence-toggle,
.split-button {
  width: 100%;
  padding: 6px;
  color: var(--text);
  font-size: 0.8125rem;
  text-align: start;
  cursor: pointer;
}
.evidence-toggle {
  display: block;
  margin: 5px 0;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--soft);
}
.evidence-toggle[aria-pressed="true"] {
  border-color: var(--accent);
  box-shadow: inset 3px 0 0 var(--accent);
}
.split-button {
  display: block;
  border: 0;
  border-top: 1px dashed var(--line);
  background: transparent;
  color: var(--muted);
}
.evidence-toggle:focus-visible,
.split-button:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.evidence-toggle:disabled,
.split-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
:global(.detail-mode) .source-review-panel {
  padding-bottom: 18px;
}
:global(.detail-mode) .source-review-panel > :deep(.source-summary),
:global(.detail-mode) .source-tool-section {
  max-width: 1100px;
  margin-inline: auto;
}
</style>
