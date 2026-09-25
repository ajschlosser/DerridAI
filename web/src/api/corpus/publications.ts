/* Copyright 2026 Aaron John Schlosser, PhD. */
import { apiRequest } from "../http";
import { LEGACY_CORPUS_BASE } from "./compatibility";

export const corpusPublicationsApi = {
  publish: (buildId: string) =>
    apiRequest<{
      publication_id: string;
      filename: string;
      sha256: string;
      record_count: number;
      created_at: string;
    }>(`${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/publish`, {
      method: "POST",
      body: JSON.stringify({ require_acceptance: true }),
    }),
  publicationUrl: (publicationId: string) =>
    `${LEGACY_CORPUS_BASE}/publications/${encodeURIComponent(publicationId)}/download`,
};
