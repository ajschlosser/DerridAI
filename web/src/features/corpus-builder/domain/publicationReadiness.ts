/* Copyright 2026 Aaron John Schlosser, PhD. */
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
