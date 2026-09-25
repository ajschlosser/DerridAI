/* Copyright 2026 Aaron John Schlosser, PhD. */
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
import { assertionFieldNames } from "./fieldAssertions";
import { TOUCHUP_CREATABLE_FIELDS, TOUCHUP_GROUPS } from "./runtimeConstants";

const NON_TOUCHUP_FIELDS = new Set([
  "record_id",
  "record_revision",
  "source_document_id",
  "source_asset_id",
  "source_spans",
  "source_units",
  "source_unit_ids",
  "source_block_ids",
  "metadata_field_status",
  "metadata_evidence",
  "metadata_decisions",
  "field_assertions",
  "current_field_assertions",
  "updates",
  "activity",
  "accepted",
  "rejected",
  "review_disposition",
  "review_state",
  "metadata_complete",
  "metadata_incomplete_fields",
  "metadata_review_fields",
]);

// Which metadata fields the LLM touch-up dialog offers for a record. Moved verbatim from the legacy runtime.

export function touchupFieldsForRecord(record: Loose): string[] {
  const known: string[] = [];
  for (const group of TOUCHUP_GROUPS) {
    for (const field of group.fields) {
      if (field in record || TOUCHUP_CREATABLE_FIELDS.has(field)) {
        if (!known.includes(field)) known.push(field);
      }
    }
  }
  for (const field of assertionFieldNames(record)) {
    if (!known.includes(field) && !NON_TOUCHUP_FIELDS.has(field)) known.push(field);
  }
  for (const field of Object.keys(record)) {
    if (
      !known.includes(field) &&
      field !== "text_length" &&
      !field.startsWith("_") &&
      !NON_TOUCHUP_FIELDS.has(field) &&
      (typeof record[field] === "string" ||
        typeof record[field] === "number" ||
        typeof record[field] === "boolean" ||
        Array.isArray(record[field]))
    )
      known.push(field);
  }
  return known;
}
