<script setup lang="ts">
import { isPlaceholderValue, usableListOptions } from "../domain/metadataValues";
import { computed } from "vue";
import type { CorpusRecord } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";
import { metadataConstraints } from "../domain/metadataConstraints";
import { metadataFieldSpec, metadataSuggestions } from "../domain/metadataFieldRegistry";
import type { MetadataSchema, SchemaField } from "../api/metadataSchemas";
import CorpusMetadataFieldEditor from "./CorpusMetadataFieldEditor.vue";
import CorpusFieldOwnershipBadge from "./CorpusFieldOwnershipBadge.vue";
import CorpusEnrichmentChanges from "./CorpusEnrichmentChanges.vue";

const props = defineProps<{
  record: CorpusRecord;
  regionTypes: string[];
  discourseRoles: string[];
  busy?: boolean;
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
  dirty: [dirty: boolean];
}>();
const i18n = useI18nStore();
const requiredFields = new Set(["region_type", "primary_text", "discourse_role"]);
const inheritedFieldSet = new Set([
  "work",
  "document_title",
  "short_title",
  "original_title",
  "document_author",
  "translator",
  "edition",
  "publication_year",
  "publisher",
  "publication_place",
  "isbn",
  "document_language",
  "original_language",
  "document_is_translation",
]);
// Which fields a record shows, in order: the locked core, then the fields of the build's schema, then the document-level ones
// records inherit. Without a schema (an old build), the fixed list.
const legacyOrder = [
  "region_type",
  "primary_text",
  "discourse_role",
  "region_author",
  "speaker",
  "position_holder",
  "target",
  "stance",
  "proposition_status",
  "claim_scope",
  "semantic_function",
  "is_direct_quote",
  "quoted_speaker",
  "quoted_author",
  "quoted_work",
  "quoted_position_holder",
  "quoted_addressee",
  "quoted_referent",
  "quotation_chain",
  "topics",
  "concepts",
  "persons",
  "works_referenced",
  "work",
  "document_title",
  "short_title",
  "original_title",
  "document_author",
  "translator",
  "edition",
  "publication_year",
  "publisher",
  "publication_place",
  "isbn",
  "document_language",
  "original_language",
  "document_is_translation",
];
const documentFields = legacyOrder.slice(legacyOrder.indexOf("work"));
const schemaFields = computed<Record<string, SchemaField>>(() =>
  Object.fromEntries((props.schema?.fields || []).map((field) => [field.name, field])),
);
const fieldOrder = computed<string[]>(() =>
  props.schema
    ? [
        "region_type",
        "primary_text",
        "discourse_role",
        ...props.schema.fields.map((field) => field.name),
        ...documentFields,
      ]
    : legacyOrder,
);
const fieldLabel = (field: string) => schemaFields.value[field]?.label || "";
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
    const value = props.record[field];
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
  return (props.record.metadata_field_status?.[field] || {}) as Record<string, unknown>;
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
    if (source === "speaker") {
      const deterministic = (props.record as Record<string, unknown>).deterministic_ingest;
      if (deterministic && typeof deterministic === "object") {
        const speakers = (deterministic as Record<string, unknown>).speakers;
        if (Array.isArray(speakers)) values.push(...speakers.map(String));
      }
    }
  }
  const cleaned =
    item.control === "multi-combobox"
      ? usableListOptions(values)
      : values.filter((value) => !isPlaceholderValue(value)).map((value) => value.trim());
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
  const value = props.record[field];
  if (value === true) return i18n.t("ui.yes", "Yes");
  if (value === false) return i18n.t("ui.no", "No");
  if (Array.isArray(value)) return value.join(", ") || "—";
  return value === null || value === undefined || value === "" ? "—" : String(value);
}
</script>

<template>
  <section class="metadata-review" aria-labelledby="metadata-review-title">
    <header class="metadata-head">
      <div>
        <h3 id="metadata-review-title">{{ i18n.t("pdf_corpus.metadata_tab", "Metadata") }}</h3>
        <p>
          {{
            i18n.t(
              "pdf_corpus.metadata_streamlined_help",
              "LLM suggestions are prefilled when valid. Deterministic rules resolve obvious relationships; review the remaining exceptions and save only what needs your judgment.",
            )
          }}
        </p>
      </div>
      <span
        class="review-status"
        :data-state="
          enrichmentPending ? 'processing' : attentionFields.length ? 'attention' : 'ready'
        "
        >{{
          enrichmentPending
            ? i18n.t("pdf_corpus.metadata_enrichment_pending", "LLM enrichment pending")
            : attentionFields.length
              ? i18n.tf("pdf_corpus.metadata_decisions_count", "{count} decision(s)", {
                  count: attentionFields.length,
                })
              : i18n.t("pdf_corpus.metadata_ready", "Ready")
        }}</span
      >
    </header>
    <CorpusEnrichmentChanges
      :record="record as unknown as Record<string, unknown>"
      :busy="busy"
      @resolve="(field, value) => emit('resolve', field, value)"
    />
    <p v-if="enrichmentPending" class="enrichment-note" role="status">
      {{
        i18n.t(
          "pdf_corpus.metadata_enrichment_pending_help",
          "This record is editable now, but its background LLM metadata has not settled yet. Confidence and suggestions will appear as each metadata family completes.",
        )
      }}
    </p>
    <div v-if="llmSuggestionCount" class="suggestion-toolbar">
      <div>
        <b>{{
          i18n.tf("pdf_corpus.llm_suggestions_ready", "{count} LLM suggestion(s) ready", {
            count: llmSuggestionCount,
          })
        }}</b
        ><span>{{
          i18n.t(
            "pdf_corpus.llm_suggestions_ready_help",
            "Suggestions are already filled into their controls. Confirm them individually or save all current suggestions at once.",
          )
        }}</span>
      </div>
      <button
        type="button"
        class="btn primary"
        :disabled="busy"
        @click="emit('resolveMany', llmSuggestions)"
      >
        {{ i18n.t("pdf_corpus.accept_all_suggestions", "Save all suggestions") }}
      </button>
    </div>

    <div
      v-if="attentionFields.length"
      class="metadata-grid"
      role="list"
      :aria-label="i18n.t('pdf_corpus.metadata_needs_review', 'Metadata needing review')"
    >
      <div v-for="field in attentionFields" :key="field" class="metadata-list-item" role="listitem">
        <CorpusMetadataFieldEditor
          :label="fieldLabel(field)"
          :field="field"
          :value="record[field]"
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
          :open="true"
          @save="(value) => emit('resolve', field, value)"
          @no-value="emit('noValue', field)"
          @source="emit('source', field)"
          @dirty="(value) => emit('dirty', value)"
        />
      </div>
    </div>
    <details v-if="settledFields.length" class="settled-metadata">
      <summary>
        {{ i18n.t("pdf_corpus.populated_metadata", "Populated metadata") }}
        <span>{{ settledFields.length }}</span>
      </summary>
      <div class="metadata-grid" role="list">
        <div v-for="field in settledFields" :key="field" class="metadata-list-item" role="listitem">
          <CorpusMetadataFieldEditor
            :label="fieldLabel(field)"
            :field="field"
            :value="record[field]"
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
            @dirty="(value) => emit('dirty', value)"
          />
        </div>
      </div>
    </details>

    <details v-if="addableFields.length" class="settled-metadata add-metadata">
      <summary>
        {{ i18n.t("pdf_corpus.add_metadata_section", "Add more details") }}
        <span>{{ addableFields.length }}</span>
      </summary>
      <p class="add-metadata-help">
        {{
          i18n.t(
            "pdf_corpus.add_metadata_help",
            "These fields are empty on this record. Fill in any that apply, such as a quoted speaker.",
          )
        }}
      </p>
      <div class="metadata-grid" role="list">
        <div v-for="field in addableFields" :key="field" class="metadata-list-item" role="listitem">
          <CorpusMetadataFieldEditor
            :label="fieldLabel(field)"
            :field="field"
            :value="record[field]"
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
            @dirty="(value) => emit('dirty', value)"
          />
        </div>
      </div>
    </details>

    <details v-if="inheritedFields.length" class="inherited-metadata">
      <summary>
        {{ i18n.t("pdf_corpus.inherited_metadata_section", "Inherited document metadata") }}
        <span>{{ inheritedFields.length }}</span>
      </summary>
      <p>
        {{
          i18n.t(
            "pdf_corpus.inherited_metadata_help",
            "These values come from the document manifest. Override only when this record legitimately differs from the document default.",
          )
        }}
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
            {{ i18n.t("pdf_corpus.view_evidence", "Evidence") }}
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
