<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import {
  metadataValueText,
  unwrapMetadataValue,
  usableListOptions,
  usableOptions,
  withoutTransportItems,
} from "../domain/metadataValues";
import { computed, nextTick, ref, watch } from "vue";
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
import UiTooltip from "./ui/UiTooltip.vue";

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
  /** Fields the server requires before it will accept the record; they are listed first and marked. */
  blockingFields?: string[];
}>();
const emit = defineEmits<{
  resolve: [field: string, value: unknown];
  noValue: [field: string];
  resolveMany: [changes: Record<string, unknown>];
  source: [field: string];
  resolveWithEvidence: [field: string, value: unknown, text: string];
  dirty: [dirty: boolean];
  /** Every pending field has been decided from this panel: the record is ready for its decision. */
  complete: [];
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
  else if (
    assertion.derivation_method === "model" ||
    String(assertion.derivation_method || "").startsWith("derridai:")
  )
    status = "model_inferred";
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
// Values stored before the API dropped structured-output residue from lists (an evidence ID, a confidence score) are
// read without it, so neither the editor nor "Accept all suggestions" can save it back.
function fieldValue(field: string) {
  const assertion = assertionByField.value[field];
  if (!assertion) return withoutTransportItems(unwrapMetadataValue(props.record[field]));
  if (assertion.value_status === "confirmed_absent") return null;
  if (assertion.value_status === "present")
    return withoutTransportItems(unwrapMetadataValue(assertion.value));
  return withoutTransportItems(unwrapMetadataValue(props.record[field]));
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
const blocking = computed(() => new Set(props.blockingFields || []));
const pendingSet = computed(() => new Set(attentionFields.value));
// The fields to decide keep the order they had when the record opened. A field that is decided stays where it was, folded
// to one line, instead of jumping to another list; the reviewer's place, and everything below it, stays put.
const sessionFields = ref<string[]>([]);
let sessionRecordId = "";
watch(
  [() => props.record.record_id, attentionFields],
  ([recordId, fields]) => {
    if (recordId !== sessionRecordId) {
      sessionRecordId = recordId;
      sessionFields.value = [
        ...fields.filter((field) => blocking.value.has(field)),
        ...fields.filter((field) => !blocking.value.has(field)),
      ];
      return;
    }
    const added = fields.filter((field) => !sessionFields.value.includes(field));
    if (added.length) sessionFields.value = [...sessionFields.value, ...added];
  },
  { immediate: true },
);
const decisionFields = computed(() =>
  sessionFields.value.filter((field) => activeFields.value.includes(field)),
);
const settledFields = computed(() =>
  activeFields.value.filter((field) => !decisionFields.value.includes(field)),
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
type MemoryHint = { value: unknown; similarity: number; support: number; absence?: boolean };
/** Less certain values earlier reviews attached to matching source spans (never pre-filled). */
function memoryHints(field: string): MemoryHint[] {
  const all = (props.record as unknown as { memory_hints?: Record<string, MemoryHint[]> })
    .memory_hints;
  return (all?.[field] || []).filter((hint) => !hint.absence);
}
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
// After a decision, focus moves to the next field still to decide (its Confirm button, so Enter confirms it), and once
// none is left the parent is told, so it can offer the record decision. It waits for the save to finish, since the
// other fields' buttons are disabled while one field is being written.
const root = ref<HTMLElement | null>(null);
const advanceFrom = ref<string | null>(null);
function decided(field: string) {
  advanceFrom.value = field;
  void nextTick(tryAdvance);
}
function tryAdvance() {
  const from = advanceFrom.value;
  if (from === null || props.busy || props.savingField || props.batchSaving) return;
  advanceFrom.value = null;
  const order = decisionFields.value;
  const start = Math.max(0, order.indexOf(from));
  const next = [...order.slice(start + 1), ...order.slice(0, start)].find(
    (field) => field !== from && pendingSet.value.has(field),
  );
  if (!next) {
    if (!attentionFields.value.some((field) => field !== from)) emit("complete");
    return;
  }
  focusField(next);
}
function focusField(field: string) {
  const card = [...(root.value?.querySelectorAll<HTMLElement>("[data-field]") || [])].find(
    (item) => item.dataset.field === field,
  );
  if (!card) return;
  const target =
    card.querySelector<HTMLElement>("[data-primary-action]:not([disabled])") ||
    card.querySelector<HTMLElement>("select:not([disabled]), input:not([disabled])");
  card.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  target?.focus({ preventScroll: true });
}
watch(
  () => [props.busy, props.savingField, props.batchSaving, attentionFields.value.length],
  () => void nextTick(tryAdvance),
);
function displayValue(field: string) {
  const value = unwrapMetadataValue(fieldValue(field));
  if (value === true) return i18n.t("ui.yes");
  if (value === false) return i18n.t("ui.no");
  return metadataValueText(value) || "—";
}
</script>

<template>
  <section ref="root" class="metadata-review" aria-labelledby="metadata-review-title">
    <header class="metadata-head">
      <h3 id="metadata-review-title">{{ i18n.t("pdf_corpus.metadata_tab") }}</h3>
      <UiTooltip
        :text="i18n.t('pdf_corpus.metadata_streamlined_help')"
        :label="i18n.t('pdf_corpus.metadata_review_help_label')"
        placement="bottom"
      />
      <span
        class="review-status"
        role="status"
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
      <b>{{
        i18n.tf("pdf_corpus.llm_suggestions_ready", {
          count: llmSuggestionCount,
        })
      }}</b>
      <button
        type="button"
        class="btn small primary"
        :title="i18n.t('pdf_corpus.llm_suggestions_ready_help')"
        :disabled="busy || batchSaving"
        @click="
          emit('resolveMany', llmSuggestions);
          decided('');
        "
      >
        {{ i18n.t("pdf_corpus.accept_all_suggestions") }}
      </button>
    </div>

    <div
      v-if="decisionFields.length"
      class="metadata-grid decision-list"
      role="list"
      :aria-label="i18n.t('pdf_corpus.metadata_needs_review')"
    >
      <div
        v-for="field in decisionFields"
        :key="field"
        class="metadata-list-item"
        role="listitem"
        :data-decided="pendingSet.has(field) ? undefined : 'true'"
      >
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
          :required-to-accept="blocking.has(field)"
          :busy="fieldBusy(field)"
          :saving="savingField === field"
          :saved="savedField === field"
          :constraint="constraint(field)"
          :calibrated-acceptance="calibrated(field)"
          :open="pendingSet.has(field)"
          :hints="memoryHints(field)"
          @save="
            (value) => {
              emit('resolve', field, value);
              decided(field);
            }
          "
          @no-value="
            emit('noValue', field);
            decided(field);
          "
          @source="emit('source', field)"
          @save-with-selection-evidence="
            (value, text) => {
              emit('resolveWithEvidence', field, value, text);
              decided(field);
            }
          "
          @dirty="(value) => emit('dirty', value)"
        >
          <template #policy>
            <CorpusFieldPolicyBadges
              :field="field"
              :schema-field="schemaFields[field]"
              :core-required="requiredFields.has(field)"
            />
          </template>
        </CorpusMetadataFieldEditor>
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
      <div class="metadata-grid field-rows" role="list">
        <div v-for="field in settledFields" :key="field" class="metadata-list-item" role="listitem">
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
          >
            <template #policy>
              <CorpusFieldPolicyBadges
                :field="field"
                :schema-field="schemaFields[field]"
                :core-required="requiredFields.has(field)"
              />
            </template>
          </CorpusMetadataFieldEditor>
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
      <div class="metadata-grid field-rows" role="list">
        <div v-for="field in addableFields" :key="field" class="metadata-list-item" role="listitem">
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
          >
            <template #policy>
              <CorpusFieldPolicyBadges
                :field="field"
                :schema-field="schemaFields[field]"
                :core-required="requiredFields.has(field)"
              />
            </template>
          </CorpusMetadataFieldEditor>
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
          <b>{{ i18n.t(`record.${field}`, field.replaceAll("_", " ")) }}</b>
          <span>{{ displayValue(field) }}</span>
          <span class="inherited-aside"
            ><CorpusFieldOwnershipBadge
              :status="String(status(field).status || 'inherited')"
              :method="String(status(field).method || 'manifest')"
            /><button type="button" class="link-button" @click="emit('source', field)">
              {{ i18n.t("pdf_corpus.view_evidence") }}
            </button></span
          >
        </article>
      </div>
    </details>
  </section>
</template>

<style scoped>
.metadata-review {
  container: metadata-review / inline-size;
  display: grid;
  gap: 12px;
}
.metadata-head {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
}
.metadata-head h3 {
  margin: 0;
  font-size: var(--fs-md);
}
.review-status {
  margin-inline-start: auto;
  padding: 3px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--surface-inset, var(--soft));
  font-size: var(--fs-sm);
  font-weight: 700;
  white-space: nowrap;
}
.review-status[data-state="attention"] {
  border-color: var(--tone-warn-edge);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.review-status[data-state="ready"] {
  border-color: var(--tone-ok-edge);
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
}
.enrichment-note {
  margin: 0;
  padding: 8px 10px;
  border-radius: var(--radius-control);
  background: var(--surface-inset, var(--soft));
  font-size: var(--fs-sm);
  line-height: 1.5;
}
.suggestion-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--tone-info-edge);
  border-radius: var(--radius-control);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
}
.suggestion-toolbar > b {
  font-size: var(--fs-sm);
}
.metadata-grid {
  min-width: 0;
  display: grid;
  gap: 8px;
}
.metadata-list-item {
  min-width: 0;
}
/* A field decided during this visit stays in place as a row, separated from the open cards around it. */
.decision-list > [data-decided="true"] {
  padding-inline: 12px;
  border-radius: var(--radius-control);
  background: var(--surface-inset, var(--soft));
}
.field-rows {
  gap: 0;
}
.field-rows > .metadata-list-item + .metadata-list-item {
  border-top: 1px solid var(--border-subtle);
}
.settled-metadata,
.inherited-metadata {
  border-top: 1px solid var(--border-subtle);
  padding-top: 4px;
}
.settled-metadata > summary,
.inherited-metadata > summary {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  font-size: var(--fs-sm);
  font-weight: 700;
  cursor: pointer;
}
.settled-metadata > summary span,
.inherited-metadata > summary span {
  color: var(--text-tertiary);
  font-weight: 600;
}
.add-metadata-help,
.inherited-metadata > p {
  margin: 0 0 6px;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  line-height: 1.5;
}
.inherited-grid {
  display: grid;
}
.inherited-row {
  display: grid;
  grid-template-columns: minmax(7rem, 0.8fr) minmax(0, 1.4fr) auto;
  gap: 4px 12px;
  align-items: center;
  min-height: 40px;
  padding: 4px 0;
  border-top: 1px solid var(--border-subtle);
}
.inherited-row > b {
  color: var(--text-secondary, var(--muted));
  font-size: var(--fs-sm);
}
.inherited-row > span {
  min-width: 0;
  font-size: var(--fs-base);
  overflow-wrap: anywhere;
}
.inherited-aside {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
}
.link-button {
  border: 0;
  background: none;
  color: var(--accent-fg);
  font: inherit;
  font-size: var(--fs-sm);
  font-weight: 700;
  min-height: 32px;
  cursor: pointer;
}
:is(button, summary):focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
@container metadata-review (max-width: 32rem) {
  .suggestion-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .inherited-row {
    grid-template-columns: 1fr;
  }
}
</style>
