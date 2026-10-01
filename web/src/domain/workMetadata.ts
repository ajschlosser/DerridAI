/* Copyright 2026 Aaron John Schlosser, PhD. */
import { currentFieldAssertions } from "./fieldAssertions";
import { WORK_METADATA_LLM_FIELDS } from "./runtimeConstants";

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

// Helpers for the Works metadata editor and overview. Moved verbatim from the legacy runtime.

const SOURCE_TYPE_ALIASES: Record<string, string> = {
  monograph: "book",
  edited_book: "book",
  journal: "journal_article",
  article: "journal_article",
  article_journal: "journal_article",
  book_chapter: "chapter",
  chapter_in_book: "chapter",
  reference_entry: "chapter",
  dissertation: "thesis",
  website: "web",
  webpage: "web",
  podcast: "audio",
  photograph: "image",
  moving_image: "video",
};
const CANONICAL_SOURCE_TYPES = new Set([
  "book",
  "journal_article",
  "chapter",
  "thesis",
  "web",
  "audio",
  "image",
  "video",
  "archival",
  "unknown",
]);

export function canonicalWorkSourceType(value: unknown): string {
  const normalized = String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[- ]/g, "_");
  if (!normalized) return "unknown";
  return (
    SOURCE_TYPE_ALIASES[normalized] ||
    (CANONICAL_SOURCE_TYPES.has(normalized) ? normalized : "unknown")
  );
}

export function workSourceType(row: Loose): string {
  const declared =
    row?.record?.source_type || row?.record?.document_type || row?.record?.media_kind;
  if (declared) return canonicalWorkSourceType(declared);
  const mediaType = String(row?.record?.media_type || "").toLowerCase();
  if (mediaType.startsWith("audio/")) return "audio";
  if (mediaType.startsWith("image/")) return "image";
  if (mediaType.startsWith("video/")) return "video";
  const filename = String(row?.file?.name || "").toLowerCase();
  if (/\.(mp3|wav|m4a|flac|ogg|opus|aac)$/.test(filename)) return "audio";
  if (/\.(png|jpe?g|gif|tiff?|webp|svg)$/.test(filename)) return "image";
  if (/\.(mp4|mov|m4v|webm|avi|mkv)$/.test(filename)) return "video";
  if (/^https?:\/\//.test(String(row?.record?.url || ""))) return "web";
  return "book";
}

export function workMetadataSourceGroups(
  item: Loose,
): Array<{ sourceType: string; rows: Loose[] }> {
  const groups = new Map<string, Loose[]>();
  for (const row of item?.rows || []) {
    const sourceType = workSourceType(row);
    const rows = groups.get(sourceType) || [];
    rows.push(row);
    groups.set(sourceType, rows);
  }
  return [...groups.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([sourceType, rows]) => ({ sourceType, rows }));
}

export function representativeWorkMetadata(rows: Loose[]) {
  const metadata: Loose = {};
  for (const field of WORK_METADATA_LLM_FIELDS) {
    const values = rows
      .map((row) => row.record?.[field])
      .filter((value) => value !== undefined && value !== null && value !== "");
    if (!values.length) continue;
    const counts = new Map();
    for (const value of values) {
      const key = JSON.stringify(value);
      counts.set(key, (counts.get(key) || 0) + 1);
    }

    const [winner] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0] || [];
    if (winner !== undefined) {
      try {
        metadata[field] = JSON.parse(winner);
      } catch {
        metadata[field] = values[0];
      }
    }
  }
  const work = rows[0]?.record?.work;
  if (work) metadata.work = work;
  return metadata;
}

export interface WorkMetadataPresentationRow {
  field_id: string;
  field: string;
  value: unknown;
  mixed: boolean;
  unique_count: number;
  empty: boolean;
}

const WORK_METADATA_EXCLUDED_ASSERTION_FIELDS = new Set([
  "region_type",
  "primary_text",
  "discourse_role",
  "speaker",
  "position_holder",
  "target",
  "stance",
  "proposition_status",
  "claim_scope",
  "semantic_function",
  "is_direct_quote",
  "quoted_speaker",
  "quoted_author",
  "quoted_work",
  "quoted_position_holder",
  "quoted_addressee",
  "quoted_referent",
  "quotation_chain",
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

const DOCUMENT_FIELD_IDENTITIES: Record<string, string> = {
  document_title: "derridai.document.title",
  short_title: "derridai.document.short_title",
  original_title: "derridai.document.original_title",
  document_author: "derridai.document.document_author",
  translator: "derridai.document.translator",
  publisher: "derridai.document.publisher",
  publication_place: "derridai.document.publication_place",
  publication_year: "derridai.document.publication_year",
  edition: "derridai.document.edition",
  isbn: "derridai.document.isbn",
  document_language: "derridai.document.language",
  original_language: "derridai.document.original_language",
  document_is_translation: "derridai.document.document_is_translation",
  document_type: "derridai.document.document_type",
};

/**
 * Work-inspector metadata follows the shared work-metadata defaults for ordering,
 * then discovers additional schema-defined assertion fields by stable identity.
 *
 * Built-in discourse/indexing semantics stay out of this bibliographic surface:
 * they already have dedicated review/insight presentations. Custom assertions
 * are not required to be added to another Works-specific whitelist to appear.
 */
export function workMetadataPresentationRows(rows: Loose[]): WorkMetadataPresentationRow[] {
  const identities = new Map<string, string>();
  const discovered: string[] = [];
  const prepared = (rows || []).map((row) => {
    const record = row?.record || {};
    const assertions = currentFieldAssertions(record);
    return {
      record,
      assertions,
      assertionByName: new Map(assertions.map((assertion) => [assertion.field_name, assertion])),
    };
  });

  for (const { assertions } of prepared) {
    for (const assertion of assertions) {
      const field = String(assertion.field_name || "").trim();
      const fieldId = String(assertion.field_id || "").trim();
      if (!field || WORK_METADATA_EXCLUDED_ASSERTION_FIELDS.has(field)) continue;
      if (fieldId.startsWith("derridai.indexing.") || fieldId.startsWith("derridai.quotation."))
        continue;
      if (!identities.has(field)) identities.set(field, fieldId || `legacy.${field}`);
      if (!discovered.includes(field)) discovered.push(field);
    }
  }

  const defaults = WORK_METADATA_LLM_FIELDS.filter(
    (field) => !["full_citation", "cover_url", "url"].includes(field),
  );
  const fields = [...defaults, ...discovered.filter((field) => !defaults.includes(field))];

  return fields.map((field) => {
    const values = prepared.map(({ record, assertionByName }) => {
      if (record[field] !== undefined) return record[field];
      const assertion = assertionByName.get(field);
      if (!assertion || (assertion.value_status && assertion.value_status !== "present")) return null;
      return assertion.value;
    });
    const serialized = values.map((value) => JSON.stringify(value ?? null));
    const mixed = serialized.some((value) => value !== serialized[0]);
    const meaningful = values.filter(
      (value) =>
        value !== null &&
        value !== undefined &&
        value !== "" &&
        (!Array.isArray(value) || value.length > 0),
    );
    const unique = new Set(meaningful.map((value) => JSON.stringify(value)));
    return {
      field_id:
        identities.get(field) ||
        DOCUMENT_FIELD_IDENTITIES[field] ||
        `legacy.${field}`,
      field,
      value: mixed ? null : values[0] ?? null,
      mixed,
      unique_count: mixed ? unique.size : 0,
      empty: meaningful.length === 0,
    };
  });
}

export function workOverviewMetadataRows(rows: Loose[]) {
  const fields = [
    "document_title",
    "document_author",
    "edition",
    "year",
    "publication_year",
    "publisher",
    "publication_place",
    "translator",
    "isbn",
    "document_language",
    "original_language",
    "canonical_work_id",
    "full_citation",
  ];
  return fields
    .map((field) => ({ field, ...commonWorkValue(rows, field) }))
    .filter(
      (item) =>
        item.mixed || (item.value !== undefined && item.value !== null && item.value !== ""),
    );
}

export function commonWorkValue(rows: Loose[], field: string) {
  const values = rows.map((row) => row.record[field]);
  if (!values.length) return { mixed: false, value: null };
  const first = JSON.stringify(values[0] ?? null);
  const mixed = values.some((value) => JSON.stringify(value ?? null) !== first);
  return { mixed, value: mixed ? null : values[0] };
}

export function workCoverUrl(rows: Loose[]) {
  return String(rows.map((row) => row.record?.cover_url).find(Boolean) || "").trim();
}

export function parseProposedMetadataValue(raw: unknown, original: unknown) {
  if (typeof original === "number") {
    const value = Number(raw);
    if (!Number.isFinite(value)) throw new Error("Expected a number.");
    return value;
  }
  if (typeof original === "boolean") return String(raw).toLowerCase() === "true";
  return raw;
}
