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
  const scholarlyFields = schema?.fields?.length
    ? schema.fields.map((field) => field.name)
    : [...LEGACY_SCHOLARLY_FIELDS];
  const fields = Array.from(
    new Set([
      ...STRUCTURAL_EDITABLE_FIELDS,
      ...scholarlyFields,
      ...assertionFieldNames(record),
      ...DOCUMENT_EDITABLE_FIELDS,
    ]),
  );
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
  return Array.from(new Set([...configuredEvidence, ...assertedEvidence, ...persistedEvidence])).filter(
    (field) =>
      alwaysVisible.has(field) ||
      hasMeaningfulValue(
        record[field] !== undefined ? record[field] : assertionValueMap[field],
      ),
  );
}
