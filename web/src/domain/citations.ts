/* Copyright 2026 Aaron John Schlosser, PhD. */

// MLA-style citation text for a corpus record. Pure functions extracted from the legacy runtime.

type CitationRecord = Record<string, unknown> | null | undefined;

export function mlaAuthorName(value: unknown): string {
  const name = String(value || "").trim();
  if (!name) return "";
  if (name.includes(",")) return name;
  const parts = name.split(/\s+/);
  if (parts.length < 2) return name;
  return `${parts.pop()}, ${parts.join(" ")}`;
}

export function mlaPageSpan(record: CitationRecord, { prefix = true }: { prefix?: boolean } = {}): string {
  const a = record?.page_start;
  const b = record?.page_end;
  if (a == null || a === "") return "";
  const span = b != null && b !== "" && String(b) !== String(a) ? `${a}–${b}` : `${a}`;
  return prefix ? `${b != null && b !== "" && String(b) !== String(a) ? "pp." : "p."} ${span}` : span;
}

export function inlineCitation(record: CitationRecord): string {
  const author = String(record?.document_author || record?.author || "").trim();
  const last = author.includes(",") ? author.split(",")[0].trim() : author.split(/\s+/).filter(Boolean).pop() || "";
  const year = String(record?.publication_year || record?.year || "").trim();
  const a = record?.page_start;
  const b = record?.page_end;
  const page = a == null || a === "" ? "" : b != null && b !== "" && String(b) !== String(a) ? `${a}-${b}` : `${a}`;
  const head = [last, year].filter(Boolean).join(" ");
  if (head && page) return `(${head}: ${page})`;
  if (head) return `(${head})`;
  return page ? `(${page})` : String(record?.record_id || "Record");
}

export function mlaSentence(value: unknown): string {
  const text = String(value || "").trim();
  return text && !/[.!?]$/.test(text) ? `${text}.` : text;
}

export function fullCitation(record: CitationRecord, { includePages = true }: { includePages?: boolean } = {}): string {
  const author = mlaAuthorName(record?.document_author || record?.author);
  const title = String(record?.work || record?.document_title || "").trim();
  const translator = String(record?.translator || "").trim();
  const edition = String(record?.edition || "").trim();
  const publisher = String(record?.publisher || "").trim();
  const year = String(record?.publication_year || record?.year || "").trim();
  const page = includePages ? mlaPageSpan(record) : "";
  const opening = [author ? mlaSentence(author) : "", title ? mlaSentence(title) : ""].filter(Boolean).join(" ");
  const publication: string[] = [];
  if (translator) publication.push(`Translated by ${translator}`);
  if (edition) publication.push(edition);
  if (publisher) publication.push(publisher);
  if (year) publication.push(year);
  if (page) publication.push(page);
  const tail = publication.length ? `${publication.join(", ")}.` : "";
  return [opening, tail].filter(Boolean).join(" ").trim() || String(record?.record_id || "Record");
}
