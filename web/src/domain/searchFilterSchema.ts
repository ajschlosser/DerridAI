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

import { SEARCH_AUTOCOMPLETE_EXCLUDED, SEARCH_FILTER_FIELDS } from "./runtimeConstants";
import type { MetadataSchema, SchemaField } from "../api/metadataSchemas";

const STORAGE_KEY = "derridai.search.filterSchema.v1";
const DEFAULT_SCHEMA_ID = "default";

export type FilterFieldKind = "text" | "number" | "boolean" | "choice" | "list";
export type FilterFieldCardinality = "scalar" | "collection";

export interface SearchFilterFieldOption {
  key: string;
  label: string;
  kind: FilterFieldKind;
  cardinality: FilterFieldCardinality;
  controlledValues: string[];
  fieldId?: string;
  semanticCompatibilityId?: string;
  /** False when the active database collection does not index this field for filtering. */
  filterable: boolean;
}

function kindForSchemaField(field: SchemaField): FilterFieldKind {
  if (field.type === "repeatable" || field.type === "list") return "list";
  return field.type || "text";
}

function controlledValues(field: SchemaField): string[] {
  return (field.values || [])
    .map((item) => String(item?.value || "").trim())
    .filter(Boolean);
}

export function filterFieldsFromSchema(
  schema: MetadataSchema | null | undefined,
  options: { filterableNames?: Iterable<string> | null } = {},
): SearchFilterFieldOption[] {
  const filterableNames =
    options.filterableNames == null ? null : new Set([...options.filterableNames].map(String));
  return (schema?.fields || [])
    .filter(
      (field) =>
        field.name &&
        !SEARCH_AUTOCOMPLETE_EXCLUDED.has(field.name) &&
        !field.name.startsWith("__") &&
        (filterableNames == null || filterableNames.has(field.name)),
    )
    .map((field) => {
      const kind = kindForSchemaField(field);
      return {
        key: field.name,
        label: field.label || field.name,
        kind,
        cardinality: kind === "list" ? "collection" : "scalar",
        controlledValues: controlledValues(field),
        fieldId: field.field_id || undefined,
        semanticCompatibilityId: field.semantic_compatibility_id || undefined,
        filterable: true,
      };
    });
}

export function filterFieldsFromNames(
  names: string[],
  labels: (key: string) => string = (key) => key,
): SearchFilterFieldOption[] {
  return [
    ...new Set(
      names.filter(
        (name) => name && !name.startsWith("__") && !SEARCH_AUTOCOMPLETE_EXCLUDED.has(name),
      ),
    ),
  ].map((key) => {
    const kind = kindForLegacyField(key);
    return {
      key,
      label: labels(key),
      kind,
      cardinality: kind === "list" ? "collection" : "scalar",
      controlledValues: [],
      filterable: true,
    };
  });
}

/**
 * Compatibility-only type inference for records that predate schema descriptors.
 * New behavior should use SchemaField.type/cardinality instead of adding names here.
 */
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
  if (
    field === "is_direct_quote" ||
    field === "primary_text" ||
    field === "needs_review" ||
    field === "document_is_translation"
  )
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
  if (
    field === "stance" ||
    field === "proposition_status" ||
    field === "region_type" ||
    field === "discourse_role"
  )
    return "choice";
  return "text";
}

/**
 * Prefer schema descriptors. Database Search also intersects them with the
 * collection's declared filter-field capability so the UI cannot offer a
 * schema field the active index cannot execute.
 *
 * Built-in names are retained only as a schema-less legacy fallback.
 */
export function resolveSearchFilterFields(options: {
  schema?: MetadataSchema | null;
  collectionFields?: string[];
  availableFields?: string[];
  labels?: (key: string) => string;
  database?: boolean;
}): SearchFilterFieldOption[] {
  const labels = options.labels || ((key: string) => key);
  const collectionFields = options.collectionFields || [];
  const fromSchema = filterFieldsFromSchema(options.schema, {
    filterableNames: options.database && collectionFields.length ? collectionFields : null,
  });
  if (fromSchema.length) return fromSchema;

  const collection = filterFieldsFromNames(collectionFields, labels);
  if (options.database && collection.length) return collection;

  const available = filterFieldsFromNames(options.availableFields || [], labels);
  if (available.length) return available;

  return filterFieldsFromNames(SEARCH_FILTER_FIELDS as string[], labels);
}

export function filterOpsForKind(
  kind: FilterFieldKind,
  options: { database?: boolean; method?: string } = {},
): Array<[string, string, string]> {
  let base: Array<[string, string, string]>;
  if (kind === "number") {
    base = [
      ["eq", "search.operator_eq", "equals"],
      ["neq", "search.operator_neq", "not equal"],
      ["gte", "search.operator_gte", "at least"],
      ["lte", "search.operator_lte", "at most"],
      ["empty", "search.operator_empty", "is empty"],
      ["notempty", "search.operator_notempty", "is not empty"],
    ];
  } else if (kind === "list") {
    base = [
      ["has", "search.operator_has", "contains"],
      ["nhas", "search.operator_nhas", "does not contain"],
      ["eq", "search.operator_eq", "equals"],
      ["neq", "search.operator_neq", "not equal"],
      ["empty", "search.operator_empty", "is empty"],
      ["notempty", "search.operator_notempty", "is not empty"],
    ];
  } else if (kind === "boolean" || kind === "choice") {
    base = [
      ["eq", "search.operator_eq", "equals"],
      ["neq", "search.operator_neq", "not equal"],
      ["empty", "search.operator_empty", "is empty"],
      ["notempty", "search.operator_notempty", "is not empty"],
    ];
  } else {
    base = [
      ["eq", "search.operator_eq", "equals"],
      ["neq", "search.operator_neq", "not equal"],
      ["has", "search.operator_has", "contains"],
      ["nhas", "search.operator_nhas", "does not contain"],
      ["empty", "search.operator_empty", "is empty"],
      ["notempty", "search.operator_notempty", "is not empty"],
    ];
  }
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

/**
 * Compatibility adapter for legacy callers that only provide a storage name.
 * Schema-aware Search uses filterOpsForKind with the resolved field descriptor.
 */
export function filterOpsForField(field: string): [string, string][] {
  return filterOpsForKind(kindForLegacyField(field)).map(([op, , fallback]) => [op, fallback]);
}
