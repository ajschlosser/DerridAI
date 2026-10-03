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

export type MetadataConstraintResult = { field: string; value: unknown; reasonKey: string };

const NON_PRIMARY_REGIONS = new Set([
  "front_matter",
  "back_matter",
  "bibliography",
  "index",
  "paratext",
]);

export function metadataConstraints(
  changes: Record<string, unknown>,
  current: Record<string, unknown> = {},
): MetadataConstraintResult[] {
  const region = String(changes.region_type ?? current.region_type ?? "");
  const results: MetadataConstraintResult[] = [];
  if (NON_PRIMARY_REGIONS.has(region)) {
    results.push({
      field: "primary_text",
      value: false,
      reasonKey: "pdf_corpus.constraint_non_primary_region",
    });
  } else if (region === "main_text") {
    results.push({
      field: "primary_text",
      value: true,
      reasonKey: "pdf_corpus.constraint_main_text_primary",
    });
  }
  return results;
}

export function isHardMetadataConstraint(
  field: string,
  changes: Record<string, unknown>,
  current: Record<string, unknown> = {},
) {
  return metadataConstraints(changes, current).some((item) => item.field === field);
}
