/* Copyright 2026 Aaron John Schlosser, PhD. */
import { assertionFieldsByTab } from "./fieldAssertions";

const STORAGE_KEY = "derridai.record.inspectorLayout.v1";

export type InspectorTabKey = "overview" | "provenance" | "indexing";

export type InspectorLayoutRow =
  | { id: string; kind: "heading"; label: string }
  | { id: string; kind: "field"; field: string };

export type InspectorLayout = Record<InspectorTabKey, InspectorLayoutRow[]>;

export const INSPECTOR_TABS: InspectorTabKey[] = ["overview", "provenance", "indexing"];

export const INSPECTOR_FIELD_CATALOG: Record<InspectorTabKey, string[]> = {
  overview: [
    "document_author",
    "edition",
    "year",
    "publication_year",
    "publisher",
    "translator",
    "document_language",
    "original_language",
    "region_type",
    "region_author",
    "__pages",
    "primary_text",
    "needs_review",
    "review_reason",
    "is_direct_quote",
    "quoted_speaker",
    "quoted_author",
    "quoted_work",
    "quoted_position_holder",
    "quoted_addressee",
    "quoted_referent",
  ],
  provenance: [
    "speaker",
    "position_holder",
    "stance",
    "target",
    "discourse_role",
    "proposition_status",
    "claim_scope",
    "semantic_function",
  ],
  indexing: [
    "topics",
    "concepts",
    "persons",
    "works_referenced",
    "institutions_referenced",
    "locations_referenced",
    "events_referenced",
    "groups_referenced",
    "languages_referenced",
  ],
};

export function inspectorFieldCatalog(
  record?: Record<string, unknown> | null,
): Record<InspectorTabKey, string[]> {
  const asserted = assertionFieldsByTab(record || {});
  return {
    overview: [...new Set([...INSPECTOR_FIELD_CATALOG.overview, ...asserted.overview])],
    provenance: [...new Set([...INSPECTOR_FIELD_CATALOG.provenance, ...asserted.provenance])],
    indexing: [...new Set([...INSPECTOR_FIELD_CATALOG.indexing, ...asserted.indexing])],
  };
}

function uid() {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `row-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function heading(label: string): InspectorLayoutRow {
  return { id: uid(), kind: "heading", label };
}

function field(name: string): InspectorLayoutRow {
  return { id: uid(), kind: "field", field: name };
}

export function defaultInspectorLayout(record?: Record<string, unknown> | null): InspectorLayout {
  const asserted = assertionFieldsByTab(record || {});
  const base: InspectorLayout = {
    overview: [
      heading("Record context"),
      field("document_author"),
      field("edition"),
      field("year"),
      field("publication_year"),
      field("publisher"),
      field("translator"),
      field("document_language"),
      field("original_language"),
      field("region_type"),
      field("region_author"),
      field("__pages"),
      field("primary_text"),
      field("needs_review"),
      field("review_reason"),
      heading("Quotation provenance"),
      field("is_direct_quote"),
      field("quoted_speaker"),
      field("quoted_author"),
      field("quoted_work"),
      field("quoted_position_holder"),
      field("quoted_addressee"),
      field("quoted_referent"),
    ],
    provenance: [
      heading("Attribution"),
      field("speaker"),
      field("position_holder"),
      field("stance"),
      field("target"),
      heading("Discourse"),
      field("discourse_role"),
      field("proposition_status"),
      field("claim_scope"),
      field("semantic_function"),
    ],
    indexing: [
      heading("Research index"),
      field("topics"),
      field("concepts"),
      field("persons"),
      field("works_referenced"),
    ],
  };
  const used = new Set(
    Object.values(base)
      .flat()
      .filter((row): row is Extract<InspectorLayoutRow, { kind: "field" }> => row.kind === "field")
      .map((row) => row.field),
  );
  const appendMissing = (tab: InspectorTabKey) => {
    const missing = asserted[tab].filter((name) => !used.has(name));
    if (!missing.length) return;
    base[tab].push(...missing.map(field));
  };
  appendMissing("overview");
  appendMissing("provenance");
  appendMissing("indexing");
  return base;
}

export function normalizeInspectorLayout(
  raw: unknown,
  record?: Record<string, unknown> | null,
): InspectorLayout {
  const fallback = defaultInspectorLayout(record);
  const catalog = inspectorFieldCatalog(record);
  if (!raw || typeof raw !== "object") return fallback;
  const source = raw as Record<string, unknown>;
  const next = { ...fallback };
  for (const tab of INSPECTOR_TABS) {
    const rows = source[tab];
    if (!Array.isArray(rows) || !rows.length) continue;
    const cleaned: InspectorLayoutRow[] = [];
    const seen = new Set<string>();
    for (const item of rows) {
      if (!item || typeof item !== "object") continue;
      const row = item as Record<string, unknown>;
      if (row.kind === "heading") {
        cleaned.push({
          id: String(row.id || uid()),
          kind: "heading",
          label: String(row.label || "").trim() || "Section",
        });
        continue;
      }
      if (row.kind === "field") {
        const name = String(row.field || "");
        if (!name || seen.has(name) || !catalog[tab].includes(name)) continue;
        seen.add(name);
        cleaned.push({ id: String(row.id || uid()), kind: "field", field: name });
      }
    }
    if (cleaned.length) next[tab] = cleaned;
  }
  return next;
}

export function moveInspectorRow(
  rows: InspectorLayoutRow[],
  from: number,
  to: number,
): InspectorLayoutRow[] {
  if (from === to || from < 0 || to < 0 || from >= rows.length || to >= rows.length) return rows;
  const next = [...rows];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

export function groupInspectorRows(
  rows: InspectorLayoutRow[],
): Array<{ heading: string | null; fields: string[] }> {
  const sections: Array<{ heading: string | null; fields: string[] }> = [];
  let current: { heading: string | null; fields: string[] } = { heading: null, fields: [] };
  for (const row of rows) {
    if (row.kind === "heading") {
      if (current.heading || current.fields.length) sections.push(current);
      current = { heading: row.label, fields: [] };
      continue;
    }
    current.fields.push(row.field);
  }
  if (current.heading || current.fields.length) sections.push(current);
  return sections;
}

export function unusedInspectorFields(
  tab: InspectorTabKey,
  rows: InspectorLayoutRow[],
  record?: Record<string, unknown> | null,
): string[] {
  const used = new Set(
    rows
      .filter((row): row is { id: string; kind: "field"; field: string } => row.kind === "field")
      .map((row) => row.field),
  );
  return inspectorFieldCatalog(record)[tab].filter((name) => !used.has(name));
}

export function loadInspectorLayout(record?: Record<string, unknown> | null): InspectorLayout {
  try {
    return normalizeInspectorLayout(
      JSON.parse(localStorage.getItem(STORAGE_KEY) || "null"),
      record,
    );
  } catch {
    return defaultInspectorLayout(record);
  }
}

export function saveInspectorLayout(
  layout: InspectorLayout,
  record?: Record<string, unknown> | null,
) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(normalizeInspectorLayout(layout, record)));
  } catch {
    /* browser storage may be unavailable */
  }
}

export function createInspectorHeading(label = "Section"): InspectorLayoutRow {
  return heading(label);
}

export function createInspectorField(name: string): InspectorLayoutRow {
  return field(name);
}
