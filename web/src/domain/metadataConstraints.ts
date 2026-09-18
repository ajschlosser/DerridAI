export type MetadataConstraintResult = { field: string; value: unknown; reasonKey: string };

const NON_PRIMARY_REGIONS = new Set(["front_matter", "back_matter", "bibliography", "index", "paratext"]);

export function metadataConstraints(changes: Record<string, unknown>, current: Record<string, unknown> = {}): MetadataConstraintResult[] {
  const region = String(changes.region_type ?? current.region_type ?? "");
  const results: MetadataConstraintResult[] = [];
  if (NON_PRIMARY_REGIONS.has(region)) {
    results.push({ field: "primary_text", value: false, reasonKey: "pdf_corpus.constraint_non_primary_region" });
  } else if (region === "main_text") {
    results.push({ field: "primary_text", value: true, reasonKey: "pdf_corpus.constraint_main_text_primary" });
  }
  return results;
}

export function isHardMetadataConstraint(field: string, changes: Record<string, unknown>, current: Record<string, unknown> = {}) {
  return metadataConstraints(changes, current).some(item => item.field === field);
}
