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
