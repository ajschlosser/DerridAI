/* Copyright 2026 Aaron John Schlosser, PhD. */

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

export interface FieldAssertionView {
  assertion_id?: string;
  field_id: string;
  field_name: string;
  value: unknown;
  derivation_method?: string;
  evaluation_status?: string;
  authority_status?: string;
  value_status?: string;
  confidence?: number | null;
}

const BUILTIN_INDEXING_FIELDS = new Set([
  "topics",
  "concepts",
  "persons",
  "works_referenced",
  "institutions_referenced",
  "locations_referenced",
  "events_referenced",
  "groups_referenced",
  "languages_referenced",
]);

const BUILTIN_OVERVIEW_ASSERTION_FIELDS = new Set([
  "region_type",
  "region_author",
  "primary_text",
  "is_direct_quote",
  "quoted_speaker",
  "quoted_author",
  "quoted_work",
  "quoted_position_holder",
  "quoted_addressee",
  "quoted_referent",
  "quotation_chain",
]);

function assertionBuckets(record: Loose | null | undefined): Record<string, unknown[]> {
  const raw = record?.field_assertions;
  return raw && typeof raw === "object" && !Array.isArray(raw)
    ? (raw as Record<string, unknown[]>)
    : {};
}

export function currentFieldAssertions(record: Loose | null | undefined): FieldAssertionView[] {
  const buckets = assertionBuckets(record);
  const selected =
    record?.current_field_assertions &&
    typeof record.current_field_assertions === "object" &&
    !Array.isArray(record.current_field_assertions)
      ? (record.current_field_assertions as Record<string, unknown>)
      : {};
  const out: FieldAssertionView[] = [];
  for (const [fieldId, rawValues] of Object.entries(buckets)) {
    const values = Array.isArray(rawValues)
      ? rawValues.filter((item): item is Loose => Boolean(item && typeof item === "object"))
      : [];
    if (!values.length) continue;
    const selectedId = String(selected[fieldId] || "");
    const current =
      (selectedId && values.find((item) => String(item.assertion_id || "") === selectedId)) ||
      values.at(-1);
    const fieldName = String(current?.field_name || "").trim();
    if (!current || !fieldName) continue;
    out.push({
      assertion_id: current.assertion_id ? String(current.assertion_id) : undefined,
      field_id: String(current.field_id || fieldId),
      field_name: fieldName,
      value: current.value,
      derivation_method: current.derivation_method ? String(current.derivation_method) : undefined,
      evaluation_status: current.evaluation_status ? String(current.evaluation_status) : undefined,
      authority_status: current.authority_status ? String(current.authority_status) : undefined,
      value_status: current.value_status ? String(current.value_status) : undefined,
      confidence:
        current.confidence === null || typeof current.confidence === "number"
          ? current.confidence
          : undefined,
    });
  }
  return out;
}

export function assertionFieldNames(record: Loose | null | undefined): string[] {
  return [...new Set(currentFieldAssertions(record).map((item) => item.field_name))];
}

export function assertionValues(record: Loose | null | undefined): Record<string, unknown> {
  const values: Record<string, unknown> = {};
  for (const assertion of currentFieldAssertions(record)) {
    if (assertion.value_status === "confirmed_absent") {
      values[assertion.field_name] = null;
      continue;
    }
    if (assertion.value_status && assertion.value_status !== "present") continue;
    values[assertion.field_name] = assertion.value;
  }
  return values;
}

export function assertionSummaries(record: Loose | null | undefined): FieldAssertionView[] {
  return currentFieldAssertions(record).map((item) => ({ ...item }));
}

export type AssertionPresentationTab = "overview" | "provenance" | "indexing";

export function assertionPresentationTab(assertion: FieldAssertionView): AssertionPresentationTab {
  const id = assertion.field_id;
  if (id.startsWith("derridai.indexing.") || BUILTIN_INDEXING_FIELDS.has(assertion.field_name))
    return "indexing";
  if (id.startsWith("derridai.quotation.") || BUILTIN_OVERVIEW_ASSERTION_FIELDS.has(assertion.field_name))
    return "overview";
  return "provenance";
}

export function assertionFieldsByTab(
  record: Loose | null | undefined,
): Record<AssertionPresentationTab, string[]> {
  const result: Record<AssertionPresentationTab, string[]> = {
    overview: [],
    provenance: [],
    indexing: [],
  };
  for (const assertion of currentFieldAssertions(record)) {
    const tab = assertionPresentationTab(assertion);
    if (!result[tab].includes(assertion.field_name)) result[tab].push(assertion.field_name);
  }
  return result;
}
