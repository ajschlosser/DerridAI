// Copyright 2026 Aaron John Schlosser, PhD.

import type { CitationResult, EvidenceRef, PublicationRecord } from "./types";

function firstPrintedPage(record: PublicationRecord): string | number | undefined {
  const direct = record.printed_page ?? record.page_start ?? record.page;
  if (direct != null) return direct;
  for (const span of record.source_spans ?? []) {
    if (span.printed_page != null) return span.printed_page;
  }
  return undefined;
}

export function formatCitation(record: PublicationRecord): CitationResult {
  const base = String(
    record.full_citation || record.citation || record.work || record.record_id || "",
  ).trim();
  const start = firstPrintedPage(record);
  const end = record.page_end as string | number | undefined;
  let plain = base;
  if (start != null && !/\bp{1,2}\.\s*\d/i.test(base)) {
    plain =
      end != null && String(end) !== String(start)
        ? `${base}, pp. ${start}–${end}`
        : `${base}, p. ${start}`;
  }
  return {
    plain,
    locator: {
      recordId: String(record.record_id),
      printedPageStart: start,
      printedPageEnd: end,
    },
  };
}

export function citationForEvidence(evidence: EvidenceRef): CitationResult {
  return {
    plain: evidence.citation,
    locator: {
      recordId: evidence.recordId,
    },
  };
}
