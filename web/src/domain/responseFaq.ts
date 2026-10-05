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

/* eslint-disable @typescript-eslint/no-explicit-any */
type Loose = Record<string, any>;
type Fn = (...args: any[]) => any;

export type ResponseFaqDeps = {
  api: Fn;
  canAccessPage: (page: string) => boolean;
  tr: (key: string, fallback?: string) => string;
  gradeRagResponse: Fn;
  prepareRagRerun: Fn;
};

// The Response Library (FAQ) reads and its two row actions. Grading opens the LLM launcher and rerun loads the saved
// request into the Research form; both are handed in so callers choose how they are reached.
export function createResponseFaq({
  api,
  canAccessPage,
  tr,
  gradeRagResponse,
  prepareRagRerun,
}: ResponseFaqDeps) {
  async function getResponseFaqPage({ limit = 50, offset = 0, query = "" } = {}) {
    if (!canAccessPage("faq")) throw new Error(tr("permissions.faq_denied"));
    const params = new URLSearchParams({
      limit: String(Math.max(1, Math.min(1000, Number(limit) || 50))),
      offset: String(Math.max(0, Number(offset) || 0)),
    });
    const search = String(query || "").trim();
    if (search) params.set("query", search);
    return api(`/api/response-cache/records?${params}`);
  }
  function gradeResponseFaqRecord(record: Loose = {}) {
    return gradeRagResponse({
      question: record.question || "",
      answer: record.text || "",
      evidence: Array.isArray(record.evidence) ? record.evidence : [],
      responseRecordId: record.record_id || null,
      generationProvider: record.provider || null,
      generationModel: record.model || null,
    });
  }
  function rerunResponseFaqRecord(record: Loose = {}) {
    const request = { ...(record.rag_request || {}) };
    delete request.thread_id;
    delete request.idempotency_key;
    return prepareRagRerun(request);
  }
  return { getResponseFaqPage, gradeResponseFaqRecord, rerunResponseFaqRecord };
}
