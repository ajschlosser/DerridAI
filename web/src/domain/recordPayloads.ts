/* Copyright 2026 Aaron John Schlosser, PhD. */
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

// Record payload and PDF-link helpers, moved verbatim from the legacy runtime.

export function recordPayload(
  record: unknown,
  {
    fields = null,
    includeUpdates = false,
    includeChromaId = false,
  }: { fields?: string[] | null; includeUpdates?: boolean; includeChromaId?: boolean } = {},
): Loose {
  const source: Loose = record && typeof record === "object" ? (record as Loose) : {};
  const keys = fields ? [...new Set(fields)] : Object.keys(source);
  const out: Loose = {};
  for (const key of keys) {
    if (!(key in source)) continue;
    if (key === "updates" && !includeUpdates) continue;
    if (key === "_updates_count" || key === "_researcher_text_policy") continue;
    if (key === "_chroma_id" && !includeChromaId) continue;
    out[key] = source[key];
  }
  return out;
}

export function compactRecordHistory(record: Loose | null | undefined, limit: number = 80) {
  const updates = Array.isArray(record?.updates) ? record.updates : [];
  return updates
    .slice(-Math.max(1, limit))
    .reverse()
    .map((update, index) => ({
      id: `history-${updates.length - index - 1}`,
      field_name: String(update?.field_name || ""),
      timestamp: update?.timestamp || null,
      source: String(update?.source || "manual"),
      initiated_by: update?.initiated_by || null,
      model: update?.model || null,
      reason: update?.reason || null,
    }));
}

export function pdfLinks(
  record: Loose | null | undefined,
): Array<{ pdf_file: string; pdf_page: number }> {
  const file = String(record?.pdf_file || "");
  if (file && Array.isArray(record?.pdf_pages)) {
    return [
      ...new Set(record.pdf_pages.map(Number).filter((page) => Number.isFinite(page) && page > 0)),
    ]
      .sort((a, b) => a - b)
      .map((pdf_page) => ({ pdf_file: file, pdf_page }));
  }
  const legacyPage = Number(record?.pdf_page);
  if (file && Number.isFinite(legacyPage) && legacyPage > 0)
    return [{ pdf_file: file, pdf_page: legacyPage }];
  if (Array.isArray(record?.pdf_links)) {
    return record.pdf_links
      .map((link) => ({ pdf_file: String(link?.pdf_file || ""), pdf_page: Number(link?.pdf_page) }))
      .filter((link) => link.pdf_file && Number.isFinite(link.pdf_page) && link.pdf_page > 0);
  }
  return [];
}

export function normalizePdfLinkChanges(record: Loose, links: Loose[]): Loose {
  const files = [...new Set(links.map((link) => link.pdf_file).filter(Boolean))];
  if (files.length > 1)
    throw new Error(
      "A record can link to multiple pages of one PDF source, not multiple PDF files.",
    );
  const file = files[0] || null;
  const pages = [
    ...new Set(
      links
        .map((link) => Number(link.pdf_page))
        .filter((page) => Number.isFinite(page) && page > 0),
    ),
  ].sort((a, b) => a - b);
  const changes: Loose = { pdf_file: file, pdf_pages: pages };
  if (record.pdf_page !== undefined) changes.pdf_page = null;
  if (record.pdf_links !== undefined) changes.pdf_links = null;
  return changes;
}

// 0.30.11 packet discipline: API boundaries receive only fields required by
// the operation. Audit history is intentionally opt-in because it can dwarf
// the rest of a record after repeated edits.
export const TOUCHUP_TRANSPORT_CONTEXT_FIELDS = [
  "record_id", "work", "document_author", "edition", "year", "page_start", "page_end",
  "region_type", "region_author", "primary_text", "speaker", "position_holder", "target",
  "discourse_role", "proposition_status", "semantic_function", "stance", "claim_scope",
  "text", "topics", "concepts", "persons", "works_referenced", "is_direct_quote",
  "quoted_speaker", "quoted_author", "quoted_work", "quoted_position_holder",
  "quoted_addressee", "quoted_referent", "quotation_chain", "inline_citation",
  "full_citation", "needs_review", "review_reason",
];
export const RAG_EVIDENCE_TRANSPORT_FIELDS = [
  "record_id", "canonical_work_id", "work", "document_author", "edition", "year",
  "page_start", "page_end", "translator", "speaker", "position_holder", "target",
  "discourse_role", "proposition_status", "stance", "text", "topics", "concepts",
  "persons", "document_language", "document_languages", "quoted_speaker",
  "quoted_author", "quoted_work", "quoted_position_holder",
];

export function upsertRecordPayload(record: unknown, chromaId: string | null = null): Loose {
  const out = recordPayload(record, { includeChromaId: false });
  if (chromaId) out._chroma_id = chromaId;
  return out;
}

export function touchupRecordPayload(record: unknown, fields: string[] = []): Loose {
  return recordPayload(record, { fields: [...fields, ...TOUCHUP_TRANSPORT_CONTEXT_FIELDS] });
}

export function ragEvidenceRecordPayload(record: unknown): Loose {
  return recordPayload(record, { fields: RAG_EVIDENCE_TRANSPORT_FIELDS });
}

export function isResponseCacheStore(store: Loose | null | undefined): boolean {
  return Boolean(
    store &&
      (store.name === "_response_cache" ||
        store.storage_name === "derridai_response_cache" ||
        store.metadata?.derridai_system_collection === "response_cache"),
  );
}
