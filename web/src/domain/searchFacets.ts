/* Copyright 2026 Aaron John Schlosser, PhD. */

// Search facets, filter descriptors and row/record filter matching for the Search and Records views. Moved
// verbatim from the legacy runtime; the state it read is passed in as dependencies.

import {
  SEARCH_AUTOCOMPLETE_EXCLUDED,
  SEARCH_FACET_FIELDS,
  SEARCH_FILTER_FIELDS,
} from "./runtimeConstants";

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

interface Deps {
  tr: (key: string, fallback?: string) => string;
  label: (key: string) => string;
  display: (value: unknown) => string;
  pages: (record: Loose) => string;
  recordDbStatus: (file: Loose, index: number, record: Loose) => Loose;
  recordFields: () => string[];
  uid: () => string;
  dbSearchWhere: () => Loose;
  filterOpsForField: (field: string) => string[][];
  getSearchFacetFilters: () => Loose;
}

export function createSearchFacets(deps: Deps) {
  const {
    tr,
    label,
    display,
    recordDbStatus,
    pages,
    recordFields,
    uid,
    dbSearchWhere,
    filterOpsForField,
  } = deps;
  function searchFacetRawValues(record: Loose, field: string, row: Loose | null = null) {
    if (field === "needs_review") return [record?.needs_review ? "true" : "false"];
    if (field === "__db_status") {
      if (row?.file) return [recordDbStatus(row.file, row.index, record).kind];
      return ["exists"];
    }
    const value = record?.[field];
    if (value == null || value === "") return [];
    if (Array.isArray(value))
      return value.flatMap((item) => (item == null ? [] : [String(item).trim()])).filter(Boolean);
    if (typeof value === "object")
      return Object.values(value)
        .flatMap((item) => (item == null ? [] : [String(item).trim()]))
        .filter(Boolean);
    return [String(value).trim()].filter(Boolean);
  }
  function searchFacetDisplay(field: string, value: string) {
    if (field === "needs_review")
      return value === "true"
        ? tr("search.needs_review")
        : tr("search.reviewed");
    if (field === "__db_status") {
      const labelsByKind: Record<string, string> = {
        synced: tr("search.db_synced"),
        changed: tr("search.db_pending"),
        exists: tr("search.db_in_database"),
        absent: tr("search.db_not_in_database"),
        unknown: tr("search.db_unknown"),
        none: tr("search.db_none"),
      };
      return labelsByKind[value] || value;
    }
    return value || tr("ui.none");
  }
  function searchFacetMatches(
    record: Loose,
    field: string,
    selected: string[],
    row: Loose | null = null,
  ) {
    if (!selected?.length) return true;
    const values = searchFacetRawValues(record, field, row).map((value) =>
      String(value).toLocaleLowerCase(),
    );
    return selected.some((value) => values.includes(String(value).toLocaleLowerCase()));
  }
  function searchRowMatchesFacets(row: Loose, excludeField = "") {
    for (const [field, values] of Object.entries(deps.getSearchFacetFilters() || {})) {
      if (field === excludeField || !Array.isArray(values) || !values.length) continue;
      if (!searchFacetMatches(row.record, field, values, row)) return false;
    }
    return true;
  }
  function searchRecordMatchesFacets(record: Loose, excludeField = "") {
    for (const [field, values] of Object.entries(deps.getSearchFacetFilters() || {})) {
      if (field === excludeField || !Array.isArray(values) || !values.length) continue;
      if (!searchFacetMatches(record, field, values, null)) return false;
    }
    return true;
  }
  function searchFacetCountsFromRows(baseRows: Loose[], field: string) {
    const counts = new Map();
    for (const row of baseRows) {
      if (!searchRowMatchesFacets(row, field)) continue;
      for (const value of searchFacetRawValues(row.record, field, row))
        counts.set(value, (counts.get(value) || 0) + 1);
    }
    return counts;
  }
  function searchFacetCountsFromRecords(records: Loose[], field: string) {
    const counts = new Map();
    for (const record of records) {
      if (!searchRecordMatchesFacets(record, field)) continue;
      for (const value of searchFacetRawValues(record, field, null))
        counts.set(value, (counts.get(value) || 0) + 1);
    }
    return counts;
  }
  function buildSearchFacets(source: Loose[], { database = false } = {}) {
    const rows = (database ? null : source) as Loose[];
    const records = (database ? source : null) as Loose[];
    return SEARCH_FACET_FIELDS.filter((field) => !(database && field === "__db_status"))
      .map((field) => {
        const counts = database
          ? searchFacetCountsFromRecords(records, field)
          : searchFacetCountsFromRows(rows, field);
        const selected = new Set((deps.getSearchFacetFilters()?.[field] || []).map(String));
        const values = [...counts.entries()]
          .sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])))
          .slice(0, 20)
          .map(([value, count]) => ({
            value: String(value),
            label: searchFacetDisplay(field, String(value)),
            count,
            selected: selected.has(String(value)),
          }));
        for (const value of selected as unknown as string[]) {
          if (!values.some((item) => item.value === value))
            values.push({
              value,
              label: searchFacetDisplay(field, value),
              count: 0,
              selected: true,
            });
        }
        return { field, label: label(field), values };
      })
      .filter((facet) => facet.values.length);
  }
  function searchSuggestions(recordsOrRows: Loose[], { database = false } = {}) {
    const out: Record<string, string[]> = {};
    const rows = database ? recordsOrRows.map((record) => ({ record })) : recordsOrRows;
    const fields = [
      ...new Set([
        ...SEARCH_FILTER_FIELDS,
        ...recordFields().filter((field) => !SEARCH_AUTOCOMPLETE_EXCLUDED.has(field)),
      ]),
    ];
    for (const field of fields) {
      if (SEARCH_AUTOCOMPLETE_EXCLUDED.has(field)) continue;
      const values = new Set<string>();
      for (const row of rows as Loose[]) {
        for (const value of searchFacetRawValues(row.record, field, row.file ? row : null)) {
          const text = String(value).trim();
          if (text && text.length <= 180) values.add(text);
          if (values.size >= 120) break;
        }
        if (values.size >= 120) break;
      }
      if (values.size)
        out[field] = [...values].sort((a, b) =>
          a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }),
        );
    }
    return out;
  }
  function searchFilterDescriptor(filter: Loose) {
    const ops = filterOpsForField(filter.field);
    const op = ops.find(([value]) => value === filter.op);
    return {
      id: String(filter.id || uid()),
      field: String(filter.field || ""),
      field_label: label(filter.field || ""),
      op: String(filter.op || "eq"),
      op_label: tr(`search.operator_${filter.op}`, op?.[1] || filter.op || "equals"),
      value: String(filter.value ?? ""),
    };
  }
  function dbSearchFilterDescriptors() {
    return Object.entries(dbSearchWhere()).map(([field, value]) => {
      const contains = value && typeof value === "object" && "$contains" in value;
      return {
        id: `db:${field}`,
        field,
        field_label: label(field),
        op: contains ? "has" : "eq",
        op_label: contains
          ? tr("search.operator_has")
          : tr("search.operator_eq"),
        value: String(contains ? value.$contains : (value ?? "")),
      };
    });
  }
  function searchColumnOptions(available: string[]) {
    return available.map((key) => ({ key, label: label(key) }));
  }
  function searchSimilarity(distance: unknown) {
    if (distance == null || !Number.isFinite(Number(distance))) return null;
    return Math.max(0, Math.min(1, 1 / (1 + Math.max(0, Number(distance)))));
  }
  function searchMatchReasons(
    record: Loose,
    query: string,
    { database = false, method = "similarity" } = {},
  ) {
    const reasons = [];
    const terms = String(query || "")
      .toLocaleLowerCase()
      .split(/\s+/)
      .filter((term) => term.length > 2);
    for (const field of [
      "work",
      "document_author",
      "speaker",
      "quoted_speaker",
      "position_holder",
      "target",
      "discourse_role",
      "topics",
      "concepts",
      "persons",
    ]) {
      if (!terms.length) break;
      const text = display(record?.[field]).toLocaleLowerCase();
      if (terms.some((term) => text.includes(term))) reasons.push(label(field));
      if (reasons.length >= 3) break;
    }
    if (database && method === "similarity")
      reasons.unshift(tr("search.semantic_match"));
    if (database && method === "mmr")
      reasons.unshift(tr("search.mmr_match"));
    if (database && method === "filter")
      reasons.unshift(tr("search.filter_match"));
    if (
      !database &&
      terms.length &&
      String(record?.text || "")
        .toLocaleLowerCase()
        .includes(terms[0])
    )
      reasons.unshift(tr("search.text_match"));
    return [...new Set(reasons)].slice(0, 4);
  }
  function rowMatchesListFilters(row: Loose, filters: Loose[]) {
    for (const [key, raw] of Object.entries(filters || {})) {
      const filter = String(raw ?? "")
        .trim()
        .toLocaleLowerCase();
      if (!filter) continue;
      if (key === "__db_status") {
        const info = recordDbStatus(row.file, row.index, row.record);
        const haystack = `${info.kind} ${info.label}`.toLocaleLowerCase();
        if (!haystack.includes(filter)) return false;
        continue;
      }
      if (key === "needs_review") {
        const value = row.record.needs_review === true ? "yes" : "no";
        if (value !== filter) return false;
        continue;
      }
      const value = key === "page_start" ? pages(row.record) : display(row.record[key]);
      if (
        !String(value ?? "")
          .toLocaleLowerCase()
          .includes(filter)
      )
        return false;
    }
    return true;
  }
  return {
    searchFacetRawValues,
    searchFacetDisplay,
    searchFacetMatches,
    searchRowMatchesFacets,
    searchRecordMatchesFacets,
    searchFacetCountsFromRows,
    searchFacetCountsFromRecords,
    buildSearchFacets,
    searchSuggestions,
    searchFilterDescriptor,
    dbSearchFilterDescriptors,
    searchColumnOptions,
    searchSimilarity,
    searchMatchReasons,
    rowMatchesListFilters,
  };
}
