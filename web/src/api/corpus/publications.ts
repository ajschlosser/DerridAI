/* Copyright 2026 Aaron John Schlosser, PhD. */
import { apiRequest } from "../http";
import { LEGACY_CORPUS_BASE } from "./compatibility";

export const corpusPublicationsApi = {
  publish: (buildId: string, options: { acceptUnreviewed?: boolean } = {}) =>
    apiRequest<{
      publication_id: string;
      filename: string;
      sha256: string;
      record_count: number;
      created_at: string;
      celf_conformant?: boolean;
      unreviewed_record_count?: number;
      unreviewed_accepted_field_count?: number;
    }>(`${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/publish`, {
      method: "POST",
      body: JSON.stringify({
        require_acceptance: true,
        accept_unreviewed: Boolean(options.acceptUnreviewed),
      }),
    }),
  publicationUrl: (publicationId: string) =>
    `${LEGACY_CORPUS_BASE}/publications/${encodeURIComponent(publicationId)}/download`,
};
