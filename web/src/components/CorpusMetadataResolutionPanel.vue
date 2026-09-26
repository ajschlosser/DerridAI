<script setup lang="ts">
import {
  metadataValueText,
  unwrapMetadataValue,
  usableListOptions,
  usableOptions,
} from "../domain/metadataValues";
import { computed, ref } from "vue";
import type { CorpusRecord } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";
import { metadataConstraints } from "../domain/metadataConstraints";
import { metadataFieldSpec, metadataSuggestions } from "../domain/metadataFieldRegistry";
import { assertionConflict, currentFieldAssertions } from "../domain/fieldAssertions";
import type { MetadataSchema, SchemaField } from "../api/metadataSchemas";
import { reviewableMetadataFieldNames } from "../features/corpus-builder/domain/recordMetadata";
import CorpusMetadataFieldEditor from "./CorpusMetadataFieldEditor.vue";
import CorpusFieldOwnershipBadge from "./CorpusFieldOwnershipBadge.vue";
import CorpusEnrichmentChanges from "./CorpusEnrichmentChanges.vue";
import CorpusFieldPolicyBadges from "./CorpusFieldPolicyBadges.vue";

const props = defineProps<{
  record: CorpusRecord;
  regionTypes: string[];
  discourseRoles: string[];
  busy?: boolean;
  batchSaving?: boolean;
  savingField?: string;
  savedField?: string;
  confidenceCalibration?: Record<string, Record<string, Record<string, number>>>;
  knownValues?: Record<string, string[]>;
  schema?: MetadataSchema | null;
}>();
const emit = defineEmits<{
  resolve: [field: string, value: unknown];
  noValue: [field: string];
  resolveMany: [changes: Record<string, unknown>];
  source: [field: string];
  resolveWithEvidence: [field: string, value: unknown, text: string];
  dirty: [dirty: boolean];
}>();
const i18n = useI18nStore();
const populatedOpen = ref(true);
const requiredFields = new Set(["region_type", "primary_text", "discourse_role"]);
const inheritedFieldSet = new Set([
  "work",
  "document_title",
  "short_title",
  "original_title",
  "canonical_work_id",
  "document_author",
  "translator",
  "edition",
  "year",
  "publication_year",
  "publisher",
  "publication_place",
  "isbn",
  "document_language",
  "original_language",
  "language",
  "document_is_translation",
]);
// Which fields a record shows, in order: the locked core, then the fields of the build's schema, then the document-level ones
// records inherit. Without a schema (an old build), the fixed list.
const schemaFields = computed<Record<string, SchemaField>>(() =>
  Object.fromEntries((props.schema?.fields || []).map((field) => [field.name, field])),
);
const canonicalAssertions = computed(() =>
  currentFieldAssertions(props.record as unknown as Record<string, unknown>),
);
const fieldOrder = computed<string[]>(() =>
  props.schema
    ? reviewableMetadataFieldNames(props.record as unknown as Record<string, unknown>, props.schema)
    : reviewableMetadataFieldNames(props.record as unknown as Record<string, unknown>, null),
);
const fieldLabel = (field: string) => schemaFields.value[field]?.label || "";
const assertionByField = computed(() =>
  Object.fromEntries(canonicalAssertions.value.map((item) => [item.field_name, item])),
);
function canonicalStatus(field: string): Record<string, unknown> | null {
  const assertion = assertionByField.value[field];
  if (!assertion) return null;
  let status = "inherited";
  if (assertion.value_status === "confirmed_absent") status = "confirmed_absent";
  else if (assertion.value_status === "invalid") status = "invalid";
  else if (assertion.value_status === "unresolved") status = "unresolved";
  else if (assertion.authority_status === "human_override") status = "human_override";
  else if (assertion.authority_status === "human_confirmed") status = "human_confirmed";
  else if (assertion.derivation_method === "model") status = "model_inferred";
  else if (assertion.derivation_method === "deterministic") status = "deterministic";
  else if (assertion.derivation_method === "inherited") status = "inherited";
  const history = assertionConflict(
    props.record as unknown as Record<string, unknown>,
    assertion.field_id || field,
  );
  return {
    status,
    method:
      assertion.method ||
      (assertion.derivation_method === "model" ? "llm" : assertion.derivation_method || ""),
    derivation_method: assertion.derivation_method,
    confidence: assertion.confidence,
    assertion_id: assertion.assertion_id,
    field_id: assertion.field_id,
    authority_status: assertion.authority_status,
    evaluation_status: assertion.evaluation_status,
    value_status: assertion.value_status,
    actor: assertion.actor,
    model: assertion.model,
    reason: assertion.reason,
    evidence: assertion.evidence,
    created_at: assertion.created_at,
    record_revision: assertion.record_revision,
    supersedes_assertion_id: assertion.supersedes_assertion_id,
    disputed: history?.disputed || false,
    conflicting_assertions: history?.alternatives || [],
  };
}
function fieldValue(field: string) {
  const assertion = assertionByField.value[field];
  if (!assertion) return unwrapMetadataValue(props.record[field]);
  if (assertion.value_status === "confirmed_absent") return null;
  if (assertion.value_status === "present") return unwrapMetadataValue(assertion.value);
  return unwrapMetadataValue(props.record[field]);
}
const unresolved = computed(
  () =>
    new Set([
      ...(props.record.metadata_incomplete_fields || []),
      ...(props.record.metadata_review_fields || []),
    ]),
);
const fields = computed(() =>
  fieldOrder.value.filter(
    (field) =>
      props.record.metadata_field_status?.[field] ||
      props.record[field] !== undefined ||
      Boolean(assertionByField.value[field]) ||
      unresolved.value.has(field),
  ),
);
const activeFields = computed(() => fields.value.filter((field) => !inheritedFieldSet.has(field)));
const attentionFields = computed(() =>
  activeFields.value.filter(
    (field) =>
      unresolved.value.has(field) ||
      ["unresolved", "invalid"].includes(String(status(field).status || "")),
  ),
);
const activeField = computed(() => attentionFields.value[0] || activeFields.value[0] || "");
const settledFields = computed(() =>
  activeFields.value.filter((field) => !attentionFields.value.includes(field)),
);
// Optional details a record simply does not have yet (a quoted speaker, topics…) have no value and no status, so they
// were never listed, and there was nowhere to add one. They are offered here, empty, for the person to fill in.
const addableFields = computed(() =>
  fieldOrder.value.filter(
    (field) => !inheritedFieldSet.has(field) && !fields.value.includes(field),
  ),
);
const inheritedFields = computed(() =>
  fields.value.filter((field) => inheritedFieldSet.has(field)),
);
const enrichmentState = computed(() => String(props.record.metadata_enrichment_state || ""));
const enrichmentPending = computed(() => ["queued", "running"].includes(enrichmentState.value));
const constraints = computed(() =>
  metadataConstraints({}, props.record as Record<string, unknown>),
);
const llmSuggestions = computed(() => {
  const out: Record<string, unknown> = {};
  for (const field of activeFields.value) {
    const info = status(field);
    const value = fieldValue(field);
    if (
      String(info.method || "").includes("llm") &&
      unresolved.value.has(field) &&
      value !== null &&
      value !== undefined &&
      value !== ""
    )
      out[field] = value;
  }
  return out;
});
const llmSuggestionCount = computed(() => Object.keys(llmSuggestions.value).length);
function status(field: string) {
  const legacy = (props.record.metadata_field_status?.[field] || {}) as Record<string, unknown>;
  const canonical = canonicalStatus(field);
  return canonical ? { ...legacy, ...canonical } : legacy;
}
function spec(field: string) {
  return metadataFieldSpec(
    field,
    props.regionTypes,
    props.discourseRoles,
    schemaFields.value[field],
  );
}
function options(field: string) {
  const item = spec(field);
  if (item.allowedValues) return item.allowedValues;
  const sources = item.suggestionFields || [field];
  const values: string[] = [];
  for (const source of sources) {
    values.push(...(props.knownValues?.[source] || []));
    values.push(...metadataSuggestions(props.record as Record<string, unknown>, [source]));
    const sourceStatus = props.record.metadata_field_status?.[source] as
      | Record<string, unknown>
      | undefined;
    for (const candidate of [sourceStatus?.proposed_value, sourceStatus?.llm_value]) {
      if (Array.isArray(candidate)) values.push(...candidate.map(String));
      else if (typeof candidate === "string") values.push(candidate);
    }
    const nlpTags = schemaFields.value[field]?.ner_tags || [];
    if (
      nlpTags.length &&
      /\b(?:PERSON|PER|ORG|GPE|LOC|FAC|WORK_OF_ART|EVENT|PRODUCT)\b/i.test(nlpTags.join(" "))
    ) {
      // Keep this deterministic and dependency-free: capitalized spans are useful
      // reviewer candidates even when an optional NLP provider is unavailable.
      const text = String((props.record as Record<string, unknown>).text || "");
      for (const match of text.matchAll(
        /\b[A-ZÀ-ÖØ-Þ][\p{L}'-]*(?:\s+[A-ZÀ-ÖØ-Þ][\p{L}'-]*){0,4}\b/gu,
      )) {
        const candidate = match[0].trim();
        if (candidate.length > 1) values.push(candidate);
      }
    }
    if (source === "speaker") {
      const deterministic = (props.record as Record<string, unknown>).deterministic_ingest;
      if (deterministic && typeof deterministic === "object") {
        const speakers = (deterministic as Record<string, unknown>).speakers;
        if (Array.isArray(speakers)) values.push(...speakers.map(String));
      }
    }
  }
  const cleaned =
    item.control === "multi-combobox" ? usableListOptions(values) : usableOptions(values);
  return [...new Set(cleaned)].sort((a, b) => a.localeCompare(b));
}
function fieldBusy(field: string) {
  return Boolean(props.busy) || Boolean(props.savingField && props.savingField !== field);
}
function constraint(field: string) {
  const item = constraints.value.find((row) => row.field === field);
  return item ? { value: item.value, reason: i18n.t(item.reasonKey, item.reasonKey) } : null;
}

function calibrated(field: string) {
  const info = status(field);
  const confidence = typeof info.confidence === "number" ? Number(info.confidence) : null;
  if (confidence === null) return null;
  const band = confidence >= 0.85 ? "high" : confidence >= 0.65 ? "medium" : "low";
  const row = props.confidenceCalibration?.[field]?.[band];
  return row && Number(row.reviewed || 0) > 0
    ? { reviewed: Number(row.reviewed || 0), acceptanceRate: Number(row.acceptance_rate || 0) }
    : null;
}
function displayValue(field: string) {
  const value = unwrapMetadataValue(fieldValue(field));
  if (value === true) return i18n.t("ui.yes");
  if (value === false) return i18n.t("ui.no");
  return metadataValueText(value) || "—";
}
</script>

<template>
  <section class="metadata-review" aria-labelledby="metadata-review-title">
    <header class="metadata-head">
      <div>
        <h3 id="metadata-review-title">{{ i18n.t("pdf_corpus.metadata_tab") }}</h3>
        <p>
          {{ i18n.t("pdf_corpus.metadata_streamlined_help") }}
        </p>
      </div>
      <p v-if="activeField" class="active-field" role="status">
        {{ i18n.t("pdf_corpus.active_metadata_field", "Active field") }}:
        <b>{{ fieldLabel(activeField) || activeField.replaceAll("_", " ") }}</b>
      </p>
      <span
        class="review-status"
        :data-state="
          enrichmentPending ? 'processing' : attentionFields.length ? 'attention' : 'ready'
        "
        >{{
          enrichmentPending
            ? i18n.t("pdf_corpus.metadata_enrichment_pending")
            : attentionFields.length
              ? i18n.tf("pdf_corpus.metadata_decisions_count", {
                  count: attentionFields.length,
                })
              : i18n.t("pdf_corpus.metadata_ready")
        }}</span
      >
    </header>
    <CorpusEnrichmentChanges
      :record="record as unknown as Record<string, unknown>"
      :busy="busy"
      @resolve="(field, value) => emit('resolve', field, value)"
    />
    <p v-if="enrichmentPending" class="enrichment-note" role="status">
      {{ i18n.t("pdf_corpus.metadata_enrichment_pending_help") }}
    </p>
    <div v-if="llmSuggestionCount" class="suggestion-toolbar">
      <div>
        <b>{{
          i18n.tf("pdf_corpus.llm_suggestions_ready", {
            count: llmSuggestionCount,
          })
        }}</b
        ><span>{{ i18n.t("pdf_corpus.llm_suggestions_ready_help") }}</span>
      </div>
      <button
        type="button"
        class="btn primary"
        :disabled="busy || batchSaving"
        @click="emit('resolveMany', llmSuggestions)"
      >
        {{ i18n.t("pdf_corpus.accept_all_suggestions") }}
      </button>
    </div>

    <div
      v-if="attentionFields.length"
      class="metadata-grid"
      role="list"
      :aria-label="i18n.t('pdf_corpus.metadata_needs_review')"
    >
      <div v-for="field in attentionFields" :key="field" class="metadata-list-item" role="listitem">
        <CorpusFieldPolicyBadges
          :field="field"
          :schema-field="schemaFields[field]"
          :core-required="requiredFields.has(field)"
        />
        <CorpusMetadataFieldEditor
          :label="fieldLabel(field)"
          :field="field"
          :value="fieldValue(field)"
          :status="status(field)"
          :revealed="(record as any).blind_reveals?.[field]"
          :recheck="(record as any).recheck_results?.[field]"
          :options="options(field)"
          :control="spec(field).control"
          :allow-custom="Boolean(spec(field).allowCustom)"
          :required="requiredFields.has(field)"
          :busy="fieldBusy(field)"
          :saving="savingField === field"
          :saved="savedField === field"
          :constraint="constraint(field)"
          :calibrated-acceptance="calibrated(field)"
          :open="field === activeField"
          @save="(value) => emit('resolve', field, value)"
          @no-value="emit('noValue', field)"
          @source="emit('source', field)"
          @save-with-selection-evidence="
            (value, text) => emit('resolveWithEvidence', field, value, text)
          "
          @dirty="(value) => emit('dirty', value)"
        />
        <button
          v-if="String(status(field).method || '').includes('llm') && status(field).autofilled"
          type="button"
          class="btn small primary quick-confirm"
          :disabled="fieldBusy(field)"
          @click="emit('resolve', field, fieldValue(field))"
        >
          {{ i18n.t("pdf_corpus.confirm_llm_value", "Confirm LLM value") }}
        </button>
      </div>
    </div>
    <details
      v-if="settledFields.length"
      class="settled-metadata"
      :open="populatedOpen"
      @toggle="populatedOpen = ($event.currentTarget as HTMLDetailsElement).open"
    >
      <summary>
        {{ i18n.t("pdf_corpus.populated_metadata") }}
        <span>{{ settledFields.length }}</span>
      </summary>
      <div class="metadata-grid" role="list">
        <div v-for="field in settledFields" :key="field" class="metadata-list-item" role="listitem">
          <CorpusFieldPolicyBadges
            :field="field"
            :schema-field="schemaFields[field]"
            :core-required="requiredFields.has(field)"
          />
          <CorpusMetadataFieldEditor
            :label="fieldLabel(field)"
            :field="field"
            :value="fieldValue(field)"
            :status="status(field)"
            :revealed="(record as any).blind_reveals?.[field]"
            :recheck="(record as any).recheck_results?.[field]"
            :options="options(field)"
            :control="spec(field).control"
            :allow-custom="Boolean(spec(field).allowCustom)"
            :required="requiredFields.has(field)"
            :busy="fieldBusy(field)"
            :saving="savingField === field"
            :saved="savedField === field"
            :constraint="constraint(field)"
            :calibrated-acceptance="calibrated(field)"
            @save="(value) => emit('resolve', field, value)"
            @no-value="emit('noValue', field)"
            @source="emit('source', field)"
            @save-with-selection-evidence="
              (value, text) => emit('resolveWithEvidence', field, value, text)
            "
            @dirty="(value) => emit('dirty', value)"
          />
        </div>
      </div>
    </details>

    <details v-if="addableFields.length" class="settled-metadata add-metadata">
      <summary>
        {{ i18n.t("pdf_corpus.add_metadata_section") }}
        <span>{{ addableFields.length }}</span>
      </summary>
      <p class="add-metadata-help">
        {{ i18n.t("pdf_corpus.add_metadata_help") }}
      </p>
      <div class="metadata-grid" role="list">
        <div v-for="field in addableFields" :key="field" class="metadata-list-item" role="listitem">
          <CorpusFieldPolicyBadges
            :field="field"
            :schema-field="schemaFields[field]"
            :core-required="requiredFields.has(field)"
          />
          <CorpusMetadataFieldEditor
            :label="fieldLabel(field)"
            :field="field"
            :value="fieldValue(field)"
            :status="status(field)"
            :options="options(field)"
            :control="spec(field).control"
            :allow-custom="Boolean(spec(field).allowCustom)"
            :required="requiredFields.has(field)"
            :busy="fieldBusy(field)"
            :saving="savingField === field"
            :saved="savedField === field"
            @save="(value) => emit('resolve', field, value)"
            @no-value="emit('noValue', field)"
            @source="emit('source', field)"
            @save-with-selection-evidence="
              (value, text) => emit('resolveWithEvidence', field, value, text)
            "
            @dirty="(value) => emit('dirty', value)"
          />
        </div>
      </div>
    </details>

    <details v-if="inheritedFields.length" class="inherited-metadata">
      <summary>
        {{ i18n.t("pdf_corpus.inherited_metadata_section") }}
        <span>{{ inheritedFields.length }}</span>
      </summary>
      <p>
        {{ i18n.t("pdf_corpus.inherited_metadata_help") }}
      </p>
      <div class="inherited-grid" role="list">
        <article
          v-for="field in inheritedFields"
          :key="field"
          class="inherited-row"
          role="listitem"
        >
          <div>
            <b>{{ i18n.t(`record.${field}`, field.replaceAll("_", " ")) }}</b
            ><CorpusFieldOwnershipBadge
              :status="String(status(field).status || 'inherited')"
              :method="String(status(field).method || 'manifest')"
            />
          </div>
          <span>{{ displayValue(field) }}</span
          ><button type="button" class="link-button" @click="emit('source', field)">
            {{ i18n.t("pdf_corpus.view_evidence") }}
          </button>
        </article>
      </div>
    </details>
  </section>
</template>

<style scoped>
.metadata-review {
  display: grid;
  gap: 14px;
}
.metadata-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.metadata-head h3 {
  margin: 0;
  font-size: 1.125rem;
}
.metadata-head p {
  margin: 5px 0 0;
  max-width: 72ch;
  color: var(--muted);
  font-size: 0.875rem;
  line-height: 1.5;
}
.review-status {
  padding: 6px 9px;
  border-radius: 999px;
  background: var(--soft);
  font-size: 0.8125rem;
  font-weight: 800;
  white-space: nowrap;
}
.review-status[data-state="attention"] {
  border: 1px solid var(--warning, #a16207);
}
.active-field {
  margin: -4px 0 0;
  padding: 9px 12px;
  border-inline-start: 3px solid var(--accent);
  background: var(--soft);
  color: var(--muted);
  font-size: 0.875rem;
}
.active-field b {
  color: var(--text);
}
.enrichment-note {
  margin: 0;
  padding: 10px 12px;
  border-radius: 9px;
  background: var(--soft);
  font-size: 0.875rem;
  line-height: 1.5;
}
.suggestion-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--soft);
}
.suggestion-toolbar > div {
  display: grid;
  gap: 2px;
}
.suggestion-toolbar b {
  font-size: 0.875rem;
}
.suggestion-toolbar span {
  font-size: 0.8125rem;
  color: var(--muted);
  line-height: 1.4;
}
.metadata-grid {
  min-width: 0;
  display: grid;
  gap: 10px;
}
.metadata-list-item {
  min-width: 0;
}
.settled-metadata {
  border-top: 1px solid var(--line);
  padding-top: 8px;
}
.settled-metadata > summary {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  font-weight: 800;
  cursor: pointer;
}
.settled-metadata > summary span {
  font-size: 0.8125rem;
  color: var(--muted);
}
.settled-metadata[open] > .metadata-grid {
  padding-top: 8px;
}
.inherited-metadata {
  margin-top: 8px;
  border-top: 1px solid var(--line);
  padding-top: 12px;
}
.inherited-metadata summary {
  cursor: pointer;
  min-height: 40px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 800;
}
.inherited-metadata summary span {
  font-size: 0.8125rem;
  color: var(--muted);
}
.inherited-metadata > p {
  color: var(--muted);
  font-size: 0.875rem;
  line-height: 1.5;
}
.inherited-grid {
  display: grid;
  gap: 7px;
}
.inherited-row {
  display: grid;
  grid-template-columns: minmax(180px, 0.7fr) 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 10px 0;
  border-top: 1px solid var(--line);
}
.inherited-row > div {
  display: flex;
  gap: 7px;
  align-items: center;
  flex-wrap: wrap;
}
.link-button {
  border: 0;
  background: none;
  color: var(--accent-fg);
  font: inherit;
  font-weight: 700;
  min-height: 36px;
  cursor: pointer;
}
:is(button, summary):focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
@media (max-width: 720px) {
  .metadata-head,
  .suggestion-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .inherited-row {
    grid-template-columns: 1fr;
  }
  .review-status {
    white-space: normal;
  }
}
@media (max-height: 860px) {
  .metadata-head p {
    display: none;
  }
  .metadata-head h3 {
    font-size: 1rem;
  }
  .metadata-review {
    gap: 10px;
  }
}
</style>
