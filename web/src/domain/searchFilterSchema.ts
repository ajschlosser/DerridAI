/* Copyright 2026 Aaron John Schlosser, PhD. */
import { SEARCH_AUTOCOMPLETE_EXCLUDED, SEARCH_FILTER_FIELDS } from "./runtimeConstants";
import type { MetadataSchema, SchemaField } from "../api/metadataSchemas";

const STORAGE_KEY = "derridai.search.filterSchema.v1";
const DEFAULT_SCHEMA_ID = "default";

export type FilterFieldKind = SchemaField["type"] | "text";

export interface SearchFilterFieldOption {
  key: string;
  label: string;
  kind: FilterFieldKind;
}

export function filterFieldsFromSchema(schema: MetadataSchema | null | undefined): SearchFilterFieldOption[] {
  const fields = schema?.fields || [];
  return fields
    .filter((field) => field.name && !SEARCH_AUTOCOMPLETE_EXCLUDED.has(field.name) && !field.name.startsWith("__"))
    .map((field) => ({
      key: field.name,
      label: field.label || field.name,
      kind: field.type || "text",
    }));
}

export function filterFieldsFromNames(
  names: string[],
  labels: (key: string) => string = (key) => key,
): SearchFilterFieldOption[] {
  return [...new Set(names.filter((name) => name && !name.startsWith("__") && !SEARCH_AUTOCOMPLETE_EXCLUDED.has(name)))].map(
    (key) => ({ key, label: labels(key), kind: kindForLegacyField(key) }),
  );
}

export function kindForLegacyField(field: string): FilterFieldKind {
  if (
    [
      "page_start",
      "page_end",
      "year",
      "publication_year",
      "text_length",
      "extraction_quality",
      "attribution_confidence",
      "semantic_classification_confidence",
    ].includes(field)
  )
    return "number";
  if (field === "is_direct_quote" || field === "primary_text" || field === "needs_review" || field === "document_is_translation")
    return "boolean";
  if (
    [
      "topics",
      "concepts",
      "persons",
      "works_referenced",
      "institutions_referenced",
      "locations_referenced",
      "events_referenced",
      "groups_referenced",
      "languages_referenced",
      "document_language",
      "quoted_speaker",
      "quotation_chain",
    ].includes(field)
  )
    return "list";
  if (field === "stance" || field === "proposition_status" || field === "region_type" || field === "discourse_role")
    return "choice";
  return "text";
}

/**
 * Prefer the corpus-associated or user-chosen schema. If neither yields fields,
 * use collection-declared filter fields, then the built-in Search field list.
 */
export function resolveSearchFilterFields(options: {
  schema?: MetadataSchema | null;
  collectionFields?: string[];
  availableFields?: string[];
  labels?: (key: string) => string;
}): SearchFilterFieldOption[] {
  const labels = options.labels || ((key: string) => key);
  const fromSchema = filterFieldsFromSchema(options.schema);
  if (fromSchema.length) return fromSchema;
  const collection = filterFieldsFromNames(options.collectionFields || [], labels);
  if (collection.length) return collection;
  return filterFieldsFromNames([...(SEARCH_FILTER_FIELDS as string[]), ...(options.availableFields || [])], labels);
}

export function filterOpsForKind(
  kind: FilterFieldKind,
  options: { database?: boolean; method?: string } = {},
): Array<[string, string, string]> {
  const numeric = kind === "number";
  const collection = kind === "list";
  const base = numeric
    ? ([
        ["eq", "search.operator_eq", "equals"],
        ["neq", "search.operator_neq", "not equal"],
        ["gte", "search.operator_gte", "at least"],
        ["lte", "search.operator_lte", "at most"],
        ["empty", "search.operator_empty", "is empty"],
        ["notempty", "search.operator_notempty", "is not empty"],
      ] as Array<[string, string, string]>)
    : collection
      ? ([
          ["has", "search.operator_has", "contains"],
          ["nhas", "search.operator_nhas", "does not contain"],
          ["eq", "search.operator_eq", "equals"],
          ["neq", "search.operator_neq", "not equal"],
          ["empty", "search.operator_empty", "is empty"],
          ["notempty", "search.operator_notempty", "is not empty"],
        ] as Array<[string, string, string]>)
      : ([
          ["eq", "search.operator_eq", "equals"],
          ["neq", "search.operator_neq", "not equal"],
          ["has", "search.operator_has", "contains"],
          ["nhas", "search.operator_nhas", "does not contain"],
          ["empty", "search.operator_empty", "is empty"],
          ["notempty", "search.operator_notempty", "is not empty"],
        ] as Array<[string, string, string]>);
  if (options.database) {
    const allowed = options.method === "filter" ? ["eq", "has"] : ["eq"];
    return base.filter(([op]) => allowed.includes(op));
  }
  return base;
}

export function loadFilterSchemaOverride(store: string): string {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") as Record<string, string>;
    return String(raw[store] || "");
  } catch {
    return "";
  }
}

export function saveFilterSchemaOverride(store: string, schemaId: string) {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") as Record<string, string>;
    if (schemaId) raw[store] = schemaId;
    else delete raw[store];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(raw));
  } catch {
    /* browser storage may be unavailable */
  }
}

export function defaultFilterSchemaId() {
  return DEFAULT_SCHEMA_ID;
}

export function chosenFilterSchemaId(options: { store: string; associatedId?: string }) {
  return loadFilterSchemaOverride(options.store) || options.associatedId || DEFAULT_SCHEMA_ID;
}

const NUMERIC_FILTER_FIELDS = new Set(["page_start", "page_end", "year", "publication_year", "text_length", "extraction_quality", "attribution_confidence", "semantic_classification_confidence"]);
const COLLECTION_FILTER_FIELDS = new Set(["topics", "concepts", "persons", "works_referenced", "institutions_referenced", "locations_referenced", "events_referenced", "groups_referenced", "languages_referenced", "document_language", "quoted_speaker", "quotation_chain"]);

export function filterOpsForField(field: string): [string, string][] {
  if (NUMERIC_FILTER_FIELDS.has(field)) return [["eq", "equals"], ["neq", "not equal"], ["gte", "greater than or equal"], ["lte", "less than or equal"], ["empty", "is empty"], ["notempty", "is not empty"]];
  if (COLLECTION_FILTER_FIELDS.has(field)) return [["has", "contains"], ["nhas", "does not contain"], ["eq", "equals exactly"], ["neq", "does not equal"], ["empty", "is empty"], ["notempty", "is not empty"]];
  return [["eq", "equals"], ["neq", "not equal"], ["has", "contains"], ["nhas", "does not contain"], ["empty", "is empty"], ["notempty", "is not empty"]];
}
