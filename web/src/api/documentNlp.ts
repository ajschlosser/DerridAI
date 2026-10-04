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

import { apiRequest } from "./http";
import type { JobSummary } from "./jobs";

export interface LanguagePackFile {
  role: "entity" | "coref" | "quote";
  filename: string;
  url: string;
  sha256: string;
  size?: number | null;
}

export interface LanguagePack {
  pack_id: string;
  language: string;
  engine: string;
  label: string;
  source_url?: string;
  license?: string;
  note?: string;
  /** spaCy model size: md (CPU-friendly) or lg (better names, larger). */
  tier?: "sm" | "md" | "lg";
  requires?: string[];
  missing_requirements?: string[];
  origin: "builtin" | "custom";
  /** True when the model is part of the API image rather than installed at runtime. */
  bundled?: boolean;
  files: LanguagePackFile[];
  installable: boolean;
  installed: boolean;
  installed_at?: string | null;
  download_bytes: number;
  worker_bundled: boolean;
  active_job?: JobSummary | null;
}

export interface LanguagePackListing {
  packs: LanguagePack[];
  models_dir: string;
}

/** Administrator commands for Document Intelligence language packs. */
export const documentNlpApi = {
  listPacks: () => apiRequest<LanguagePackListing>("/api/document-nlp/packs"),
  addPack: (entry: Record<string, unknown>) =>
    apiRequest<LanguagePackListing>("/api/document-nlp/packs", {
      method: "POST",
      body: JSON.stringify(entry),
    }),
  removePack: (packId: string) =>
    apiRequest<LanguagePackListing>(`/api/document-nlp/packs/${encodeURIComponent(packId)}`, {
      method: "DELETE",
    }),
  installPack: (packId: string) =>
    apiRequest<JobSummary>(`/api/document-nlp/packs/${encodeURIComponent(packId)}/install`, {
      method: "POST",
    }),
  cancelInstall: (jobId: string) =>
    apiRequest<JobSummary>(`/api/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" }),
  uninstallPack: (packId: string) =>
    apiRequest<LanguagePackListing>(
      `/api/document-nlp/packs/${encodeURIComponent(packId)}/install`,
      { method: "DELETE" },
    ),
};
