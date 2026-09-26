<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import type { CorpusRecord, SourceBlock } from "../../api/corpus";
import { timeLabel } from "../../domain/sourceMedia";
import { useI18nStore } from "../../stores/i18n";
import FieldEvidenceList from "../FieldEvidenceList.vue";

const props = defineProps<{
  record: CorpusRecord;
  fields: string[];
  selectedField: string;
  blocks: SourceBlock[];
  evidenceBlockIds: Set<string>;
  paginatedSource: boolean;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  "update:selectedField": [field: string];
  toggleEvidence: [blockId: string];
}>();

const i18n = useI18nStore();
</script>

<template>
  <section
    id="review-panel-evidence"
    class="review-inspector-panel evidence-review-panel"
    role="tabpanel"
    aria-labelledby="review-tab-evidence"
    tabindex="0"
  >
    <p class="inspector-help">
      {{ i18n.t("pdf_corpus.evidence_review_help") }}
    </p>

    <FieldEvidenceList
      :evidence="props.record.metadata_evidence || {}"
      :fields="props.fields"
      :selected-field="props.selectedField"
      @select="emit('update:selectedField', $event)"
    />

    <div v-if="props.selectedField" class="source-blocks compact-source-blocks">
      <article
        v-for="block in props.blocks"
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
          · {{ props.selectedField }}
        </button>
      </article>
    </div>
  </section>
</template>

<style scoped>
.review-inspector-panel {
  min-width: 0;
}
.inspector-help {
  margin: 0;
  padding: 12px 14px 0;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.source-blocks {
  display: grid;
  gap: 8px;
  padding: 10px;
  min-width: 0;
}
.compact-source-blocks {
  padding-top: 6px;
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
.evidence-toggle {
  display: block;
  width: 100%;
  margin: 5px 0;
  padding: 6px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--soft);
  color: var(--text);
  font-size: 0.8125rem;
  text-align: start;
  cursor: pointer;
}
.evidence-toggle[aria-pressed="true"] {
  border-color: var(--accent);
  box-shadow: inset 3px 0 0 var(--accent);
}
.evidence-toggle:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.evidence-toggle:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
