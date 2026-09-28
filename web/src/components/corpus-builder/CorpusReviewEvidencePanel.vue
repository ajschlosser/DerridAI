<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { CorpusRecord, SourceBlock } from "../../api/corpus";
import { corpusMetadataApi, type EvidenceSuggestion } from "../../api/corpus/metadata";
import { timeLabel } from "../../domain/sourceMedia";
import { metadataValueText } from "../../domain/metadataValues";
import { useI18nStore } from "../../stores/i18n";
import { allEvidenceBlockIds } from "../../domain/metadataEvidence";
import { precedentEvidenceSuggestions } from "../../domain/metadataPrecedents";
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
  /** Enables suggestions; without a build there is nothing to ask. */
  buildId?: string;
  /** Provider request for model suggestions; the button is hidden when absent. */
  llmRequest?: Record<string, unknown> | null;
  /** Tab/panel id prefix; Focus View uses its own so it never duplicates the workspace's ids. */
  idPrefix?: string;
}>();

const emit = defineEmits<{
  "update:selectedField": [field: string];
  toggleEvidence: [blockId: string];
  /** Replace the field's cited spans with exactly these block ids (select all / clear). */
  setEvidence: [blockIds: string[]];
  /** Open the source browser to cite (or un-cite) spans for the selected field from other records. */
  browseExternal: [];
}>();

const i18n = useI18nStore();
const query = ref("");
const suggestions = ref<EvidenceSuggestion[]>([]);
const semanticStatus = ref<"available" | "fallback" | "idle">("idle");
const semanticStatusReason = ref("");
const suggestState = ref<"idle" | "loading" | "done" | "failed">("idle");
// Suggestions belong to one field of one record; never carry them across.
watch(
  () => [props.record.record_id, props.selectedField],
  () => {
    suggestions.value = [];
    semanticStatus.value = "idle";
    semanticStatusReason.value = "";
    suggestState.value = "idle";
  },
);
async function suggest(kind: "lexical" | "llm" | "precedents") {
  if (!props.buildId || !props.selectedField) return;
  suggestState.value = "loading";
  const field = props.selectedField;
  const recordId = props.record.record_id;
  try {
    // Precedents contribute only this record's own blocks that resemble their reviewed evidence.
    let items: EvidenceSuggestion[];
    if (kind === "precedents") {
      items = precedentEvidenceSuggestions(
        await corpusMetadataApi.precedents(props.buildId, recordId, field),
        props.record.source_block_ids || [],
      );
      semanticStatus.value = "idle";
      semanticStatusReason.value = "";
    } else if (kind === "llm" && props.llmRequest) {
      items = (
        await corpusMetadataApi.suggestEvidenceLlm(props.buildId, recordId, field, props.llmRequest)
      ).items;
      semanticStatus.value = "idle";
      semanticStatusReason.value = "";
    } else {
      const response = await corpusMetadataApi.suggestEvidence(props.buildId, recordId, field);
      items = response.items;
      semanticStatus.value = response.status?.semantic === "fallback" ? "fallback" : "available";
      semanticStatusReason.value = response.status?.reason || "";
    }
    if (field !== props.selectedField || recordId !== props.record.record_id) return;
    suggestions.value = items;
    suggestState.value = "done";
  } catch {
    suggestState.value = "failed";
  }
}
const suggestionFor = (blockId: string) =>
  suggestions.value.find((item) => item.block_id === blockId);
const suggestionLabel = (item: EvidenceSuggestion) =>
  item.lexical_support === false
    ? i18n.t("pdf_corpus.evidence_suggest_unverified")
    : item.method.startsWith("llm")
      ? i18n.t("pdf_corpus.evidence_suggested_llm")
      : item.method.startsWith("precedent")
        ? i18n.t("pdf_corpus.evidence_suggested_precedent")
        : item.lexical_score != null && item.semantic_score != null
          ? i18n.t("pdf_corpus.evidence_suggested_lexical_semantic")
          : item.semantic_score != null
            ? i18n.t("pdf_corpus.evidence_suggested_semantic")
            : i18n.t("pdf_corpus.evidence_suggested_lexical");
const rank = (blockId: string) => {
  const index = suggestions.value.findIndex((item) => item.block_id === blockId);
  return index < 0 ? Number.MAX_SAFE_INTEGER : index;
};
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
    const has = allEvidenceBlockIds(props.record.metadata_evidence?.[field]).length > 0;
    return !has && metadataValueText(values.value[field]) !== "";
  }),
);
const nextMissing = computed(
  () => missing.value.find((field) => field !== props.selectedField) || "",
);
// Narrowing the list never changes what is selected; a filtered-out span stays cited.
const shown = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase();
  return props.blocks
    .filter(
      (block) =>
        (!onlySelected.value || props.evidenceBlockIds.has(block.block_id)) &&
        (!needle ||
          String(block.text || "")
            .toLocaleLowerCase()
            .includes(needle)),
    )
    .sort((a, b) => rank(a.block_id) - rank(b.block_id));
});
// Spans cited from other records of the same source; kept apart from the record's own spans.
const externalCount = computed(
  () => props.record.metadata_evidence?.[props.selectedField]?.external_block_ids?.length || 0,
);
const selectedCount = computed(
  () => props.blocks.filter((block) => props.evidenceBlockIds.has(block.block_id)).length,
);
// "Select all" and "Clear" act on what is shown, so a filter narrows them; spans filtered out stay as they are.
const allShownSelected = computed(
  () => shown.value.length > 0 && shown.value.every((b) => props.evidenceBlockIds.has(b.block_id)),
);
function selectAllShown() {
  const ids = new Set(props.evidenceBlockIds);
  for (const block of shown.value) ids.add(block.block_id);
  emit("setEvidence", [...ids]);
}
function clearShown() {
  const remove = new Set(shown.value.map((b) => b.block_id));
  emit(
    "setEvidence",
    [...props.evidenceBlockIds].filter((id) => !remove.has(id)),
  );
}
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
          <span v-if="externalCount" class="assign-count" data-testid="external-evidence-count">{{
            i18n.tf("pdf_corpus.evidence_external_count", { count: externalCount })
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
          <button
            type="button"
            class="btn small"
            :disabled="props.disabled"
            :title="i18n.t('pdf_corpus.browse_evidence_help')"
            @click="emit('browseExternal')"
          >
            {{ i18n.t("pdf_corpus.browse_evidence") }}
          </button>
          <button type="button" class="btn small" @click="emit('update:selectedField', '')">
            {{ i18n.t("pdf_corpus.evidence_done") }}
          </button>
        </div>
      </header>

      <div v-if="props.buildId" class="assign-suggest">
        <button
          type="button"
          class="btn small"
          :disabled="props.disabled || suggestState === 'loading'"
          @click="suggest('lexical')"
        >
          {{ i18n.t("pdf_corpus.evidence_suggest") }}
        </button>
        <button
          v-if="props.llmRequest"
          type="button"
          class="btn small"
          :disabled="props.disabled || suggestState === 'loading'"
          @click="suggest('llm')"
        >
          {{ i18n.t("pdf_corpus.evidence_suggest_llm") }}
        </button>
        <button
          type="button"
          class="btn small"
          :disabled="props.disabled || suggestState === 'loading'"
          @click="suggest('precedents')"
        >
          {{ i18n.t("pdf_corpus.evidence_suggest_precedents") }}
        </button>
        <span class="suggest-note" role="status">{{
          suggestState === "failed"
            ? i18n.t("pdf_corpus.evidence_suggest_failed")
            : semanticStatus === "fallback"
              ? `${i18n.t("pdf_corpus.evidence_suggest_semantic_fallback")} ${semanticStatusReason}`
              : suggestState === "done" && !suggestions.length
                ? i18n.t("pdf_corpus.evidence_suggest_none")
                : i18n.t("pdf_corpus.evidence_suggest_help")
        }}</span>
      </div>

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
        <button
          type="button"
          class="btn small"
          :disabled="props.disabled || !shown.length"
          @click="allShownSelected ? clearShown() : selectAllShown()"
        >
          {{
            allShownSelected
              ? i18n.tf("pdf_corpus.evidence_clear_shown", { count: shown.length })
              : i18n.tf("pdf_corpus.evidence_select_all", { count: shown.length })
          }}
        </button>
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
          <p v-if="suggestionFor(block.block_id)" class="suggested-note">
            {{ i18n.t("pdf_corpus.evidence_suggested") }}:
            {{ suggestionLabel(suggestionFor(block.block_id)!) }}
            <template v-if="suggestionFor(block.block_id)!.reason">
              — {{ suggestionFor(block.block_id)!.reason }}
            </template>
          </p>
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
.assign-suggest {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 10px;
  padding: 0 14px;
}
.suggest-note,
.suggested-note {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
.suggested-note {
  color: var(--accent);
}
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
