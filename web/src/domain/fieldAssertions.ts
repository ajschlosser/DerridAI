/* Copyright 2026 Aaron John Schlosser, PhD. */

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

export interface FieldAssertionEvidenceView {
  [key: string]: unknown;
}

export interface FieldAssertionView {
  assertion_id?: string;
  record_revision?: number;
  field_id: string;
  field_name: string;
  value: unknown;
  derivation_method?: string;
  evaluation_status?: string;
  authority_status?: string;
  value_status?: string;
  method?: string;
  confidence?: number | null;
  reason?: string;
  evidence?: FieldAssertionEvidenceView[];
  actor?: string;
  model?: string;
  run_id?: string;
  schema_id?: string;
  schema_version?: string;
  supersedes_assertion_id?: string;
  created_at?: string;
}

export interface FieldAssertionConflictView {
  field_id: string;
  field_name: string;
  current: FieldAssertionView | null;
  alternatives: FieldAssertionView[];
  disputed: boolean;
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

function selectedAssertionIds(record: Loose | null | undefined): Record<string, unknown> {
  return record?.current_field_assertions &&
    typeof record.current_field_assertions === "object" &&
    !Array.isArray(record.current_field_assertions)
    ? (record.current_field_assertions as Record<string, unknown>)
    : {};
}

function normalizedAssertion(raw: Loose, fallbackFieldId: string): FieldAssertionView | null {
  const fieldName = String(raw.field_name || "").trim();
  if (!fieldName) return null;
  const evidence = Array.isArray(raw.evidence)
    ? raw.evidence.filter((item): item is FieldAssertionEvidenceView =>
        Boolean(item && typeof item === "object" && !Array.isArray(item)),
      )
    : undefined;
  return {
    assertion_id: raw.assertion_id ? String(raw.assertion_id) : undefined,
    record_revision:
      typeof raw.record_revision === "number" && Number.isFinite(raw.record_revision)
        ? raw.record_revision
        : undefined,
    field_id: String(raw.field_id || fallbackFieldId),
    field_name: fieldName,
    value: raw.value,
    derivation_method: raw.derivation_method ? String(raw.derivation_method) : undefined,
    evaluation_status: raw.evaluation_status ? String(raw.evaluation_status) : undefined,
    authority_status: raw.authority_status ? String(raw.authority_status) : undefined,
    value_status: raw.value_status ? String(raw.value_status) : undefined,
    method: raw.method ? String(raw.method) : undefined,
    confidence:
      raw.confidence === null || typeof raw.confidence === "number" ? raw.confidence : undefined,
    reason: raw.reason ? String(raw.reason) : undefined,
    evidence,
    actor: raw.actor ? String(raw.actor) : undefined,
    model: raw.model ? String(raw.model) : undefined,
    run_id: raw.run_id ? String(raw.run_id) : undefined,
    schema_id: raw.schema_id ? String(raw.schema_id) : undefined,
    schema_version: raw.schema_version ? String(raw.schema_version) : undefined,
    supersedes_assertion_id: raw.supersedes_assertion_id
      ? String(raw.supersedes_assertion_id)
      : undefined,
    created_at: raw.created_at ? String(raw.created_at) : undefined,
  };
}

function assertionHistoryById(
  record: Loose | null | undefined,
  fieldId: string,
): FieldAssertionView[] {
  const rawValues = assertionBuckets(record)[fieldId];
  if (!Array.isArray(rawValues)) return [];
  return rawValues
    .filter((item): item is Loose => Boolean(item && typeof item === "object"))
    .map((item) => normalizedAssertion(item, fieldId))
    .filter((item): item is FieldAssertionView => Boolean(item));
}

export function currentFieldAssertions(record: Loose | null | undefined): FieldAssertionView[] {
  const buckets = assertionBuckets(record);
  const selected = selectedAssertionIds(record);
  const out: FieldAssertionView[] = [];
  for (const fieldId of Object.keys(buckets)) {
    const values = assertionHistoryById(record, fieldId);
    if (!values.length) continue;
    const selectedId = String(selected[fieldId] || "");
    const current =
      (selectedId && values.find((item) => String(item.assertion_id || "") === selectedId)) ||
      values.at(-1);
    if (current) out.push(current);
  }
  return out;
}

export function assertionHistory(
  record: Loose | null | undefined,
  field: string,
): FieldAssertionView[] {
  const direct = assertionHistoryById(record, field);
  if (direct.length) return direct;
  for (const fieldId of Object.keys(assertionBuckets(record))) {
    const values = assertionHistoryById(record, fieldId);
    if (values.some((item) => item.field_name === field)) return values;
  }
  return [];
}

function comparableValue(assertion: FieldAssertionView): string {
  if (assertion.value_status === "confirmed_absent") return "__confirmed_absent__";
  if (assertion.value_status && assertion.value_status !== "present")
    return `__${assertion.value_status}__`;
  try {
    return JSON.stringify(assertion.value);
  } catch {
    return String(assertion.value);
  }
}

export function assertionConflict(
  record: Loose | null | undefined,
  field: string,
): FieldAssertionConflictView | null {
  const history = assertionHistory(record, field);
  if (!history.length) return null;
  const current =
    currentFieldAssertions(record).find(
      (item) => item.field_id === field || item.field_name === field,
    ) || history.at(-1)!;
  const currentValue = comparableValue(current);
  const alternatives = history.filter(
    (item) =>
      item.assertion_id !== current.assertion_id &&
      (comparableValue(item) !== currentValue || item.authority_status === "disputed"),
  );
  return {
    field_id: current.field_id,
    field_name: current.field_name,
    current,
    alternatives,
    disputed:
      current.authority_status === "disputed" ||
      alternatives.some((item) => item.authority_status === "disputed"),
  };
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
  if (
    id.startsWith("derridai.quotation.") ||
    BUILTIN_OVERVIEW_ASSERTION_FIELDS.has(assertion.field_name)
  )
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
