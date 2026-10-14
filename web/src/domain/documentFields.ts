/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
