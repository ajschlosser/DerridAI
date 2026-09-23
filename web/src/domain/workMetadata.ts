/* Copyright 2026 Aaron John Schlosser, PhD. */
import { WORK_METADATA_LLM_FIELDS } from "./runtimeConstants";

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

// Helpers for the Works metadata editor and overview. Moved verbatim from the legacy runtime.

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
