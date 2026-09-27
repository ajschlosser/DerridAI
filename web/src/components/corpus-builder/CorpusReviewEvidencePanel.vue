<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import type { CorpusRecord, SourceBlock } from "../../api/corpus";
import { timeLabel } from "../../domain/sourceMedia";
import { metadataValueText } from "../../domain/metadataValues";
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import FieldEvidenceList from "../FieldEvidenceList.vue";

/**
 * Choosing the source spans that support a metadata value. Pick a field, then tick the spans: one calm list, the
 * chosen field always named at the top with how many spans back it, and a way to narrow the source instead of
 * scanning it.
 */
const props = defineProps<{
  record: CorpusRecord;
  fields: string[];
  selectedField: string;
  blocks: SourceBlock[];
  evidenceBlockIds: Set<string>;
  paginatedSource: boolean;
  disabled?: boolean;
  /** Tab/panel id prefix; Focus View uses its own so it never duplicates the workspace's ids. */
  idPrefix?: string;
}>();

const emit = defineEmits<{
  "update:selectedField": [field: string];
  toggleEvidence: [blockId: string];
}>();

const i18n = useI18nStore();
const query = ref("");
const onlySelected = ref(false);

const fieldLabel = computed(() =>
  i18n.t(`record.${props.selectedField}`, props.selectedField.replace(/_/g, " ")),
);
const fieldValue = computed(() =>
  metadataValueText((props.record as unknown as Record<string, unknown>)[props.selectedField]),
);
const values = computed(() => props.record as unknown as Record<string, unknown>);
// Fields that have a value but no bound evidence: the work still to do, and what "Next field" walks through.
const missing = computed(() =>
  props.fields.filter((field) => {
    const has = (props.record.metadata_evidence?.[field]?.block_ids || []).length > 0;
    return !has && metadataValueText(values.value[field]) !== "";
  }),
);
const nextMissing = computed(
  () => missing.value.find((field) => field !== props.selectedField) || "",
);
// Narrowing the list never changes what is selected; a filtered-out span stays cited.
const shown = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase();
  return props.blocks.filter(
    (block) =>
      (!onlySelected.value || props.evidenceBlockIds.has(block.block_id)) &&
      (!needle ||
        String(block.text || "")
          .toLocaleLowerCase()
          .includes(needle)),
  );
});
const selectedCount = computed(
  () => props.blocks.filter((block) => props.evidenceBlockIds.has(block.block_id)).length,
);
function locator(block: SourceBlock) {
  return block.locator_kind === "time"
    ? timeLabel(block.start, block.end)
    : props.paginatedSource && block.page != null
      ? `${i18n.t("pdf_corpus.page_abbrev")} ${block.page}`
      : block.block_id;
}
</script>

<template>
  <section
    :id="`${props.idPrefix || 'review'}-panel-evidence`"
    class="review-inspector-panel evidence-review-panel"
    role="tabpanel"
    :aria-labelledby="`${props.idPrefix || 'review'}-tab-evidence`"
    tabindex="0"
  >
    <p class="inspector-help">
      {{ i18n.t("pdf_corpus.evidence_review_help") }}
    </p>

    <div class="evidence-fields">
      <FieldEvidenceList
        :evidence="props.record.metadata_evidence || {}"
        :fields="props.fields"
        :selected-field="props.selectedField"
        :values="values"
        @select="emit('update:selectedField', $event)"
      />
    </div>

    <section
      v-if="props.selectedField"
      class="evidence-assign"
      :aria-label="i18n.tf('pdf_corpus.evidence_choosing_for', { field: fieldLabel })"
    >
      <header class="assign-head">
        <div class="assign-title">
          <span class="assign-eyebrow">{{
            i18n.tf("pdf_corpus.evidence_choosing_for", { field: fieldLabel })
          }}</span>
          <b v-if="fieldValue">{{ fieldValue }}</b>
          <span class="assign-count" role="status">{{
            selectedCount
              ? i18n.tf(`pdf_corpus.evidence_span_count_${selectedCount === 1 ? "one" : "many"}`, {
                  count: selectedCount,
                })
              : i18n.t("pdf_corpus.evidence_none_yet")
          }}</span>
        </div>
        <div class="assign-actions">
          <button
            v-if="nextMissing"
            type="button"
            class="btn small"
            @click="emit('update:selectedField', nextMissing)"
          >
            {{ i18n.t("pdf_corpus.evidence_next_field") }}
          </button>
          <button type="button" class="btn small" @click="emit('update:selectedField', '')">
            {{ i18n.t("pdf_corpus.evidence_done") }}
          </button>
        </div>
      </header>

      <div class="assign-filter">
        <input
          v-model="query"
          type="search"
          class="control"
          :aria-label="i18n.t('pdf_corpus.evidence_filter')"
          :placeholder="i18n.t('pdf_corpus.evidence_filter')"
        />
        <label class="only-selected">
          <input v-model="onlySelected" type="checkbox" />
          {{ i18n.t("pdf_corpus.evidence_only_selected") }}
        </label>
      </div>

      <ol class="source-blocks compact-source-blocks">
        <li
          v-for="block in shown"
          :key="block.block_id"
          class="source-block"
          :class="{ 'evidence-block': props.evidenceBlockIds.has(block.block_id) }"
        >
          <header>
            <span class="block-locator">{{ locator(block) }}</span>
            <span v-if="block.speaker || block.type" class="block-kind">{{
              block.speaker || block.type
            }}</span>
            <button
              type="button"
              class="evidence-toggle"
              :aria-pressed="props.evidenceBlockIds.has(block.block_id)"
              :disabled="props.disabled"
              :title="block.block_id"
              @click="emit('toggleEvidence', block.block_id)"
            >
              <AppIcon :name="props.evidenceBlockIds.has(block.block_id) ? 'check' : 'plus'" />{{
                i18n.t("pdf_corpus.evidence_use")
              }}<span class="sr-only"> · {{ locator(block) }} · {{ fieldLabel }}</span>
            </button>
          </header>
          <p>{{ block.text }}</p>
        </li>
        <li v-if="!shown.length" class="evidence-empty" role="status">
          {{ i18n.t("pdf_corpus.evidence_no_match") }}
        </li>
      </ol>
    </section>
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
.evidence-fields {
  padding: 0 10px;
}
.evidence-assign {
  display: grid;
  gap: 8px;
  margin-block-start: 12px;
  border-block-start: 1px solid var(--line);
}
.assign-head {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 6px 10px;
  padding: 10px 14px;
  border-block-end: 1px solid var(--line);
  background: var(--surface-card, var(--card));
}
.assign-title {
  display: grid;
  gap: 1px;
  min-width: 0;
}
.assign-eyebrow {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.assign-title b {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.9375rem;
}
.assign-count {
  font-size: 0.8125rem;
  font-weight: 650;
  color: var(--tone-ok-fg);
}
.assign-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.assign-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 12px;
  padding: 0 14px;
}
.assign-filter .control {
  flex: 1 1 10rem;
  min-inline-size: 0;
}
.only-selected {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 0.8125rem;
  cursor: pointer;
}
.source-blocks {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 4px 14px 16px;
  list-style: none;
  min-width: 0;
}
.source-block {
  position: relative;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-card, 9px);
  background: var(--surface-card, var(--card));
}
.source-block:hover {
  border-color: var(--border-strong, var(--line));
}
.source-block.evidence-block {
  border-color: var(--accent);
  background: var(--surface-selected, var(--soft));
  box-shadow: inset 3px 0 0 var(--accent);
}
:global([dir="rtl"]) .source-block.evidence-block {
  box-shadow: inset -3px 0 0 var(--accent);
}
.source-block header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 0.8125rem;
}
.block-locator {
  color: var(--text);
  font-weight: 700;
}
.block-kind {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-block p {
  max-width: 100%;
  margin: 6px 0 0;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  font: 0.875rem/1.55 var(--font-reading, Georgia, serif);
}
/* The whole card is the target: the button's pseudo-element stretches over it, so no aim is needed. */
.evidence-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-inline-start: auto;
  padding: 4px 10px;
  border: 1px solid var(--line);
  border-radius: var(--radius-pill, 999px);
  background: var(--surface-card, var(--soft));
  color: var(--text);
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 650;
  cursor: pointer;
}
.evidence-toggle::after {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
}
.evidence-toggle svg {
  inline-size: 0.875rem;
  block-size: 0.875rem;
}
.evidence-toggle[aria-pressed="true"] {
  border-color: var(--accent);
  background: var(--accent);
  color: var(--accent-on);
}
.evidence-toggle:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.evidence-toggle:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.evidence-empty {
  padding: 12px;
  color: var(--muted);
  font-size: 0.8125rem;
  text-align: center;
}
</style>
