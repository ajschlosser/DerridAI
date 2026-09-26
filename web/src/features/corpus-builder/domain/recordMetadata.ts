/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { MetadataSchema } from "../../../api/metadataSchemas";
import {
  assertionFieldNames,
  assertionValues,
  currentFieldAssertions,
} from "../../../domain/fieldAssertions";

const STRUCTURAL_EDITABLE_FIELDS = ["region_type", "primary_text", "discourse_role"] as const;

const DOCUMENT_EDITABLE_FIELDS = [
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
  "document_is_translation",
  "language",
] as const;

export const OPERATIONAL_RECORD_FIELDS = new Set([
  "record_id",
  "record_revision",
  "source_document_id",
  "source_asset_id",
  "source_spans",
  "source_units",
  "source_unit_ids",
  "source_block_ids",
  "source_extracted_text",
  "text",
  "text_length",
  "text_review_status",
  "text_reviewed_at",
  "text_revision_history",
  "page_start",
  "page_end",
  "pdf_file",
  "pdf_page",
  "pdf_pages",
  "accepted",
  "rejected",
  "review_disposition",
  "review_state",
  "needs_review",
  "review_reason",
  "metadata_complete",
  "metadata_incomplete_fields",
  "metadata_review_fields",
  "metadata_attention_reasons",
  "metadata_needs_attention",
  "metadata_stage_status",
  "metadata_execution_ledger",
  "metadata_decisions",
  "metadata_enrichment_state",
  "metadata_enrichment_history",
  "metadata_disputes",
  "human_touched_fields",
  "human_touched_at",
  "activity",
  "updates",
  "review_events",
  "source_quality_issues",
  "resolved_source_quality_issues",
  "text_noise",
  "can_accept",
  "build_id",
  "publication_id",
  "field_assertions",
  "current_field_assertions",
  "metadata_field_status",
  "metadata_evidence",
  "field_assessments",
  "field_evidence",
  "recheck_results",
  "second_opinion",
  "blind_reveals",
  "slice_lineage",
  "boundary_review",
  "boundary_suspicion",
  "boundary_quality_issues",
  "text_cleanup_status",
  "text_cleanup_report",
  "text_touchup_proposal",
]);

const LEGACY_SCHOLARLY_FIELDS = [
  "region_author",
  "speaker",
  "position_holder",
  "target",
  "proposition_status",
  "semantic_function",
  "stance",
  "claim_scope",
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
] as const;

type LooseRecord = Record<string, unknown>;

export function isReviewVisibleSchemaField(field: MetadataSchema["fields"][number]): boolean {
  return field.role !== "operational" && field.review_visibility !== "hidden";
}

/**
 * Bookkeeping keys that live on a record but are not scholarly metadata (segmentation evidence,
 * NLP hints, lineage...). Mirrors the API's `_operational_key`; a schema field of the same name
 * is still shown because the schema, not the key, decides.
 */
const OPERATIONAL_PREFIXES = [
  "boundary_",
  "metadata_",
  "review_",
  "text_",
  "source_",
  "topology_",
  "nlp_",
  "slice_",
  "human_",
  "llm_",
  "segmentation_",
  "unit_",
  "recheck",
  "second_opinion",
  "blind_",
  "printed_page",
  "extraction_",
  "acceptance_",
  "field_assertion",
  "current_field",
  "record_sizing",
  "editorial_",
  "autonomous_",
  "pdf_",
  "inline_",
  "full_",
];
const OPERATIONAL_KEYS = new Set(["lineage", "media_kind", "parent_block_id"]);
export function isOperationalKey(key: string): boolean {
  return OPERATIONAL_KEYS.has(key) || OPERATIONAL_PREFIXES.some((prefix) => key.startsWith(prefix));
}

function reviewableAssertionFieldNames(
  record: LooseRecord,
  schema?: MetadataSchema | null,
): string[] {
  const schemaByName = new Map((schema?.fields || []).map((field) => [field.name, field]));
  return assertionFieldNames(record).filter((field) => {
    if (OPERATIONAL_RECORD_FIELDS.has(field)) return false;
    const configured = schemaByName.get(field);
    if (configured) return isReviewVisibleSchemaField(configured);
    return !isOperationalKey(field);
  });
}

export function reviewableMetadataFieldNames(
  record: LooseRecord,
  schema?: MetadataSchema | null,
): string[] {
  const scholarlyFields = schema?.fields?.length
    ? schema.fields.filter(isReviewVisibleSchemaField).map((field) => field.name)
    : [...LEGACY_SCHOLARLY_FIELDS];
  return Array.from(
    new Set([
      ...STRUCTURAL_EDITABLE_FIELDS,
      ...scholarlyFields,
      ...reviewableAssertionFieldNames(record, schema),
      ...DOCUMENT_EDITABLE_FIELDS,
    ]),
  ).filter((field) => !OPERATIONAL_RECORD_FIELDS.has(field));
}

/**
 * Shape the advanced human-editable metadata packet from canonical schema and
 * assertion identity. Operational/source fields are intentionally excluded.
 *
 * Fixed lists here are structural/document compatibility policy, not the
 * universe of scholarly metadata: schema fields and canonical assertions are
 * discovered dynamically.
 */
export function editableRecordMetadata(
  record: LooseRecord,
  schema?: MetadataSchema | null,
): Record<string, unknown> {
  const fields = reviewableMetadataFieldNames(record, schema);
  return Object.fromEntries(
    fields.filter((field) => record[field] !== undefined).map((field) => [field, record[field]]),
  );
}

function hasMeaningfulValue(value: unknown): boolean {
  if (Array.isArray(value)) return value.length > 0;
  return value !== null && value !== undefined && value !== "";
}

/**
 * Evidence review follows schema policy and canonical assertions instead of a
 * closed list of Derrida-specific field names.
 */
export function evidenceCandidateFieldNames(
  record: LooseRecord,
  schema?: MetadataSchema | null,
): string[] {
  const persistedEvidence =
    record.metadata_evidence &&
    typeof record.metadata_evidence === "object" &&
    !Array.isArray(record.metadata_evidence)
      ? Object.keys(record.metadata_evidence as Record<string, unknown>)
      : [];
  const assertions = currentFieldAssertions(record);
  const assertedEvidence = assertions
    .filter((assertion) => Array.isArray(assertion.evidence) && assertion.evidence.length > 0)
    .map((assertion) => assertion.field_name);
  const assertionValueMap = assertionValues(record);
  const configuredEvidence = (schema?.fields || [])
    .filter((field) => field.evidence)
    .map((field) => field.name);

  const alwaysVisible = new Set([...persistedEvidence, ...assertedEvidence]);
  return Array.from(
    new Set([...configuredEvidence, ...assertedEvidence, ...persistedEvidence]),
  ).filter(
    (field) =>
      alwaysVisible.has(field) ||
      hasMeaningfulValue(record[field] !== undefined ? record[field] : assertionValueMap[field]),
  );
}
