/* Copyright 2026 Aaron John Schlosser, PhD. */
import { apiRequest } from "../http";
import type {
  AuthorCandidate,
  CaptureCandidatePage,
  CaptureOptions,
  CorpusCapture,
  CorpusCaptureListItem,
  SourceProviderInfo,
} from "./types";

const CAPTURES = "/api/corpus/captures";
const capturePath = (captureId: string, suffix = "") =>
  `${CAPTURES}/${encodeURIComponent(captureId)}${suffix}`;

export interface CandidateFilters {
  offset?: number;
  limit?: number;
  provider?: string;
  language?: string;
  role?: string;
  selection?: "selected" | "excluded";
  acquisition?: string;
}

function query(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params))
    if (value !== undefined && value !== "") search.set(key, String(value));
  const text = search.toString();
  return text ? `?${text}` : "";
}

/** Corpus Capture: author resolution, discovery, review and acquisition. It never starts a build. */
export const corpusCaptureApi = {
  sourceProviders: () =>
    apiRequest<{ items: SourceProviderInfo[] }>("/api/corpus/source-providers"),
  searchAuthors: (q: string, language = "en", limit = 10) =>
    apiRequest<{ items: AuthorCandidate[] }>(
      `/api/corpus/authors/search${query({ q, language, limit })}`,
    ),
  createCapture: (wikidataQid: string, options: CaptureOptions, uiLanguage = "en") =>
    apiRequest<CorpusCapture>(CAPTURES, {
      method: "POST",
      body: JSON.stringify({
        wikidata_qid: wikidataQid,
        options,
        start_discovery: true,
        ui_language: uiLanguage,
      }),
    }),
  listCaptures: (limit = 100) =>
    apiRequest<{ items: CorpusCaptureListItem[] }>(`${CAPTURES}${query({ limit })}`),
  getCapture: (captureId: string) => apiRequest<CorpusCapture>(capturePath(captureId)),
  deleteCapture: (captureId: string) =>
    apiRequest<{ deleted: string }>(capturePath(captureId), { method: "DELETE" }),
  candidates: (captureId: string, filters: CandidateFilters = {}) =>
    apiRequest<CaptureCandidatePage>(
      capturePath(captureId, `/candidates${query({ offset: 0, limit: 1000, ...filters })}`),
    ),
  /** `candidateIds: null` applies to every candidate in the capture. */
  setSelection: (captureId: string, candidateIds: string[] | null, selected: boolean) =>
    apiRequest<CorpusCapture>(capturePath(captureId, "/selection"), {
      method: "PATCH",
      body: JSON.stringify({ candidate_ids: candidateIds, selected }),
    }),
  discover: (captureId: string) =>
    apiRequest<CorpusCapture>(capturePath(captureId, "/discover"), { method: "POST" }),
  refresh: (captureId: string) =>
    apiRequest<CorpusCapture>(capturePath(captureId, "/refresh"), { method: "POST" }),
  acquire: (captureId: string) =>
    apiRequest<CorpusCapture>(capturePath(captureId, "/acquire"), { method: "POST" }),
  retry: (captureId: string) =>
    apiRequest<CorpusCapture>(capturePath(captureId, "/retry"), { method: "POST" }),
  cancel: (captureId: string) =>
    apiRequest<CorpusCapture>(capturePath(captureId, "/cancel"), { method: "POST" }),
};
