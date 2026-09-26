/* Copyright 2026 Aaron John Schlosser, PhD. */
import { apiRequest } from "../http";
import type {
  PdfAsset,
  DocumentLayoutPlan,
  SourceBlock,
  GutenbergHit,
  WikisourceHit,
  GutenbergStatus,
  PageDetectionRequest,
} from "./types";
import { LEGACY_CORPUS_BASE, legacyCorpusUrl } from "./compatibility";

export const corpusSourcesApi = {
  gutenbergStatus: () => apiRequest<GutenbergStatus>("/api/gutenberg/status"),
  refreshGutenbergCatalogue: () =>
    apiRequest<GutenbergStatus>("/api/gutenberg/catalogue/refresh", { method: "POST" }),
  gutenbergArchiveAction: (action: "start" | "pause" | "resume" | "refetch") =>
    apiRequest<GutenbergStatus>(`/api/gutenberg/archive/${action}`, { method: "POST" }),
  listAssets: () => apiRequest<{ items: PdfAsset[] }>(legacyCorpusUrl("assets")),
  async uploadAsset(
    file: File,
    ocrMode = "auto",
    sourceIllegibility = 0,
    pages: PageDetectionRequest = { mode: "auto" },
  ) {
    const body = new FormData();
    body.append("file", file);
    body.append("ocr_mode", ocrMode);
    body.append("ocr_languages", "eng+fra+deu");
    body.append("source_illegibility", String(sourceIllegibility));
    body.append("page_number_detection", pages.mode);
    if (pages.providerProfileId) body.append("provider_profile_id", pages.providerProfileId);
    return apiRequest<PdfAsset>(legacyCorpusUrl("assets"), { method: "POST", body });
  },
  importUrl: (
    url: string,
    sourceIllegibility = 0,
    pages: PageDetectionRequest = { mode: "auto" },
  ) =>
    apiRequest<PdfAsset>(legacyCorpusUrl("assets/url"), {
      method: "POST",
      body: JSON.stringify({
        url,
        source_illegibility: sourceIllegibility,
        page_number_detection: pages.mode,
        provider_profile_id: pages.providerProfileId || undefined,
      }),
    }),
  searchGutenberg: (query: string) =>
    apiRequest<{ items: GutenbergHit[] }>(
      `${LEGACY_CORPUS_BASE}/gutenberg/search?q=${encodeURIComponent(query)}&limit=12`,
    ),
  searchWikisource: (query: string) =>
    apiRequest<{ items: WikisourceHit[] }>(
      `${LEGACY_CORPUS_BASE}/wikisource/search?q=${encodeURIComponent(query)}&limit=12`,
    ),
  importGutenberg: (
    etextId: number,
    sourceIllegibility = 0,
    pages: PageDetectionRequest = { mode: "auto" },
  ) =>
    apiRequest<PdfAsset>(legacyCorpusUrl("gutenberg/import"), {
      method: "POST",
      body: JSON.stringify({
        etext_id: etextId,
        source_illegibility: sourceIllegibility,
        page_number_detection: pages.mode,
        provider_profile_id: pages.providerProfileId || undefined,
      }),
    }),
  assetContentUrl: (assetId: string) =>
    `${LEGACY_CORPUS_BASE}/assets/${encodeURIComponent(assetId)}/content`,
  updatePageLabels: (assetId: string, labels: Record<number, string | null>) =>
    apiRequest<PdfAsset>(
      `${LEGACY_CORPUS_BASE}/assets/${encodeURIComponent(assetId)}/page-labels`,
      {
        method: "PATCH",
        body: JSON.stringify({ labels }),
      },
    ),
  updateDocumentLayout: (assetId: string, plan: DocumentLayoutPlan) =>
    apiRequest<PdfAsset>(
      `${LEGACY_CORPUS_BASE}/assets/${encodeURIComponent(assetId)}/document-layout`,
      {
        method: "PATCH",
        body: JSON.stringify(plan),
      },
    ),
  blocks: (assetId: string, offset = 0, limit = 200, ids: string[] = []) =>
    apiRequest<{ items: SourceBlock[]; total: number }>(
      `${LEGACY_CORPUS_BASE}/assets/${encodeURIComponent(assetId)}/blocks?offset=${offset}&limit=${limit}${
        ids.length ? `&ids=${encodeURIComponent(ids.join(","))}` : ""
      }`,
    ),
  profiles: () =>
    apiRequest<{ items: Array<Record<string, unknown>> }>(legacyCorpusUrl("corpus-profiles")),
};
