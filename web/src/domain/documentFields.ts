/* Copyright 2026 Aaron John Schlosser, PhD. */
import {
  completeDocumentFields,
  type DocumentRequirement,
  type MetadataSchema,
} from "../api/metadataSchemas";

export interface MissingDocumentField {
  name: string;
  requiredFor: DocumentRequirement[];
}

/**
 * Required document fields that detection on source load did not fill. Only these are ever asked of the user;
 * a detected value is never re-asked.
 */
export function missingRequiredDocumentFields(
  schema: Pick<MetadataSchema, "document_fields"> | null | undefined,
  detected: Record<string, unknown> | null | undefined,
): MissingDocumentField[] {
  const values = detected ?? {};
  return completeDocumentFields(schema?.document_fields)
    .filter((policy) => policy.required_for.length > 0)
    .filter((policy) => {
      const value = values[policy.name];
      return value === undefined || value === null || String(value).trim() === "";
    })
    .map((policy) => ({ name: policy.name, requiredFor: policy.required_for }));
}

/** Only the non-empty values for fields still missing, trimmed: what a build request should carry. */
export function suppliedDocumentMetadata(
  missing: MissingDocumentField[],
  values: Record<string, string>,
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const { name } of missing) {
    const value = String(values[name] ?? "").trim();
    if (value) out[name] = value;
  }
  return out;
}
