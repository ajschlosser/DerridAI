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
      review_mode?: "reviewed" | "autonomous" | "hybrid" | "unreviewed";
      decision_mode?: "reviewed" | "autonomous" | "hybrid" | "unreviewed";
      celf_conformant?: boolean;
      celf_conformance?: Record<string, unknown>;
      human_reviewed_record_count?: number;
      autonomous_record_count?: number;
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
  unfinishedCorpusUrl: (buildId: string) =>
    `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/download-unfinished`,
};
