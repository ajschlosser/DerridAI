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
import type { PipelineRunTrace } from "../types/pipelines";
import { useI18nStore } from "../stores/i18n";
import { metadataConstraints } from "../domain/metadataConstraints";
import {
  metadataFieldSpec,
  metadataSuggestions,
  PROPOSITION_STATUS_VALUES,
  STANCE_VALUES,
} from "../domain/metadataFieldRegistry";
import { assertionConflict, currentFieldAssertions } from "../domain/fieldAssertions";
import type { MetadataSchema, SchemaField } from "../api/metadataSchemas";
import { corpusBuilderApi, type MetadataPrecedents } from "../api/corpus";
import { reviewableMetadataFieldNames } from "../features/corpus-builder/domain/recordMetadata";
import CorpusMetadataFieldEditor from "./CorpusMetadataFieldEditor.vue";
import CorpusFieldPrecedents from "./CorpusFieldPrecedents.vue";
import CorpusFieldOwnershipBadge from "./CorpusFieldOwnershipBadge.vue";
import CorpusEnrichmentChanges from "./CorpusEnrichmentChanges.vue";
import CorpusFieldPolicyBadges from "./CorpusFieldPolicyBadges.vue";
import UiTooltip from "./ui/UiTooltip.vue";
import PipelineRunTracePanel from "./pipelines/PipelineRunTracePanel.vue";

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
  /** Enables read-only metadata-precedent cross-references. */
  buildId?: string;
}>();
const emit = defineEmits<{
  resolve: [field: string, value: unknown];
  noValue: [field: string];
  resolveMany: [changes: Record<string, unknown>];
  source: [field: string];
  resolveWithEvidence: [field: string, value: unknown, text: string];
  resolveWithHumanSource: [field: string, value: unknown, note: string];
  browseEvidence: [field: string, value: unknown];
  dirty: [dirty: boolean];
  /** Every pending field has been decided from this panel: the record is ready for its decision. */
  complete: [];
}>();
const i18n = useI18nStore();
const dirtyFields = new Set<string>();
function fieldDirty(field: string, dirty: boolean) {
  if (dirty) dirtyFields.add(field);
  else dirtyFields.delete(field);
  emit("dirty", dirtyFields.size > 0);
}
watch(
  () => props.record.record_id,
  () => {
    dirtyFields.clear();
    emit("dirty", false);
  },
);
const MACHINE_VOCABULARY_LABELS = new Set(
  [
    "ADJ",
    "ADP",
    "ADV",
    "AUX",
    "CCONJ",
    "DET",
    "INTJ",
    "NOUN",
    "NUM",
    "PART",
    "PRON",
    "PROPN",
    "PUNCT",
    "SCONJ",
    "SYM",
    "VERB",
    "X",
    "CARDINAL",
    "DATE",
    "EVENT",
    "FAC",
    "GPE",
    "LANGUAGE",
    "LAW",
    "LOC",
    "MONEY",
    "NORP",
    "ORDINAL",
    "ORG",
    "PERCENT",
    "PERSON",
    "PER",
    "PRODUCT",
    "QUANTITY",
    "TIME",
    "WORK_OF_ART",
  ].map((value) => value.toLocaleLowerCase()),
);

const nlpProvenance = computed(() => {
  const data = (props.record as unknown as { nlp_candidates?: Record<string, unknown> })
    .nlp_candidates;
  if (!data || typeof data !== "object") return null;
  const status = String(data.status || "");
  const engine = String(data.engine || "spacy");
  const engineVersion = String(data.engine_version || "");
  const model = String(data.model || "");
  const language = String(data.language || "");
  const reason = String(data.reason || "");
  return { status, engine, engineVersion, model, language, reason };
});
const nlpProvenanceLabel = computed(() => {
  const item = nlpProvenance.value;
  if (!item) return "";
  const parts = [
    item.engine === "spacy" ? "spaCy" : item.engine,
    item.engineVersion ? `v${item.engineVersion}` : "",
    item.model,
    item.language,
  ].filter(Boolean);
  if (item.status !== "ok") parts.push(item.reason || item.status);
  return parts.join(" · ");
});

const metadataPipelineTrace = computed<PipelineRunTrace | null>(() => {
  const memory = (
    props.record as unknown as {
      editorial_memory_used?: { pipeline_trace?: unknown };
    }
  ).editorial_memory_used;
  const trace = memory?.pipeline_trace;
  if (!trace || typeof trace !== "object") return null;
  const candidate = trace as Partial<PipelineRunTrace>;
  return candidate.run_id && candidate.pipeline_id && Array.isArray(candidate.stages)
    ? (trace as PipelineRunTrace)
    : null;
});
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
const repeatableGroups = computed(() =>
  Object.fromEntries(
    (props.schema?.groups || [])
      .filter((group) => group.repeatable)
      .map((group) => [group.key, group]),
  ),
);
const repeatableMembers = (field: string) =>
  repeatableGroups.value[field]
    ? (props.schema?.fields || []).filter((item) => item.group === field)
    : [];
const canonicalAssertions = computed(() =>
  currentFieldAssertions(props.record as unknown as Record<string, unknown>),
);
const fieldOrder = computed<string[]>(() =>
  props.schema
    ? reviewableMetadataFieldNames(props.record as unknown as Record<string, unknown>, props.schema)
    : reviewableMetadataFieldNames(props.record as unknown as Record<string, unknown>, null),
);
const fieldLabel = (field: string) =>
  schemaFields.value[field]?.label || repeatableGroups.value[field]?.label || "";
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
  const legacy = props.record.metadata_field_status?.[field] as Record<string, unknown> | undefined;
  // A reviewer decision is applied immediately in Record Review. Until its
  // serialized write returns, the canonical assertion projection still
  // describes the preceding model state and must not repaint the old value.
  if (legacy?.optimistic_review === true)
    return withoutTransportItems(unwrapMetadataValue(props.record[field]));
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
// Precedents kept from the last enrichment arrive in one request per record, so each pending field shows its count
// without being opened. A field without kept precedents (or a failed request) loads its own when opened.
const keptPrecedents = ref<Record<string, MetadataPrecedents>>({});
watch(
  // A primitive key: polling replaces the record object, which must not clear and refetch kept precedents.
  () => JSON.stringify([props.buildId, props.record.record_id, attentionFields.value.length > 0]),
  async (key) => {
    const [buildId, recordId, anyPending] = JSON.parse(key) as [string, string, boolean];
    keptPrecedents.value = {};
    if (!buildId || !anyPending) return;
    try {
      const result = await corpusBuilderApi.fieldPrecedents(buildId, recordId);
      if (buildId === props.buildId && recordId === props.record.record_id)
        keptPrecedents.value = result.fields || {};
    } catch {
      keptPrecedents.value = {};
    }
  },
  { immediate: true },
);
// "Use this value" from a precedent fills that field's draft; the reviewer still chooses evidence and saves.
const prefills = ref<Record<string, { value: unknown; key: number }>>({});
let prefillKey = 0;
function usePrecedentValue(field: string, value: unknown) {
  prefills.value = { ...prefills.value, [field]: { value, key: ++prefillKey } };
}
watch(
  () => props.record.record_id,
  () => {
    prefills.value = {};
  },
);
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
/** How many reviewed examples the model's prompt carried for this field (0 = the model worked alone). */
function memoryExamples(field: string): number {
  const used = (
    props.record as unknown as {
      editorial_memory_used?: { example_counts?: Record<string, number> };
    }
  ).editorial_memory_used;
  return Number(used?.example_counts?.[field] || 0);
}
function memoryHints(field: string): MemoryHint[] {
  const all = (props.record as unknown as { memory_hints?: Record<string, MemoryHint[]> })
    .memory_hints;
  return (all?.[field] || []).filter((hint) => !hint.absence);
}
function status(field: string) {
  const legacy = (props.record.metadata_field_status?.[field] || {}) as Record<string, unknown>;
  if (legacy.optimistic_review === true) return legacy;
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
function nlpOptions(field: string): string[] {
  const data = (
    props.record as unknown as {
      nlp_candidates?: {
        status?: string;
        fields?: Record<string, Array<{ start?: number; end?: number; text?: string }>>;
      };
    }
  ).nlp_candidates;
  if (!data || data.status !== "ok") return [];
  const sourceText = String(props.record.text || "");
  const candidates = data.fields?.[field] || [];
  return candidates.flatMap((candidate) => {
    const start = Number(candidate.start);
    const end = Number(candidate.end);
    const text = String(candidate.text || "").trim();
    if (!text || !Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end <= start)
      return [];
    // A text edit makes stored offsets stale. Never surface a candidate unless the
    // retained exact span still binds to the current Record text.
    return sourceText.slice(start, end) === candidate.text ? [text] : [];
  });
}
function foreignClosedVocabulary(field: string): Set<string> {
  const own = new Set((spec(field).allowedValues || []).map((value) => value.toLocaleLowerCase()));
  const all = new Set(
    [
      ...props.regionTypes,
      ...props.discourseRoles,
      ...PROPOSITION_STATUS_VALUES,
      ...STANCE_VALUES,
      ...Object.values(schemaFields.value).flatMap((schemaField) =>
        schemaField.type === "choice" && schemaField.strict
          ? schemaField.values.map((item) => item.value)
          : [],
      ),
    ].map((value) => String(value).trim().toLocaleLowerCase()),
  );
  for (const value of own) all.delete(value);
  return all;
}
function isSafeSuggestionForField(field: string, value: string): boolean {
  const normalized = value.trim().toLocaleLowerCase();
  if (!normalized || MACHINE_VOCABULARY_LABELS.has(normalized)) return false;
  if (spec(field).control !== "enum" && foreignClosedVocabulary(field).has(normalized))
    return false;
  return true;
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
      Record<string, unknown> | undefined;
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
  // Only the server's exact, field-local POS/NER spans are allowed into reviewer
  // suggestions. The old capitalized-word regex admitted sentence-initial noise.
  values.push(...nlpOptions(field));
  const cleaned =
    item.control === "multi-combobox" ? usableListOptions(values) : usableOptions(values);
  return [...new Set(cleaned.filter((value) => isSafeSuggestionForField(field, value)))].sort(
    (a, b) => a.localeCompare(b),
  );
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
// After a decision, focus moves to the next field still to decide (its Confirm button, so Enter confirms it).
// Record Review applies decision state optimistically, so the last decision can report completion immediately;
// an explicit blocking caller can still hold `savingField` / `batchSaving` until it is ready to advance.
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
              ? i18n.tf(
                  attentionFields.length === 1
                    ? "pdf_corpus.metadata_decisions_count_one"
                    : "pdf_corpus.metadata_decisions_count",
                  { count: attentionFields.length },
                )
              : i18n.t("pdf_corpus.metadata_ready")
        }}</span
      >
    </header>
    <p v-if="nlpProvenance" class="nlp-provenance">
      <b>{{ i18n.t("pdf_corpus.linguistic_analyzer_record") }}</b>
      <span>{{ nlpProvenanceLabel }}</span>
    </p>
    <CorpusEnrichmentChanges
      :record="record as unknown as Record<string, unknown>"
      :busy="busy"
      @resolve="(field, value) => emit('resolve', field, value)"
    />
    <p v-if="enrichmentPending" class="enrichment-note" role="status">
      {{ i18n.t("pdf_corpus.metadata_enrichment_pending_help") }}
    </p>
    <details v-if="metadataPipelineTrace" class="metadata-pipeline-trace">
      <summary>
        {{
          i18n.t(
            "pdf_corpus.metadata_pipeline_trace_title",
            "How metadata precedents were retrieved",
          )
        }}
      </summary>
      <p>
        {{
          i18n.t(
            "pdf_corpus.metadata_pipeline_trace_help",
            "This audit trace shows the exact saved retrieval pipeline used for this record, including semantic search, reranking, fallbacks, candidate counts, and timing. It describes how advisory precedents were selected; it does not make those precedents authoritative metadata.",
          )
        }}
      </p>
      <PipelineRunTracePanel :trace="metadataPipelineTrace" />
    </details>
    <div v-if="llmSuggestionCount" class="suggestion-toolbar">
      <b>{{
        i18n.tf("pdf_corpus.llm_suggestions_ready", {
          count: llmSuggestionCount,
        })
      }}</b>
      <UiTooltip
        :text="i18n.t('pdf_corpus.llm_suggestions_ready_help')"
        trigger-mode="content"
        :content-focusable="Boolean(busy || batchSaving)"
        placement="bottom"
      >
        <button
          type="button"
          class="btn small primary"
          :disabled="busy || batchSaving"
          @click="
            emit('resolveMany', llmSuggestions);
            decided('');
          "
        >
          {{ i18n.t("pdf_corpus.accept_all_suggestions") }}
        </button>
      </UiTooltip>
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
          :repeatable-members="repeatableMembers(field)"
          :repeatable-max-items="repeatableGroups[field]?.max_items || undefined"
          :field="field"
          :value="fieldValue(field)"
          :status="status(field)"
          :memory-examples="memoryExamples(field)"
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
          :prefill="prefills[field] || null"
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
          @save-with-human-source="
            (value, note) => {
              emit('resolveWithHumanSource', field, value, note);
              decided(field);
            }
          "
          @browse-evidence="(value) => emit('browseEvidence', field, value)"
          @dirty="(value) => fieldDirty(field, value)"
        >
          <template #policy>
            <CorpusFieldPolicyBadges
              :field="field"
              :schema-field="schemaFields[field]"
              :core-required="requiredFields.has(field)"
            />
          </template>
        </CorpusMetadataFieldEditor>
        <CorpusFieldPrecedents
          v-if="buildId && pendingSet.has(field)"
          :build-id="buildId"
          :record-id="record.record_id"
          :field="field"
          :field-label="fieldLabel(field)"
          :preloaded="keptPrecedents[field] || null"
          :source-block-ids="record.source_block_ids || []"
          :can-use="!fieldBusy(field)"
          @use="(value) => usePrecedentValue(field, value)"
        />
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
            :repeatable-members="repeatableMembers(field)"
            :repeatable-max-items="repeatableGroups[field]?.max_items || undefined"
            :field="field"
            :value="fieldValue(field)"
            :status="status(field)"
            :memory-examples="memoryExamples(field)"
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
            @save-with-human-source="
              (value, note) => emit('resolveWithHumanSource', field, value, note)
            "
            @browse-evidence="(value) => emit('browseEvidence', field, value)"
            @dirty="(value) => fieldDirty(field, value)"
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
            :repeatable-members="repeatableMembers(field)"
            :repeatable-max-items="repeatableGroups[field]?.max_items || undefined"
            :field="field"
            :value="fieldValue(field)"
            :status="status(field)"
            :memory-examples="memoryExamples(field)"
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
            @save-with-human-source="
              (value, note) => emit('resolveWithHumanSource', field, value, note)
            "
            @browse-evidence="(value) => emit('browseEvidence', field, value)"
            @dirty="(value) => fieldDirty(field, value)"
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
.nlp-provenance {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  margin: -4px 0 0;
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  line-height: 1.45;
}
.nlp-provenance b {
  color: var(--text-secondary);
}
.enrichment-note {
  margin: 0;
  padding: 8px 10px;
  border-radius: var(--radius-control);
  background: var(--surface-inset, var(--soft));
  font-size: var(--fs-sm);
  line-height: 1.5;
}
.metadata-pipeline-trace {
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset, var(--soft));
}
.metadata-pipeline-trace > summary {
  min-height: 32px;
  font-size: var(--fs-sm);
  font-weight: 700;
  cursor: pointer;
}
.metadata-pipeline-trace > p {
  margin: 6px 0 10px;
  color: var(--text-tertiary);
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
