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

import type { CorpusBuild } from "../../../api/corpus";

export function firstValidationRecordId(build: CorpusBuild | null | undefined): string {
  const validation = build?.validation || {};
  const actionable = validation.validation_issues?.find((item) => item?.record_id);
  if (actionable?.record_id) return String(actionable.record_id);

  for (const key of [
    "metadata_evidence_errors",
    "metadata_schema_errors",
    "relationship_errors",
    "human_ownership_errors",
    "record_content_errors",
  ] as const) {
    const items = validation[key];
    if (!Array.isArray(items)) continue;
    const found = items.find(
      (item) => item && typeof item === "object" && "record_id" in item && item.record_id,
    );
    if (found && typeof found === "object" && "record_id" in found) {
      return String(found.record_id);
    }
  }

  const citation = validation.citation_errors?.find(Boolean);
  return citation ? String(citation) : "";
}
